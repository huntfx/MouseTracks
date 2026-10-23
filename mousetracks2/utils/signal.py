"""Qt-like signals in pure python.
Completely overkill, just a little side project for fun.

Not Implemented:
    Certain features were planned but not added. This is a little note
    to prevent the same things being attempted in the future.

    Recursive Signature Matching:
        Originally the signature matching was going to check inside each
        container type, and verify everything was a perfect match. It
        just seemed overkill for something so minor, would break on new
        types and would add a lot of overhead in `emit()` too.
        >>> Signal(list[str], dict[str, int])

    Joined Signals:
        My original idea of adding variants. It would allow for multiple
        signatures for a single signal. Abandoned as then emitting would
        get confusing to deal with.
        >>> Signal(str, int) | Signal(str)

    Variant Signals:
        I intended it to be like `typing.overload`. Each variant was to
        be a subset of the main signal, including the option for more
        restrictive types. In the end, it got too restrictive and was
        removed, but the underlying code was kept so that it can build
        the variants automatically.
        >>> Signal(str, x_pos: int, y_pos: int).variant(str)

    Type Hints:
        I'd have loved for the inputs in `Signal()` to propagate through
        to all the other methods, to make life easy when coding with it.
        Turns out the class is too dynamic and Python literally doesn't
        support the type hints I'd need. I tested a half-baked solution,
        but it wasn't good enough so I removed it. `Any` it is.
"""

import inspect
import threading
import weakref
from contextlib import contextmanager, suppress
from dataclasses import dataclass, field
from types import UnionType
from typing import Any, Callable, Generator, Self, Sequence, Type


def _normalise_annotation(annotation: Any) -> type | UnionType | Any:
    """Convert empty annotations into Any."""
    if annotation is inspect.Parameter.empty:
        return Any
    return annotation


def _type_members(annotation: type | UnionType | Any | None) -> set[type]:
    """Split an annotation into its individual member types if union."""
    if annotation is None:
        return {type(None)}
    if isinstance(annotation, UnionType):
        return set(annotation.__args__)
    return {getattr(annotation, '__origin__', annotation)}


@dataclass
class Signature:
    """Hold a function signature."""

    positional_types: list[type | UnionType | None]
    named_types: dict[str, type | UnionType | None]
    args_type: type | UnionType | None
    kwargs_type: type | UnionType | None
    _raw_signature: inspect.Signature = field(repr=False)

    @classmethod
    def from_function(cls, func: Callable) -> Self:
        """Get the signature of a function."""
        raw_signature = inspect.signature(func, eval_str=True)
        positional_types: list[Any] = []
        named_types: dict[str, Any] = {}
        args_type = kwargs_type = None
        for name, param in raw_signature.parameters.items():
            annotation = _normalise_annotation(param.annotation)
            match param.kind:
                case param.POSITIONAL_ONLY | param.POSITIONAL_OR_KEYWORD:
                    positional_types.append(annotation)
                case param.KEYWORD_ONLY:
                    named_types[name] = annotation
                case param.VAR_POSITIONAL:
                    args_type = annotation
                case param.VAR_KEYWORD:
                    kwargs_type = annotation

        return cls(
            positional_types,
            named_types,
            args_type,
            kwargs_type,
            raw_signature,
        )

    @staticmethod
    def _is_type_match(expected: type | UnionType, actual: type | UnionType) -> bool:
        """Check the types are a match."""
        if expected is Any or actual is Any:
            return True
        return bool(_type_members(actual) & _type_members(expected))

    def match(self, *arg_types: type | UnionType | Any, **kwarg_types: type | UnionType | Any) -> bool:
        """Determine if a function call is compatible with this signature."""
        try:
            bound = self._raw_signature.bind(*arg_types, **kwarg_types)
        except TypeError:
            return False

        for name, value in bound.arguments.items():
            param = self._raw_signature.parameters[name]
            expected = _normalise_annotation(param.annotation)

            if param.kind is param.VAR_POSITIONAL:
                if not all(self._is_type_match(expected, v) for v in value):
                    return False
            elif param.kind is param.VAR_KEYWORD:
                if not all(self._is_type_match(expected, v) for v in value.values()):
                    return False
            elif not self._is_type_match(expected, value):
                return False

        return True


class Signal:
    """Create a Qt-like signal with declared argument types.

    Runtime type checks are enforced.
    """

    def __init__(self, *args_: type | UnionType, **kwargs: type | UnionType) -> None:
        self._arg_types: list[list[type | UnionType]] = [[]]
        self._kwarg_types: list[dict[str, type | UnionType]] = [{}]
        self._connections: list[list[Callable | weakref.WeakMethod]] = [[]]

        # Generate variants by trimming the parameters
        args: list[type | UnionType] = list(args_)
        named_items: list[tuple[str, type | UnionType]] = list(kwargs.items())
        self._num_args = len(args)
        self._num_kwargs = len(kwargs)

        for i in range(self._num_args):
            self._arg_types.insert(0, args[:i + 1])
            self._kwarg_types.insert(0, {})
            self._connections.append([])

        for i in range(self._num_kwargs):
            self._arg_types.insert(0, args)
            self._kwarg_types.insert(0, dict(named_items[:i + 1]))
            self._connections.append([])

        self._args_default: list[Any] = []
        self._kwargs_default: dict[str, Any] = {}
        self._name: str | None = None
        self._lock = threading.Lock()

    def __set_name__(self, owner: type, name: str) -> None:
        """Record the class attribute name of this signal."""
        self._name = name

    def __get__(self, instance: object | None, owner: type | None = None) -> Self:
        """Give each instance its own signal.

        This is called when the signal is defined as a class attribute,
        as each instance of the class needs its own copy of the signal.
        """
        if instance is None:
            return self
        assert self._name is not None
        with self._lock:
            bound = instance.__dict__.get(self._name)
            if bound is None:
                bound = self._fork_instance()
                instance.__dict__[self._name] = bound
        return bound

    def _fork_instance(self) -> Self:
        # pylint: disable=protected-access
        """Create a shared instance fork.
        This is used to create separate instances that share everything
        but connections.
        """
        bound = object.__new__(type(self))
        bound._arg_types = self._arg_types
        bound._kwarg_types = self._kwarg_types
        bound._num_args = self._num_args
        bound._num_kwargs = self._num_kwargs
        bound._args_default = self._args_default
        bound._kwargs_default = self._kwargs_default
        bound._name = self._name
        bound._connections = [[] for _ in self._connections]
        bound._lock = threading.Lock()
        return bound

    def connect(self, func: Callable) -> None:
        """Connect a function to a signal.
        Raises a ValueError if the signature is not compatible.
        """
        signature = Signature.from_function(func)

        for i, (arg_types, kwarg_types) in enumerate(zip(self._arg_types, self._kwarg_types)):
            if signature.match(*arg_types, **kwarg_types):
                ref: Callable | weakref.WeakMethod = weakref.WeakMethod(func) if inspect.ismethod(func) else func
                break
        else:
            raise ValueError('signal does not support function signature')

        with self._lock:
            self._connections[i].append(ref)

    def _resolve_overflow(self, args: list[Any], kwargs: dict[str, Any],
                          reverse: bool = False) -> tuple[list, dict]:
        """Resolve an overflow of `args` into `kwargs`.

        >>> Signal(str, x=int, y=int)._resolve_overflow(['', 0], {'y': 1})
        ([''], {'x': 0, 'y': 1})
        """
        names = list(self._kwarg_types[0])

        if reverse:
            empty_names = (name for name in reversed(names)
                           if name not in kwargs)
            i = 0
            with suppress(IndexError):
                for i, name in enumerate(empty_names, start=1):
                    kwargs[name] = args[-i]
            if i:
                args = args[:-i]
            return args, kwargs

        else:
            remaining_args = iter(args[self._num_args:])
            with suppress(StopIteration):
                for name in names:
                    if name not in kwargs:
                        kwargs[name] = next(remaining_args)
            return args[:self._num_args] + list(remaining_args), kwargs

    def _verify_input_length(self, args: list[Any], kwargs: dict[str, Any]) -> None:
        """Check the input length is not too long, or raise an error."""
        if len(args) > self._num_args:
            total = self._num_args + self._num_kwargs
            raise TypeError(f'expected at most {total} '
                            f'argument{"s"[:total > 1]}, '
                            f'got {len(args) + len(kwargs)}')
        for name in kwargs:
            if name not in self._kwarg_types[0]:
                raise ValueError(f'got an unexpected keyword argument {name!r}')

    def _check_arg_types(self, args: list[Any], types: Sequence[type | UnionType],
                         reverse: bool = False) -> None:
        """Check `arg` types against the signal signature.
        This assumes any overflow has already been handled.

        If `reverse` is set, then it will test values from the right.
        """
        if reverse:
            start = max(0, len(types) - len(args))
            zipped = zip(args, types[start:])
        else:
            start = 0
            zipped = zip(args, types)

        for i, (arg, type_) in enumerate(zipped, start=start):
            if not isinstance(arg, type_):
                raise TypeError(f'expected {type_!r} for pos {i}, '
                                f'got {type(arg).__name__!r}')

    def _check_kwarg_types(self, kwargs: dict, types: dict) -> None:
        """Check `kwarg` types against the signal signature.
        This assumes any overflow has already been handled.
        """
        for name, value in kwargs.items():
            if name in types and not isinstance(value, types[name]):
                raise TypeError(f'expected {types[name]!r} for {name!r}, '
                                f'got {type(value).__name__!r}')

    def _resolve_defaults(self, args: list[Any], kwargs: dict[str, Any]) -> tuple[list, dict]:
        """Resolve input `args` and `kwargs` with default values.
        This assumes any overflow has already been handled.

        If any values are missing, an error is raised.
        """
        num_args = len(args)
        missing_arg_count = max(0, self._num_args - num_args)
        missing_kwargs = [name for name in self._kwarg_types[0]
                          if name not in kwargs]

        # Apply default values, or raise an error
        for i in range(missing_arg_count):
            try:
                args.append(self._args_default[i])
            except IndexError:
                raise TypeError('missing required argument: pos '
                                f'{self._num_args - missing_arg_count}') from None
        for missing_kwarg in missing_kwargs:
            try:
                kwargs[missing_kwarg] = self._kwargs_default[missing_kwarg]
            except KeyError:
                raise TypeError('missing required positional argument: '
                                f'{missing_kwarg!r}') from None
        return args, kwargs

    def emit(self, *args_: Any, **kwargs: Any) -> None:
        """Emit data to all connections."""
        args = list(args_)
        args, kwargs = self._resolve_overflow(args, kwargs)
        self._verify_input_length(args, kwargs)
        args, kwargs = self._resolve_defaults(args, kwargs)

        # Emit for all possible signatures
        for arg_types, kwarg_types, connections in zip(self._arg_types, self._kwarg_types, self._connections):
            if not connections:
                continue

            self._check_arg_types(args, arg_types)
            self._check_kwarg_types(kwargs, kwarg_types)

            # Emit signal to the connection
            connection_args = args[:len(arg_types)]
            connection_kwargs = {k: v for k, v in kwargs.items() if k in kwarg_types}
            dead = False
            for ref in connections:
                connection = ref() if isinstance(ref, weakref.ref) else ref
                if connection is not None:
                    connection(*connection_args, **connection_kwargs)
                else:
                    dead = True

            # Only rebuild the list if a connection was actually deleted
            if dead:
                with self._lock:
                    connections[:] = [ref for ref in connections
                                      if not isinstance(ref, weakref.ref) or ref() is not None]

    def defaults(self, *args_: Any, **kwargs: Any) -> Self:
        """Set default values for emit() to use.
        These work similar to `namedtuple`, in order but filling in the
        right most slice of function arguments.

        >>> Signal(str, enable=bool, x=int, y=int).defaults(True, x=0, y=0)
        """
        if self._args_default or self._kwargs_default:
            raise RuntimeError('unable to set multiple defaults')

        args = list(args_)
        args, kwargs = self._resolve_overflow(args, kwargs, reverse=True)
        self._verify_input_length(args, kwargs)
        self._check_arg_types(args, self._arg_types[0], reverse=True)
        self._check_kwarg_types(kwargs, self._kwarg_types[0])
        self._args_default = args
        self._kwargs_default = kwargs
        return self


class _LightweightTest:
    """Base class for a lightweight test runner.
    Subclass this and add `test_*` methods using plain `assert`.

    These are shamelessly LLM generated as tests are boring to write.
    """

    @classmethod
    def run(cls) -> None:
        passed = failed = 0
        for subclass in cls.__subclasses__():
            instance = subclass()
            for name in dir(instance):
                if not name.startswith('test_'):
                    continue
                try:
                    getattr(instance, name)()
                except AssertionError as e:
                    failed += 1
                    print(f'FAIL  {subclass.__name__}.{name}: {e}')
                except Exception as e:  # pylint: disable=broad-exception-caught
                    failed += 1
                    print(f'ERROR {subclass.__name__}.{name}: {e!r}')
                else:
                    passed += 1
        print(f'{passed} passed, {failed} failed')

    @contextmanager
    def assert_raises(self, *exceptions: Type[Exception]) -> Generator[None, None, None]:
        """Check that an exception is raised."""
        with suppress(*exceptions):
            yield
            assert False


class _TestSignatureMatch(_LightweightTest):
    @staticmethod
    def _sig(func: Callable) -> Signature:
        return Signature.from_function(func)

    def test_unannotated(self) -> None:
        def fn(x): ...  # type: ignore[no-untyped-def]
        sig = self._sig(fn)
        assert not sig.match()
        assert sig.match(int)
        assert sig.match(str)
        assert not sig.match(str, int)

    def test_annotated(self) -> None:
        def fn(x: int): ...  # type: ignore[no-untyped-def]
        sig = self._sig(fn)
        assert not sig.match()
        assert sig.match(int)
        assert sig.match(Any)
        assert not sig.match(int, int)
        assert sig.match(x=int)
        assert not sig.match(y=int)
        assert sig.match(str | int)

    def test_annotated_mix(self) -> None:
        def fn(x: int | str): ...  # type: ignore[no-untyped-def]
        sig = self._sig(fn)
        assert not sig.match()
        assert sig.match(int)
        assert sig.match(Any)
        assert not sig.match(int, int)
        assert sig.match(x=int)
        assert sig.match(x=str)
        assert sig.match(str | int)

    def test_args(self) -> None:
        def fn(x: int, *args: str): ...  # type: ignore[no-untyped-def]
        sig = self._sig(fn)
        assert sig.match(int)
        assert not sig.match(int, int)
        assert sig.match(int, str, str)

    def test_args_unannotated(self) -> None:
        def fn(x: int, *args): ...  # type: ignore[no-untyped-def]
        sig = self._sig(fn)
        assert sig.match(int, str, bool)

    def test_defaults(self) -> None:
        def fn(x: int, y: int = 0): ...  # type: ignore[no-untyped-def]
        sig = self._sig(fn)
        assert sig.match(int)
        assert sig.match(int, int)
        assert sig.match(x=int, y=int)

    def test_all(self) -> None:
        def fn(x, *args: str, y: int | None = None, **kwargs: int): ...  # type: ignore[no-untyped-def]
        sig = self._sig(fn)
        assert sig.match(str)
        assert not sig.match(str, int)
        assert sig.match(str, y=int)
        assert sig.match(str, z=int)
        assert not sig.match(str, z=str)

    def test_recursive(self) -> None:
        def fn(x: list[str]): ...  # type: ignore[no-untyped-def]
        sig = self._sig(fn)
        assert sig.match(list)
        assert sig.match(list[int])  # Recursive not supported, so will match
        assert not sig.match(dict)

    def test_stringified_annotation(self) -> None:
        def fn(x: 'Signal'): ...  # type: ignore[no-untyped-def]
        sig = self._sig(fn)
        assert sig.match(Signal)
        assert not sig.match(int)


class _TestSignal(_LightweightTest):
    def test_positional_types(self) -> None:
        calls = []
        def func(x, y): calls.append((x, y))  # type: ignore[no-untyped-def]

        sig = Signal(int, int)
        sig.connect(func)
        sig.emit(2, 5)

        assert calls == [(2, 5)]

    def test_named_types_auto_prefix(self) -> None:
        calls = []
        def func(x, y): calls.append(('func', x, y))  # type: ignore[no-untyped-def]
        def func2(x): calls.append(('func2', x))  # type: ignore[no-untyped-def]

        sig = Signal(x=int, y=int)
        sig.connect(func)
        sig.connect(func2)
        sig.emit(2, 5)

        assert calls == [('func', 2, 5), ('func2', 2)]

    def test_type_mismatch_raises(self) -> None:
        def func(x, y): ...  # type: ignore[no-untyped-def]

        sig = Signal(x=int, y=int)
        sig.connect(func)

        with self.assert_raises(TypeError):
            sig.emit(2, 'test')

    def test_auto_prefix_accepts_subset_signatures(self) -> None:
        def func_full(x: int, y: int): ...  # type: ignore[no-untyped-def]
        def func_partial(x: int): ...  # type: ignore[no-untyped-def]

        sig = Signal(int, int)
        sig.connect(func_full)
        sig.connect(func_partial)

    def test_connect_rejects_incompatible_signature(self) -> None:
        def func(x: str): ...  # type: ignore[no-untyped-def]

        sig = Signal(int)
        with self.assert_raises(ValueError):
            sig.connect(func)

    def test_defaults_positional(self) -> None:
        calls = []
        def func(x, y): calls.append((x, y))  # type: ignore[no-untyped-def]

        sig = Signal(str, int).defaults(5)
        sig.connect(func)
        sig.emit('hi')

        assert calls == [('hi', 5)]

    def test_defaults_named(self) -> None:
        calls = []
        def func(x, y): calls.append((x, y))  # type: ignore[no-untyped-def]

        sig = Signal(x=int, y=int).defaults(y=5)
        sig.connect(func)
        sig.emit(x=1)

        assert calls == [(1, 5)]

    def test_defaults_named_missing_required_raises(self) -> None:
        def func(x, y): ...  # type: ignore[no-untyped-def]

        sig = Signal(x=int, y=int).defaults(y=5)
        sig.connect(func)

        with self.assert_raises(TypeError):
            sig.emit(y=5)  # x still required

    def test_defaults_overflow_fills_trailing_named(self) -> None:
        calls = []
        def func(s, *, enable, x, y): calls.append((s, enable, x, y))  # type: ignore[no-untyped-def]

        sig = Signal(str, enable=bool, x=int, y=int).defaults(True, x=0, y=0)
        sig.connect(func)
        sig.emit('hi')

        assert calls == [('hi', True, 0, 0)]

    def test_defaults_cannot_set_twice(self) -> None:
        sig = Signal(int).defaults(1)

        with self.assert_raises(RuntimeError):
            sig.defaults(2)

    def test_defaults_type_mismatch_positional_raises(self) -> None:
        sig = Signal(str)
        with self.assert_raises(TypeError):
            sig.defaults(5)

    def test_defaults_type_mismatch_named_raises(self) -> None:
        sig = Signal(x=int)
        with self.assert_raises(TypeError):
            sig.defaults(x='bad')

    def test_emit_too_many_positional_raises(self) -> None:
        sig = Signal(str)
        with self.assert_raises(TypeError):
            sig.emit('a', 'b')

    def test_defaults_too_many_positional_raises(self) -> None:
        sig = Signal(str)
        with self.assert_raises(TypeError):
            sig.defaults('a', 'b')

    def test_emit_unexpected_keyword_raises(self) -> None:
        sig = Signal(x=int)
        with self.assert_raises(ValueError):
            sig.emit(x=1, z=2)

    def test_emit_overflow_then_too_many_raises(self) -> None:
        sig = Signal(str, x=int)
        with self.assert_raises(TypeError):
            sig.emit('a', 'b', 'c')

    def test_defaults_partial_trailing_fill(self) -> None:
        calls = []
        def func(s, *, x, y, z): calls.append((s, x, y, z))  # type: ignore[no-untyped-def]

        sig = Signal(str, x=int, y=int, z=int).defaults(1)
        sig.connect(func)
        sig.emit('hi', x=2, y=3)

        assert calls == [('hi', 2, 3, 1)]

    def test_defaults_partial_trailing_fill_missing_raises(self) -> None:
        def func(s, *, x, y, z): ...  # type: ignore[no-untyped-def]

        sig = Signal(str, x=int, y=int, z=int).defaults(1)
        sig.connect(func)

        with self.assert_raises(TypeError):
            sig.emit('hi', x=2)

    def test_emit_explicit_value_overrides_default(self) -> None:
        calls = []
        def func(x, y): calls.append((x, y))  # type: ignore[no-untyped-def]

        sig = Signal(x=int, y=int).defaults(x=0, y=0)
        sig.connect(func)
        sig.emit(x=1, y=2)

        assert calls == [(1, 2)]

    def test_defaults_unexpected_keyword_raises(self) -> None:
        sig = Signal(x=int)
        with self.assert_raises(ValueError):
            sig.defaults(z=1)

    def test_connect_picks_fullest_matching_bucket(self) -> None:
        calls = []
        def func(x, y=0): calls.append((x, y))  # type: ignore[no-untyped-def]

        sig = Signal(int, int)
        sig.connect(func)
        sig.emit(1, 2)

        assert calls == [(1, 2)]

    def test_signal_with_no_args(self) -> None:
        calls = []
        def func(): calls.append(True)  # type: ignore[no-untyped-def]

        sig = Signal()
        sig.connect(func)
        sig.emit()

        assert calls == [True]

    def test_emit_with_no_connections(self) -> None:
        sig = Signal(int)
        sig.emit(1)

    def test_class_attribute_signals_are_independent_per_instance(self) -> None:
        calls = []

        class Widget:
            clicked = Signal(int)

        a = Widget()
        b = Widget()

        def on_a(x): calls.append(('a', x))  # type: ignore[no-untyped-def]
        def on_b(x): calls.append(('b', x))  # type: ignore[no-untyped-def]

        a.clicked.connect(on_a)
        b.clicked.connect(on_b)

        a.clicked.emit(1)
        b.clicked.emit(2)

        assert calls == [('a', 1), ('b', 2)]
        assert a.clicked is a.clicked  # cached, not rebuilt every access
        assert a.clicked is not b.clicked
        assert Widget.clicked is not a.clicked

    def test_class_attribute_defaults_are_shared_across_instances(self) -> None:
        calls = []

        class Widget:
            clicked = Signal(int).defaults(0)

        a = Widget()
        b = Widget()

        def on_a(x): calls.append(('a', x))  # type: ignore[no-untyped-def]
        def on_b(x): calls.append(('b', x))  # type: ignore[no-untyped-def]

        a.clicked.connect(on_a)
        b.clicked.connect(on_b)

        a.clicked.emit()
        b.clicked.emit()

        assert calls == [('a', 0), ('b', 0)]

    def test_connect_drops_collected_receiver(self) -> None:
        calls = []

        class Receiver:
            def on_click(self, x): calls.append(x)  # type: ignore[no-untyped-def]

        sig = Signal(int)
        receiver = Receiver()
        sig.connect(receiver.on_click)

        del receiver
        sig.emit(1)

        assert calls == []

    def test_connect_keeps_plain_function_alive(self) -> None:
        calls = []

        def make_func() -> Callable:
            def func(x: int) -> None: calls.append(x)  # type: ignore[no-untyped-def]
            return func

        sig = Signal(int)
        sig.connect(make_func())  # no other reference to the connected function is kept

        sig.emit(1)

        assert calls == [1]

    def test_emit_prunes_dead_receiver_without_calling_plain_function(self) -> None:
        calls = []

        class Receiver:
            def on_click(self, x): ...  # type: ignore[no-untyped-def]

        def func(x): calls.append(x)  # type: ignore[no-untyped-def]

        sig = Signal(int)
        receiver = Receiver()
        sig.connect(receiver.on_click)
        sig.connect(func)

        del receiver
        sig.emit(1)

        assert calls == [1]

    def test_concurrent_connect_does_not_lose_connections(self) -> None:
        calls: list[int] = []
        sig = Signal(int)
        barrier = threading.Barrier(20)

        def make_func(i: int) -> Callable:
            def func(x: int) -> None:
                calls.append(i)
            return func

        funcs = [make_func(i) for i in range(20)]

        def connect(func: Callable) -> None:
            barrier.wait()
            sig.connect(func)

        threads = [threading.Thread(target=connect, args=(func,)) for func in funcs]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        sig.emit(1)

        assert len(calls) == 20


if __name__ == '__main__':
    _LightweightTest.run()
