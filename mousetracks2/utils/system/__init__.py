import shlex
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Type

from .base import Window as _Window, MonitorEventsListener as _MonitorEventsListener
from ...constants import SYS_EXECUTABLE, IS_BUILT_EXE

if TYPE_CHECKING:
    Window: Type[_Window]
    MonitorEventsListener: Type[_MonitorEventsListener]

match sys.platform:
    case 'win32':
        from .win32 import monitor_locations
        from .win32 import get_autostart, set_autostart, remove_autostart
        from .win32 import is_elevated, relaunch_as_elevated
        from .win32 import Window
        from .win32 import MonitorEventsListener

    case 'darwin':
        from .base import monitor_locations
        from .base import get_autostart, set_autostart, remove_autostart
        from .base import is_elevated, relaunch_as_elevated
        from .base import Window
        from .base import MonitorEventsListener

    case _:
        from .base import monitor_locations
        from .linux import get_autostart, set_autostart, remove_autostart
        from .base import is_elevated, relaunch_as_elevated
        from .linux import Window
        from .base import MonitorEventsListener

__all__ = [
    'monitor_locations',
    'get_autostart', 'set_autostart', 'remove_autostart', 'remap_autostart',
    'is_elevated', 'relaunch_as_elevated',
    'Window',
    'MonitorEventsListener',
]


def remap_autostart(cmd: str | None) -> bool:
    """Check if remaping the executable is required.
    This is in case a user downloads a new version.
    It is only designed to run for built executables.
    """
    if cmd is None or not IS_BUILT_EXE:
        return False
    exe, *args = shlex.split(cmd, posix=sys.platform != 'win32')
    exe_path = Path(exe.strip('"')).resolve()
    if IS_BUILT_EXE and exe_path != Path(SYS_EXECUTABLE).resolve():
        print(f'Autostart path is outdated. Correcting "{exe}" to "{SYS_EXECUTABLE}".')
        set_autostart(*args)
        return True
    return False
