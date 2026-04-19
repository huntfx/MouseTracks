import os
import sys
from pathlib import Path
from typing import cast
from contextlib import suppress

import psutil

from .cli import CLI


SYS_EXECUTABLE = Path(sys.executable)
"""The current python executable."""

REPO_DIR = Path(__file__).parent.parent
"""The location of the repository root."""

IS_BUILT_EXE = False
"""If the application is running as a built executable.
Supports both PyInstaller and Nuitka.
"""

IS_EXE = getattr(sys, 'frozen', False)
"""If the application is running as an executable.
Possible deprecated for `IS_BUILT_EXE`.
"""

# Pyinstaller overrides
if hasattr(sys, '_MEIPASS'):
    REPO_DIR = Path(sys._MEIPASS)
    IS_BUILT_EXE = True

# Nuitka overrides
elif '__compiled__' in globals():
    REPO_DIR = Path(sys.executable).parent
    SYS_EXECUTABLE = Path(cast(str, __compiled__.original_argv0))  # type: ignore
    IS_BUILT_EXE = True

# Current Dir Resolution
CURRENT_DIR = SYS_EXECUTABLE.parent if IS_BUILT_EXE else REPO_DIR
"""The current directory the app is being run from."""

if CLI.installed:
    LAUNCH_EXECUTABLE = SYS_EXECUTABLE.parent / 'MouseTracks.exe'
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

EXECUTABLE_DIR = LAUNCH_EXECUTABLE.parent if IS_BUILT_EXE else REPO_DIR
"""The location of all other executables."""

match sys.platform:
    case 'win32':
        APPDATA = Path(os.path.expandvars('%APPDATA%'))
    case 'darwin':
        APPDATA = Path(os.path.expanduser('~/Library/Application Support/'))
    case _:
        APPDATA = Path(os.getenv('XDG_DATA_HOME', os.path.expanduser('~/.local/share')))
"""The AppData folder.
Source: https://github.com/ActiveState/appdirs/blob/master/appdirs.py
"""

if CLI.data_dir is None:
    if CLI.portable:
        DATA_DIR = CURRENT_DIR / '.mousetracks'
    else:
        DATA_DIR = APPDATA / 'MouseTracks'
else:
    DATA_DIR = CLI.data_dir
"""Where to save the data."""
