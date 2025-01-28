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

BASE_DIR = APPDATA / 'MouseTracks'

DEFAULT_PROFILE_NAME = 'Desktop'

UPDATES_PER_SECOND = 60

DOUBLE_CLICK_MS = 500
"""Maximum time in ms where a double click is valid."""

DOUBLE_CLICK_TOL = 8
"""Maximum pixels where a double click is valid."""

COMPRESSION_THRESHOLD = 425000  # Max: 2 ** 64 - 1
"""How many ticks to trigger track compression."""

COMPRESSION_FACTOR = 1.1
"""How much to compress tracks by."""

INACTIVITY_MS = 1000 * 60 * 5  # 5 mins
"""Time in ms before inactive."""

RADIAL_ARRAY_SIZE = 2048
"""Size to use for gamepad radial arrays."""

DEBUG = True
"""Switch on assertion statements for testing."""

IS_EXE = getattr(sys, 'frozen', False)
"""Determine if running as an executable."""
