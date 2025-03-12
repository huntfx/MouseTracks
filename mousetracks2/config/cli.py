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
    parser = argparse.ArgumentParser(description="MouseTracks Application")
    parser.add_argument('--offline', action='store_true', help='Run in offline mode')
    parser.add_argument('--start-hidden', action='store_true', help='Minimise on startup')
    parser.add_argument('--autostart', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--data-dir', type=str, default=str(APPDATA / 'MouseTracks'), help='Specify an alternative data directory.')
    return parser.parse_args()


_ARGS = parse_args()

OFFLINE: bool = _ARGS.offline

START_HIDDEN: bool = _ARGS.start_hidden

AUTOSTART: bool = _ARGS.autostart

DATA_DIR = Path(_ARGS.data_dir)
