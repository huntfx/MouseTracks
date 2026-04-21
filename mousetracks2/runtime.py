import os
import sys
from pathlib import Path
from typing import cast


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
Possibly deprecated for `IS_BUILT_EXE`.
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
