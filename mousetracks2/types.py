from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Generic, Iterable, Self, SupportsIndex, TypeVar, cast, overload


T = TypeVar('T')


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

    def __init__(self, default_factory: Callable[[], T], *args: T) -> None:
        self.default_factory = default_factory
        super().__init__(*args)

    def _missing(self, idx: SupportsIndex | slice) -> None:
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

@dataclass
class Rect:
    """Store the data for a rect."""

    left: int = 0
    top: int = 0
    right: int = 0
    bottom: int = 0
    width: int = 0
    height: int = 0

    @classmethod
    def from_size(cls, width: int, height: int, x: int = 0, y: int = 0) -> Self:
        """Create a Rect from a width and height with an optional position."""
        return cls(x, y, x + width, y + height, width, height)

    @classmethod
    def from_rect(cls, left: int, top: int, right: int, bottom: int) -> Self:
        """Create a Rect from the individual components."""
        return cls(left, top, right, bottom, right - left, bottom - top)

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """Get the individual components."""
        return self.left, self.top, self.right, self.bottom

    @property
    def size(self) -> tuple[int, int]:
        """Get the size."""
        return self.width, self.height

    @property
    def position(self) -> tuple[int, int]:
        """Get the position."""
        return self.left, self.top

    def calculate_offset(self, coordinate: tuple[int, int]) -> tuple[int, int] | None:
        """Calculate the offset for a pixel within the rectangle.

        Returns:
            The offset coordinate or None if not within bounds.
        """
        x, y = coordinate
        x1, y1, x2, y2 = self.rect
        if x1 <= x < x2 and y1 <= y < y2:
            return x - x1, y - y1
        return None


class RectList(list[Rect]):
    """Store a list of rects."""

    @overload
    def __getitem__(self, item: SupportsIndex) -> Rect: ...
    @overload
    def __getitem__(self, item: slice) -> Self: ...
    def __getitem__(self, item: SupportsIndex | slice) -> Rect | Self:
        result = super().__getitem__(item)
        if isinstance(result, Rect):
            return result
        return type(self)(result)

    def calculate_offset(self, coordinate: tuple[int, int], combined: bool = False,
                         ) -> tuple[tuple[int, int], tuple[int, int]] | None:
        """Detect which rect contains a given coordinate.

        Returns:
            The rect with the offset coordinate, or None if not within bounds.
        """
        if not self:
            return None

        if combined:
            x_min, y_min, x_max, y_max = self[0].rect
            for x1, y1, x2, y2 in self[1:].rects:
                x_min = min(x_min, x1)
                y_min = min(y_min, y1)
                x_max = max(x_max, x2)
                y_max = max(y_max, y2)

            rect = Rect.from_rect(x_min, y_min, x_max, y_max)
            offset_pixel = rect.calculate_offset(coordinate)
            if offset_pixel is not None:
                return rect.size, offset_pixel

        else:
            for rect in self:
                offset_pixel = rect.calculate_offset(coordinate)
                if offset_pixel is not None:
                    return rect.size, offset_pixel

        return None

    @property
    def rects(self) -> list[tuple[int, int, int, int]]:
        return [item.rect for item in self]

    @property
    def sizes(self) -> list[tuple[int, int]]:
        return [item.size for item in self]

    @property
    def positions(self) -> list[tuple[int, int]]:
        return [item.position for item in self]
