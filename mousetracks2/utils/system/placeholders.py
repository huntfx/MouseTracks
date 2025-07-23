"""Placeholder functions that do nothing.
These are used when code hasn't yet been written for an OS.
"""

from typing import Any, Self

def check_autostart() -> bool:
    """Determine if running on startup."""
    raise NotImplementedError


def set_autostart(*args: str) -> None:
    """Set to run on startup."""


def remove_autostart() -> None:
    """Stop running on startup."""


def is_elevated() -> bool:
    """Check if the script is running with admin privileges."""
    return False


def relaunch_as_elevated() -> None:
    """Relaunch the script with admin privileges."""


class Window:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    @classmethod
    def get_focused(cls) -> Self:
        return cls()

    @property
    def pid(self) -> int:
        return 0

    @pid.setter
    def pid(self, pid: int) -> None: ...

    @property
    def title(self) -> str:
        return ''

    @property
    def executable(self) -> str:
        return ''

    @property
    def rects(self) -> list[tuple[int, int, int, int]]:
        return []

    @property
    def position(self) -> tuple[int, int]:
        return (0, 0)

    @property
    def size(self) -> tuple[int, int]:
        return (0, 0)
