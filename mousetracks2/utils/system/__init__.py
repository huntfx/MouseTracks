import sys

match sys.platform:
    case 'win32':
        from .win32 import monitor_locations
        from .win32 import get_autostart, set_autostart, remove_autostart

    case 'darwin':
        from .darwin import monitor_locations
        from .placeholders import get_autostart, set_autostart, remove_autostart

    case _:
        from .linux import monitor_locations
        from .placeholders import get_autostart, set_autostart, remove_autostart

__all__ = [
    'monitor_locations',
    'get_autostart', 'set_autostart', 'remove_autostart',
]
