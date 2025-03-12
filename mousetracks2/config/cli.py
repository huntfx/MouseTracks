import argparse
import os
import sys
from pathlib import Path

# Get the appdata folder
# Source: https://github.com/ActiveState/appdirs/blob/master/appdirs.py
match sys.platform:
    case "win32":
        APPDATA = Path(os.path.expandvars('%APPDATA%'))
    case 'darwin':
        APPDATA = Path(os.path.expanduser('~/Library/Application Support/'))
    case _:
        APPDATA = Path(os.getenv('XDG_DATA_HOME', os.path.expanduser("~/.local/share")))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='MouseTracks')
    parser.add_argument('--offline', action='store_true', help='Force offline mode')
    parser.add_argument('--start-hidden', action='store_true', help='Minimise on startup')
    parser.add_argument('--autostart', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--data-dir', type=str, default=str(APPDATA / 'MouseTracks'), help='Specify an alternative data directory')
    parser.add_argument('--no-mouse', action='store_true', help='Disable mouse tracking')
    parser.add_argument('--no-keyboard', action='store_true', help='Disable keyboard tracking')
    parser.add_argument('--no-gamepad', action='store_true', help='Disable gamepad tracking')
    parser.add_argument('--no-network', action='store_true', help='Disable network tracking')
    return parser.parse_args()


_ARGS = parse_args()

OFFLINE: bool = _ARGS.offline

START_HIDDEN: bool = _ARGS.start_hidden

AUTOSTART: bool = _ARGS.autostart

DATA_DIR = Path(_ARGS.data_dir)

DISABLE_MOUSE: bool = _ARGS.no_mouse

DISABLE_KEYBOARD: bool = _ARGS.no_keyboard

DISABLE_GAMEPAD: bool = _ARGS.no_gamepad

DISABLE_NETWORK: bool = _ARGS.no_network
