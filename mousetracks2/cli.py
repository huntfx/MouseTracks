import argparse
import os
import sys
from pathlib import Path
from typing import Callable, Sequence

from .version import VERSION



def parse_args(args: Sequence[str] | None = None, strict: bool = False) -> argparse.Namespace:
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
    parser.add_argument('--launcher', type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument('--post-install', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--data-dir', type=str, default=None, help='specify the data directory')
    parser.add_argument('--admin', '--elevate', action='store_true', help='request to run as administrator if not already')
    parser.add_argument('--portable', action='store_true', help='run as portable (save data next to executable)')
    parser.add_argument('--disable-temp-warning', action='store_true', help='disable the startup warning message when saving to the temporary directory')

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

    parser.add_argument('--generate-keys', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--write-public-key', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--show-public-key', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--sign-executable', metavar='PATH', help=argparse.SUPPRESS)
    parser.add_argument('--verify-executable', metavar='PATH', help=argparse.SUPPRESS)

    parser.add_argument('--debug-get-autostart', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--debug-remap-autostart', action='store_true', help=argparse.SUPPRESS)

    if strict:
        result = parser.parse_args(args)
    else:
        result, _unknown = parser.parse_known_args(args)
    return result


def bool2str(value: bool | None) -> str:
    """Convert a value from `bool` / `None` to `str`."""
    if value is None:
        return ''
    return f'{value:d}'


def str2bool(value: str) -> bool:
    """Convert a value from `str` to `bool`."""
    return bool(int(value))


class EnvGroup:
    """Light wrapper for `os.environ` to allow value groups.
    This is purpose built for the `CLI` class and is not complete
    enough to be used anywhere else.
    """

    SEP = '::'

    def __init__(self, group: str) -> None:
        self.env = os.environ
        self.group = group.replace(self.SEP, '.')

    def decode(self, data: str) -> dict[str | None, str]:
        """Build a dict from an env string.

        If there are any ungrouped items, they will also be applied to
        the current group, as it's likely these were set outside of MT.
        """
        result: dict[str | None, str] = {}
        for item in data.split(os.pathsep):
            try:
                group, value = item.split(self.SEP, 1)
            except ValueError:
                result[None] = item
                # Value was set outside of EnvGroup, so apply to current group
                if self.group not in result:
                    result[self.group] = item
            else:
                result[group] = value
        return result

    def encode(self, data: dict[str | None, str]) -> str:
        """Convert the env data back to its string form."""
        return os.pathsep.join(f'{k}{self.SEP}{v}' if k is not None else v for k, v in data.items())

    def __getitem__(self, key: str) -> str:
        """Get data for a key in the current group."""
        if key not in self.env:
            raise KeyError(key)
        data = self.decode(self.env[key])
        if self.group in data:
            return data[self.group]
        raise KeyError(key)

    def get(self, key: str) -> str | None:
        """Get data for a key in the current group."""
        if key not in self.env:
            return None
        data = self.decode(self.env[key])
        return data.get(self.group)

    def __setitem__(self, key: str, value: str) -> None:
        """Set data for a key in the current group."""
        if key in self.env:
            data = self.decode(os.environ[key])
        else:
            data = {}
        data[self.group] = value
        self.env[key] = self.encode(data)

    def setdefault(self, key: str, value: str) -> None:
        """Set default data for a key in the current group."""
        if key in self.env:
            data = self.decode(os.environ[key])
        else:
            data = {}
        data.setdefault(self.group, value)
        self.env[key] = self.encode(data)


class CLI:
    """Store all the arguments in environment variables.

    When a new process is spawned, it may not retain `sys.argv`, but it
    does retain all the environment variables. By using `setdefault`,
    this class ensures that the values are set by the parent process and
    read by the child processes.
    """

    def __init__(self, args: Sequence[str] | None = None, group: str = __name__) -> None:
        self._soft_load = False
        self._args = args
        self.env = EnvGroup(group)
        self.args = self._load_args()

    def _load_args(self) -> argparse.Namespace:
        """Load in the command line arguments.

        When a new process is spawned, it may not retain `sys.argv`,
        but it does retain all the environment variables. By enabling
        the "soft load", this ensures that the values are set by the
        parent process and read by the child processes instead of being
        overwritten.
        """
        args = parse_args(self._args)

        # Load in default values
        self._soft_load = True
        try:
            self.data_dir = None
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
            self.post_install = False
            self.portable = False
            self.disable_temp_warning = False

        finally:
            self._soft_load = False

        # Only update if the value is different to the default
        if args.data_dir is not None:
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
        if args.post_install:
            self.post_install = True
        if args.portable:
            self.portable = True
        if args.disable_temp_warning:
            self.disable_temp_warning = True

        return args

    @property
    def _set(self) -> Callable:
        """Return a function to set an environment value."""
        if self._soft_load:
            return self.env.setdefault
        return self.env.__setitem__

    @property
    def offline(self) -> bool:
        """Force offline mode so that no connections are ever made."""
        return str2bool(self.env['MT_OFFLINE'])

    @offline.setter
    def offline(self, value: bool) -> None:
        """Set offline mode."""
        self._set('MT_OFFLINE', bool2str(value))

    @property
    def start_hidden(self) -> bool | None:
        """Start the application as hidden."""
        value = self.env.get('MT_START_HIDDEN')
        return str2bool(value) if value else None

    @start_hidden.setter
    def start_hidden(self, value: bool | None) -> None:
        """Set if the application should be started as hidden."""
        if value is not None:
            self._set('MT_START_HIDDEN', bool2str(value))

    @property
    def autostart(self) -> bool:
        """Flag when automatically launched at startup."""
        return str2bool(self.env['MT_AUTOSTART'])

    @autostart.setter
    def autostart(self, value: bool) -> None:
        """Set autostart mode."""
        self._set('MT_AUTOSTART', bool2str(value))

    @property
    def data_dir(self) -> Path | None:
        """Get the data directory path."""
        data_dir = self.env['MT_DATA_DIR']
        if data_dir:
            return Path(data_dir)
        return None

    @data_dir.setter
    def data_dir(self, value: Path) -> None:
        """Set the data directory path."""
        self._set('MT_DATA_DIR', str(value) if value else '')

    @property
    def disable_splash(self) -> bool:
        """Disable the splash screen."""
        return str2bool(self.env['MT_DISABLE_SPLASH'])

    @disable_splash.setter
    def disable_splash(self, value: bool) -> None:
        """Set the splash screen disabled state."""
        self._set('MT_DISABLE_SPLASH', bool2str(value))

    @property
    def disable_mouse(self) -> bool:
        """Disable mouse tracking."""
        return str2bool(self.env['MT_DISABLE_MOUSE'])

    @disable_mouse.setter
    def disable_mouse(self, value: bool) -> None:
        """Set mouse tracking disabled state."""
        self._set('MT_DISABLE_MOUSE', bool2str(value))

    @property
    def disable_keyboard(self) -> bool:
        """Disable keyboard tracking."""
        return str2bool(self.env['MT_DISABLE_KEYBOARD'])

    @disable_keyboard.setter
    def disable_keyboard(self, value: bool) -> None:
        """Set keyboard tracking disabled state."""
        self._set('MT_DISABLE_KEYBOARD', bool2str(value))

    @property
    def disable_gamepad(self) -> bool:
        """Disable gamepad tracking."""
        return str2bool(self.env['MT_DISABLE_GAMEPAD'])

    @disable_gamepad.setter
    def disable_gamepad(self, value: bool) -> None:
        """Set gamepad tracking disabled state."""
        self._set('MT_DISABLE_GAMEPAD', bool2str(value))

    @property
    def disable_network(self) -> bool:
        """Disable network tracking."""
        return str2bool(self.env['MT_DISABLE_NETWORK'])

    @disable_network.setter
    def disable_network(self, value: bool) -> None:
        """Set network tracking disabled state."""
        self._set('MT_DISABLE_NETWORK', bool2str(value))

    @property
    def elevate(self) -> bool:
        """Run with elevated privileges."""
        return str2bool(self.env['MT_ELEVATE'])

    @elevate.setter
    def elevate(self, value: bool) -> None:
        """Set elevated mode."""
        self._set('MT_ELEVATE', bool2str(value))

    @property
    def portable(self) -> bool:
        """If running as a portable application."""
        return str2bool(self.env['MT_PORTABLE'])

    @portable.setter
    def portable(self, value: bool) -> None:
        """Set as a portable application."""
        self._set('MT_PORTABLE', bool2str(value))

    @property
    def single_monitor(self) -> bool:
        """Treat all monitors as a single monitor."""
        value = self.env['MT_SINGLE_MONITOR']
        return str2bool(value)

    @single_monitor.setter
    def single_monitor(self, value: bool) -> None:
        """Set single monitor mode."""
        self._set('MT_SINGLE_MONITOR', bool2str(value))

    @property
    def multi_monitor(self) -> bool:
        """Handle each monitor separately."""
        value = self.env['MT_MULTI_MONITOR']
        return str2bool(value)

    @multi_monitor.setter
    def multi_monitor(self, value: bool) -> None:
        """Set multi monitor mode."""
        self._set('MT_MULTI_MONITOR', bool2str(value))

    @property
    def installed(self) -> bool:
        """Determine if running installed or portable."""
        value = self.env['MT_INSTALLED']
        return str2bool(value)

    @installed.setter
    def installed(self, value: bool) -> None:
        """Set if running installed or portable."""
        self._set('MT_INSTALLED', bool2str(value))

    @property
    def post_install(self) -> bool:
        """Determine if running straight after being installed."""
        value = self.env['MT_POST_INSTALL']
        return str2bool(value)

    @post_install.setter
    def post_install(self, value: bool) -> None:
        """Set if running straight after being installed."""
        self._set('MT_POST_INSTALL', bool2str(value))

    @property
    def disable_temp_warning(self) -> bool:
        """Determine if the temp drive warning should be disabled."""
        value = self.env['MT_DISABLE_TMP_WARNING']
        return str2bool(value)

    @disable_temp_warning.setter
    def disable_temp_warning(self, value: bool) -> None:
        """Set if the temp drive warning is disabled."""
        self._set('MT_DISABLE_TMP_WARNING', bool2str(value))


def run_cli_function(cli: CLI) -> bool:
    # pylint: disable=import-outside-toplevel
    """Run a single function and quit."""
    match cli.args:
        case argparse.Namespace(show_public_key=True) if sys.platform == 'win32':
            from .sign import get_runtime_public_key

            public_key = get_runtime_public_key()
            print(public_key.decode('utf-8') if public_key else '')

        case argparse.Namespace(sign_executable=path) if path and sys.platform == 'win32':
            from .sign import sign_executable, verify_signature

            # Only sign if verification fails, to not double up
            if verify_signature(path, write_untrusted=False):
                print(f'Executable is already signed: {path}')
            else:
                sign_executable(path)

            # Ensure the new signature is valid
            assert verify_signature(path, write_untrusted=False)

        case argparse.Namespace(verify_executable=path) if path and sys.platform == 'win32':
            from .sign import verify_signature

            if verify_signature(path, write_untrusted=False):
                print(f'{path} signature passed verification')
            else:
                print(f'{path} signature failed verification')

        case argparse.Namespace(generate_keys=True) if sys.platform == 'win32':
            from .sign import generate_keys
            generate_keys()

        case argparse.Namespace(write_public_key=True) if sys.platform == 'win32':
            from .sign import write_public_key_to_py
            write_public_key_to_py()

        case argparse.Namespace(debug_get_autostart=True):
            from .utils.system import get_autostart
            print(f'Autostart command: {get_autostart()}')

        case argparse.Namespace(debug_remap_autostart=True):
            from .utils.system import remap_autostart
            result = remap_autostart()
            print(f'Remapped autostart: {result}')

        case _:
            return False
    return True
