import platform
from typing import TYPE_CHECKING, Callable, Generic, Iterable, SupportsIndex, TypeVar, cast, overload

if platform.system() == 'Windows':
    from .win import *
elif platform.system() == 'Linux':
    from .linux import *
elif platform.system() == 'Darwin':
    from .mac import *

import pynput


T = TypeVar('T')


if 'get_monitor_locations' not in globals():
    def get_monitor_locations():
        """Get the location of each monitor.
        This is a placeholder function which will use the primary
        monitor resolution.

        Returns:
            ((x1, y1, x2, y2),) as 4 integers for each monitor
        """
        width, height = main_monitor_resolution()
        return ((0, 0, width, height),)


if 'check_key_press' not in globals():
    check_key_press = lambda key: False


if 'DOUBLE_CLICK_INTERVAL' not in globals():
    DOUBLE_CLICK_INTERVAL = 0.5


def match_pixel_to_monitor(pixel, monitors):
    """Find which monitor a pixel is on.

    Returns:
        index of monitor, or None
    """
    for i, (x1, y1, x2, y2) in enumerate(monitors):
        if x1 <= pixel[0] < x2 and y1 <= pixel[1] < y2:
            return i


class DefaultList(list[T], Generic[T]):
    """Implementation of a default list.

    >>> intlist = DefaultList(int)
    >>> intlist[0]
    0
    >>> len(intlist)
    1
    >>> intlist[2]
    0
    >>> len(intlist)
    3
    >>> intlist[1] = intlist[3] = 5
    >>> intlist == [0, 5, 0, 5]
    True
    >>> intlist[2:5:2] = [10, 15]
    >>> intlist
    [0, 5, 10, 5, 15]
    >>> intlist[::-1]
    [15, 5, 10, 5, 0]
    >>> intlist[1::-1]
    [5, 0]
    >>> intlist[-1]
    15
    """

    def __init__(self, default_factory: Callable[[], T], *args):
        self.default_factory = default_factory
        super().__init__(*args)

    def _missing(self, idx: SupportsIndex | slice):
        """Ensure the list is the correct length for the given index."""
        if isinstance(idx, slice):
            start = idx.start or 0
            stop = idx.stop or 0
            step = idx.step or 1
            if step > 0:
                idx = stop - divmod(stop - start, step)[1]
            else:
                idx = start - divmod(start - stop, step)[1]

        while len(self) <= idx.__index__():
            self.append(self.default_factory())

    @overload
    def __getitem__(self, idx: SupportsIndex) -> T: ...
    @overload
    def __getitem__(self, idx: slice) -> list[T]: ...
    def __getitem__(self, idx: SupportsIndex | slice) -> T | list[T]:
        """Get an item at the specified index."""
        if isinstance(idx, slice):
            self._missing(idx)
            return super().__getitem__(idx)

        try:
            return super().__getitem__(idx)
        except IndexError:
            self._missing(idx)
            return super().__getitem__(idx)

    @overload
    def __setitem__(self, idx: SupportsIndex, value: T) -> None: ...
    @overload
    def __setitem__(self, idx: slice, value: Iterable[T]) -> None: ...
    def __setitem__(self, idx: SupportsIndex | slice, value: T | Iterable[T]) -> None:
        """Set a value at a specified index."""
        if isinstance(idx, slice):
            if TYPE_CHECKING: value = cast(Iterable[T], value)
            self._missing(idx)
            super().__setitem__(idx, value)

        else:
            if TYPE_CHECKING: value = cast(T, value)
            try:
                super().__setitem__(idx, value)
            except IndexError:
                self._missing(idx)
                super().__setitem__(idx, value)


def get_cursor_pos() -> tuple[int, int] | None:
    """Get the current cursor position.

    This is only used for switching profiles, as the mouse move listener
    can handle all other events.
    """
    x, y = pynput.mouse.Controller().position
    if x is y is None:
        return None
    return x, y
