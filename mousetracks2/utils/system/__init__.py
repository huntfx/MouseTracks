import sys
from typing import TYPE_CHECKING, Type

from screeninfo import get_monitors as _get_monitors

from . import placeholders

if TYPE_CHECKING:
    Window: Type[placeholders.Window]

match sys.platform:
    case 'win32':
        from .win32 import check_autostart, set_autostart, remove_autostart
        from .win32 import is_elevated, relaunch_as_elevated
        from .win32 import Window

    case 'darwin':
        from .placeholders import check_autostart, set_autostart, remove_autostart
        from .placeholders import is_elevated, relaunch_as_elevated
        from .placeholders import Window

    case _:
        from .placeholders import check_autostart, set_autostart, remove_autostart
        from .placeholders import is_elevated, relaunch_as_elevated
        from .linux import Window


def monitor_locations() -> list[tuple[int, int, int, int]]:
    """Get the bounds of each monitor."""
    return [(screen.x, screen.y, screen.x + screen.width, screen.y + screen.height)
            for screen in _get_monitors()]


__all__ = [
    'monitor_locations',
    'check_autostart', 'set_autostart', 'remove_autostart',
    'is_elevated', 'relaunch_as_elevated',
    'Window',
]
