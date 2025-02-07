import sys

match sys.platform:
    case 'win32':
        from .win32 import monitor_locations
        from .win32 import get_autorun, set_autorun, remove_autorun

    case 'darwin':
        from .darwin import monitor_locations
        from .placeholders import get_autorun, set_autorun, remove_autorun

    case _:
        from .linux import monitor_locations
        from .placeholders import get_autorun, set_autorun, remove_autorun

__all__ = [
    'monitor_locations',
    'get_autorun', 'set_autorun', 'remove_autorun',
]
