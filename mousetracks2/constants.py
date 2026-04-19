import sys
from pathlib import Path
from typing import cast

from contextlib import suppress

import psutil

from .cli import CLI


SYS_EXECUTABLE = Path(sys.executable)

REPO_DIR = Path(__file__).parent.parent

IS_BUILT_EXE = False

# PyInstaller
if hasattr(sys, '_MEIPASS'):
    REPO_DIR = Path(sys._MEIPASS)
    IS_BUILT_EXE = True

# Nuitka
elif '__compiled__' in globals():
    REPO_DIR = Path(sys.executable).parent
    SYS_EXECUTABLE = Path(cast(str, __compiled__.original_argv0))  # type: ignore
    IS_BUILT_EXE = True

if CLI.installed:
    # Expected path
    LAUNCH_EXECUTABLE = SYS_EXECUTABLE.parent / 'MouseTracks.exe'

    # Try to get actual path
    with suppress(psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        current_proc = psutil.Process()
        current_exe = current_proc.exe()
        for parent in current_proc.parents():
            parent_exe = parent.exe()
            if parent_exe != current_exe:
                LAUNCH_EXECUTABLE = Path(parent_exe)
                break

else:
    LAUNCH_EXECUTABLE = SYS_EXECUTABLE
"""The executable that was used to launch MouseTracks."""

if IS_BUILT_EXE:
    EXECUTABLE_DIR = LAUNCH_EXECUTABLE.parent
else:
    EXECUTABLE_DIR = REPO_DIR
"""The location of all other executables."""

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

RADIAL_ARRAY_SIZE = 2048
"""Size to use for gamepad radial arrays."""

DEBUG = True
"""Switch on assertion statements for testing."""

IS_EXE = getattr(sys, 'frozen', False)
"""Determine if running as an executable."""

TRACKING_DISABLE = 'Untracked'
"""Turn off tracking for any applications with this name."""

TRACKING_IGNORE = '<ignore>'
"""Ignore tracking for any applications with this name.
This may be used when specifically excluding a splash screen.
"""

TRACKING_WILDCARD = '<*>'

PACKAGE_IDENTIFIER = 'uk.peterhunt.mousetracks'

UNTRUSTED_EXT = '.skipped'
