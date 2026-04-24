import shlex
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Type

from . import base
from ...context import Context, CTX
from ...runtime import IS_BUILT_EXE

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
    """Check if remapping the executable is required.
    This is in case a user downloads a new version.
    It is only designed to run for built executables.

    It will not remap if the existing autostart is for the installed
    application, or if the data directory doesn't match.
    """
    # Skip if running directly from Python
    if not IS_BUILT_EXE:
        return False

    # Get the parts from the existing command
    exe, args = split_autostart(cmd)

    # Skip if autostart is currently disabled
    if exe is None:
        return False

    saved_ctx = Context(args, group=__name__)

    # Skip if MouseTracks was installed as the launcher takes highest priority
    if saved_ctx.installed:
        print('Skipping autostart remap, was set by installed launcher executable')
        return False

    # Skip if data dir has changed
    if CTX.data_dir != saved_ctx.data_dir:
        print(f'Skipping autostart remap, current data dir does not match "{saved_ctx.data_dir}"')
        return False

    # Update the path to the current portable executable
    exe_path = Path(exe.strip('"')).resolve()
    if exe_path != CTX.launch_executable:
        print(f'Autostart path is outdated. Correcting "{exe}" to "{CTX.launch_executable}".')
        set_autostart(*args, ignore_args=('--start-hidden', '--start-visible'))
        return True

    print('Skipping autostart remap, executable and data dir match')
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
