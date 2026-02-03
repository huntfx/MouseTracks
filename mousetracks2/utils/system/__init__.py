import shlex
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Type

from .base import Window as _Window, MonitorEventsListener as _MonitorEventsListener
from ...constants import APP_EXECUTABLE, IS_BUILT_EXE

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


def remap_autostart(cmd: str | None = None) -> bool:
    """Check if remaping the executable is required.
    This is in case a user downloads a new version.
    It is only designed to run for built executables.
    """
    # Skip if running directly from Python
    if not IS_BUILT_EXE:
        return False

    # Get the parts from the existing command
    exe, args = split_autostart(cmd)

    # Skip if autostart is disabled, or MouseTracks was installed
    if exe is None or '--installed' in args:
        return False

    # Update the path to the current portable executable
    exe_path = Path(exe.strip('"')).resolve()
    if IS_BUILT_EXE and exe_path != APP_EXECUTABLE.resolve():
        print(f'Autostart path is outdated. Correcting "{exe}" to "{APP_EXECUTABLE}".')
        set_autostart(*args, ignore_args=('--start-hidden', '--start-visible'))
        return True

    return False


def split_autostart(cmd: str | None = None) -> tuple[str | None, list[str]]:
    """Split an autostart string into the executable and args."""
    if cmd is None:
        try:
            cmd = get_autostart()
        except NotImplementedError:
            cmd = None
        if cmd is None:
            return None, []
    exe, *args = shlex.split(cmd, posix=sys.platform != 'win32')
    return exe, args
