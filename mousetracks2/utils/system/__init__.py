import sys
from typing import TYPE_CHECKING, Type

from . import placeholders

if TYPE_CHECKING:
    Window: Type[placeholders.Window]

match sys.platform:
    case 'win32':
        from .win32 import monitor_locations
        from .win32 import check_autostart, set_autostart, remove_autostart
        from .win32 import is_elevated, relaunch_as_elevated
        from .win32 import Window

    case 'darwin':
        from .darwin import monitor_locations
        from .placeholders import check_autostart, set_autostart, remove_autostart
        from .placeholders import is_elevated, relaunch_as_elevated
        from .placeholders import Window

    case _:
        from .linux import monitor_locations
        from .placeholders import check_autostart, set_autostart, remove_autostart
        from .placeholders import is_elevated, relaunch_as_elevated
        from .linux import Window

__all__ = [
    'monitor_locations',
    'check_autostart', 'set_autostart', 'remove_autostart',
    'is_elevated', 'relaunch_as_elevated',
    'Window',
]
