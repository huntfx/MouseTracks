import argparse
import os
import sys
from pathlib import Path
from typing import Callable

from ..version import VERSION

# Get the appdata folder
# Source: https://github.com/ActiveState/appdirs/blob/master/appdirs.py
match sys.platform:
    case 'win32':
        APPDATA = Path(os.path.expandvars('%APPDATA%'))
    case 'darwin':
        APPDATA = Path(os.path.expanduser('~/Library/Application Support/'))
    case _:
        APPDATA = Path(os.getenv('XDG_DATA_HOME', os.path.expanduser('~/.local/share')))


def parse_args(strict: bool = False) -> argparse.Namespace:
    """Parse the command line arguments.

    Parameters:
        strict: Check there are no unrecognised arguments.
            This is not done by default, as both `multiprocessing` and
            `PyInstaller` insert their own custom arguments.
    """
    parser = argparse.ArgumentParser(description='MouseTracks', formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', '--version', action='version', version=f'MouseTracks {VERSION}')
    parser.add_argument('--autostart', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--installed', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--data-dir', type=str, default=str(APPDATA / 'MouseTracks'), help='specify the data directory')
    parser.add_argument('--admin', '--elevate', action='store_true', help='request to run as administrator if not already')

    startup_group = parser.add_argument_group('Startup Options')
    startup_group.set_defaults(start_hidden=None)
    startup_group.add_argument('--start-hidden', dest='start_hidden', action='store_const', const=True, help='minimise to the system tray on startup')
    startup_group.add_argument('--start-visible', dest='start_hidden', action='store_const', const=False, help='make the application visible on startup')
    startup_group.add_argument('--no-splash', action='store_true', help='disable splash screen')

    monitor_group = parser.add_argument_group('Monitor Options')
    monitor_options = monitor_group.add_mutually_exclusive_group()
    monitor_options.set_defaults(multi_monitor=True)
    monitor_options.add_argument('--multi-monitor', action='store_const', const=True, dest='multi_monitor',
                                 help='record monitors as independent displays')
    monitor_options.add_argument('--single-monitor', action='store_const', const=False, dest='multi_monitor',
                                 help='record monitors as one large combined display')

    privacy_group = parser.add_argument_group('Privacy Options')
    privacy_group.add_argument('--offline', action='store_true', help='force offline mode')
    privacy_group.add_argument('--no-mouse', action='store_true', help='disable mouse tracking')
    privacy_group.add_argument('--no-keyboard', action='store_true', help='disable keyboard tracking')
    privacy_group.add_argument('--no-gamepad', action='store_true', help='disable gamepad tracking')
    privacy_group.add_argument('--no-network', action='store_true', help='disable network tracking')

    if strict:
        args = parser.parse_args()
    else:
        args, unknown = parser.parse_known_args()
    return args


def bool2str(value: bool | None) -> str:
    """Convert a value from `bool` / `None` to `str`."""
    if value is None:
        return ''
    return f'{value:d}'


def str2bool(value: str) -> bool:
    """Convert a value from `str` to `bool`."""
    return bool(int(value))


class _CLI:
    """Store all the arguments in environment variables.

    When a new process is spawned, it may not retain `sys.argv`, but it
    does retain all the environment variables. By using `setdefault`,
    this class ensures that the values are set by the parent process and
    read by the child processes.
    """

    def __init__(self) -> None:
        self._soft_load = False
        self._load_args()

    def _load_args(self) -> None:
        """Load in the command line arguments.

        When a new process is spawned, it may not retain `sys.argv`,
        but it does retain all the environment variables. By enabling
        the "soft load", this ensures that the values are set by the
        parent process and read by the child processes instead of being
        overwritten.
        """
        args = parse_args()

        # Load in default values
        self._soft_load = True
        try:
            self.data_dir = Path(args.data_dir)
            self.start_hidden = None
            self.offline = False
            self.autostart = False
            self.installed = False
            self.disable_splash = False
            self.disable_mouse = False
            self.disable_keyboard = False
            self.disable_gamepad = False
            self.disable_network = False
            self.elevate = False
            self.single_monitor = False
            self.multi_monitor = True

        finally:
            self._soft_load = False

        # Only update if the value is different to the default
        if args.data_dir != str(APPDATA / 'MouseTracks'):
            self.data_dir = Path(args.data_dir)
        if args.start_hidden is not None:
            self.start_hidden = args.start_hidden
        if args.offline:
            self.offline = True
        if args.autostart:
            self.autostart = True
        if args.installed:
            self.installed = True
        if args.admin:
            self.elevate = True
        if args.no_splash:
            self.disable_splash = True
        if args.no_mouse:
            self.disable_mouse = True
        if args.no_keyboard:
            self.disable_keyboard = True
        if args.no_gamepad:
            self.disable_gamepad = True
        if args.no_network:
            self.disable_network = True
        if not args.multi_monitor:
            self.single_monitor = True
            self.multi_monitor = False

    @property
    def _set(self) -> Callable:
        """Return a function to set an environment value."""
        if self._soft_load:
            return os.environ.setdefault
        return os.environ.__setitem__

    @property
    def offline(self) -> bool:
        """Force offline mode so that no connections are ever made."""
        return str2bool(os.environ['MT_OFFLINE'])

    @offline.setter
    def offline(self, value: bool) -> None:
        """Set offline mode."""
        self._set('MT_OFFLINE', bool2str(value))

    @property
    def start_hidden(self) -> bool | None:
        """Start the application as hidden."""
        value = os.environ.get('MT_START_HIDDEN')
        return str2bool(value) if value else None

    @start_hidden.setter
    def start_hidden(self, value: bool | None) -> None:
        """Set if the application should be started as hidden."""
        if value is not None:
            self._set('MT_START_HIDDEN', bool2str(value))

    @property
    def autostart(self) -> bool:
        """Flag when automatically launched at startup."""
        return str2bool(os.environ['MT_AUTOSTART'])

    @autostart.setter
    def autostart(self, value: bool) -> None:
        """Set autostart mode."""
        self._set('MT_AUTOSTART', bool2str(value))

    @property
    def data_dir(self) -> Path:
        """Get the data directory path."""
        return Path(os.environ['MT_DATA_DIR'])

    @data_dir.setter
    def data_dir(self, value: Path) -> None:
        """Set the data directory path."""
        self._set('MT_DATA_DIR', str(value))

    @property
    def disable_splash(self) -> bool:
        """Disable the splash screen."""
        return str2bool(os.environ['MT_DISABLE_SPLASH'])

    @disable_splash.setter
    def disable_splash(self, value: bool) -> None:
        """Set the splash screen disabled state."""
        self._set('MT_DISABLE_SPLASH', bool2str(value))

    @property
    def disable_mouse(self) -> bool:
        """Disable mouse tracking."""
        return str2bool(os.environ['MT_DISABLE_MOUSE'])

    @disable_mouse.setter
    def disable_mouse(self, value: bool) -> None:
        """Set mouse tracking disabled state."""
        self._set('MT_DISABLE_MOUSE', bool2str(value))

    @property
    def disable_keyboard(self) -> bool:
        """Disable keyboard tracking."""
        return str2bool(os.environ['MT_DISABLE_KEYBOARD'])

    @disable_keyboard.setter
    def disable_keyboard(self, value: bool) -> None:
        """Set keyboard tracking disabled state."""
        self._set('MT_DISABLE_KEYBOARD', bool2str(value))

    @property
    def disable_gamepad(self) -> bool:
        """Disable gamepad tracking."""
        return str2bool(os.environ['MT_DISABLE_GAMEPAD'])

    @disable_gamepad.setter
    def disable_gamepad(self, value: bool) -> None:
        """Set gamepad tracking disabled state."""
        self._set('MT_DISABLE_GAMEPAD', bool2str(value))

    @property
    def disable_network(self) -> bool:
        """Disable network tracking."""
        return str2bool(os.environ['MT_DISABLE_NETWORK'])

    @disable_network.setter
    def disable_network(self, value: bool) -> None:
        """Set network tracking disabled state."""
        self._set('MT_DISABLE_NETWORK', bool2str(value))

    @property
    def elevate(self) -> bool:
        """Run with elevated privileges."""
        return str2bool(os.environ['MT_ELEVATE'])

    @elevate.setter
    def elevate(self, value: bool) -> None:
        """Set elevated mode."""
        self._set('MT_ELEVATE', bool2str(value))

    @property
    def single_monitor(self) -> bool:
        """Treat all monitors as a single monitor."""
        value = os.environ['MT_SINGLE_MONITOR']
        return str2bool(value)

    @single_monitor.setter
    def single_monitor(self, value: bool) -> None:
        """Set single monitor mode."""
        self._set('MT_SINGLE_MONITOR', bool2str(value))

    @property
    def multi_monitor(self) -> bool:
        """Handle each monitor separately."""
        value = os.environ['MT_MULTI_MONITOR']
        return str2bool(value)

    @multi_monitor.setter
    def multi_monitor(self, value: bool) -> None:
        """Set multi monitor mode."""
        self._set('MT_MULTI_MONITOR', bool2str(value))

    @property
    def installed(self) -> bool:
        """Determine if running installed or portable."""
        value = os.environ['MT_INSTALLED']
        return str2bool(value)

    @installed.setter
    def installed(self, value: bool) -> None:
        """Set if running installed or portable."""
        self._set('MT_INSTALLED', bool2str(value))


CLI = _CLI()
