import sys
from typing import TYPE_CHECKING, Type

from .base import remap_autostart, Window as _Window

if TYPE_CHECKING:
    Window: Type[_Window]

match sys.platform:
    case 'win32':
        from .win32 import monitor_locations
        from .win32 import get_autostart, set_autostart, remove_autostart
        from .win32 import is_elevated, relaunch_as_elevated
        from .win32 import Window

    case 'darwin':
        from .base import monitor_locations
        from .base import get_autostart, set_autostart, remove_autostart
        from .base import is_elevated, relaunch_as_elevated
        from .base import Window

    case _:
        from .base import monitor_locations
        from .linux import get_autostart, set_autostart, remove_autostart
        from .base import is_elevated, relaunch_as_elevated
        from .linux import Window

__all__ = [
    'monitor_locations',
    'get_autostart', 'set_autostart', 'remove_autostart', 'remap_autostart',
    'is_elevated', 'relaunch_as_elevated',
    'Window',
]
