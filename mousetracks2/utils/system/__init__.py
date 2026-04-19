import shlex
import sys
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Type

from . import base
from ...cli import CLI
from ...runtime import LAUNCH_EXECUTABLE, IS_BUILT_EXE, DATA_DIR

if TYPE_CHECKING:
    Window: Type[base.Window]
    MonitorEventListener: Type[base.EventListener]
    ControllerEventListener: Type[base.EventListener]
    ForegroundAppListener: Type[base.EventListener]
    UserResizeAppListener: Type[base.EventListener]

match sys.platform:
    case 'win32':
        from .windows import SUPPORTS_TRAY
        from .windows import monitor_locations
        from .windows import get_autostart, set_autostart, remove_autostart
        from .windows import is_elevated, relaunch_as_elevated
        from .windows import Window
        from .windows import MonitorEventListener, ControllerEventListener
        from .windows import ForegroundAppListener, UserResizeAppListener
        from .base import hide_child_process
        from .windows import prepare_application_icon
        from .windows import update_installer_version_number
        from .windows import force_physical_dpi_awareness

    case 'darwin':
        from .macos import SUPPORTS_TRAY
        from .base import monitor_locations
        from .macos import get_autostart, set_autostart, remove_autostart
        from .base import is_elevated, relaunch_as_elevated
        from .macos import Window
        from .base import MonitorEventListener, ControllerEventListener
        from .base import ForegroundAppListener, UserResizeAppListener
        from .macos import hide_child_process, prepare_application_icon
        from .base import update_installer_version_number
        from .base import force_physical_dpi_awareness

    case _:
        from .base import SUPPORTS_TRAY
        from .base import monitor_locations
        from .linux import get_autostart, set_autostart, remove_autostart
        from .base import is_elevated, relaunch_as_elevated
        from .linux import Window
        from .base import MonitorEventListener, ControllerEventListener
        from .base import ForegroundAppListener, UserResizeAppListener
        from .base import hide_child_process, prepare_application_icon
        from .base import update_installer_version_number
        from .base import force_physical_dpi_awareness

__all__ = [
    'SUPPORTS_TRAY',
    'monitor_locations',
    'get_autostart', 'set_autostart', 'remove_autostart', 'remap_autostart',
    'is_elevated', 'relaunch_as_elevated',
    'Window',
    'MonitorEventListener', 'ControllerEventListener',
    'ForegroundAppListener', 'UserResizeAppListener',
    'hide_child_process', 'prepare_application_icon',
    'update_installer_version_number',
    'force_physical_dpi_awareness',
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

    # Skip if autostart is currently disabled
    if exe is None:
        return False

    # Skip if MouseTracks was installed as it has a single launcher
    if '--installed' in args:
        return False

    # Skip if data dir is different
    if '--data-dir' in args:
        with suppress(KeyError, IndexError):
            data_dir = Path(args[args.index('--data-dir') + 1])
            if data_dir.resolve() != DATA_DIR.resolve():
                return False

    # Skip if portable state is different
    if ('--portable' in args) != CLI.portable:
        return False

    # Update the path to the current portable executable
    exe_path = Path(exe.strip('"')).resolve()
    if IS_BUILT_EXE and exe_path != LAUNCH_EXECUTABLE.resolve():
        print(f'Autostart path is outdated. Correcting "{exe}" to "{LAUNCH_EXECUTABLE}".')
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
