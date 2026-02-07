"""Entry point for the installed executable.
Portable executables bypass this file.
"""

import ctypes
import sys
import subprocess

from mousetracks2.utils.update import get_local_executables
from mousetracks2.constants import APP_EXECUTABLE
from mousetracks2.sign import verify_signature


MB_ICONERROR = 0x10


def show_error(title: str, message: str) -> None:
    """Displays an error message box.
    Currently only supports Windows.
    """
    ctypes.windll.user32.MessageBoxW(0, message, title, MB_ICONERROR)


def main() -> None:
    base_dir = APP_EXECUTABLE.parent

    # Build an ordered list of available executables
    lower, current, higher = get_local_executables(base_dir)
    executables = list(lower)
    if current is not None:
        executables.append(current)
    executables.extend(higher)

    # Get the latest version that passes the signature verification
    try:
        executable = next(filter(verify_signature, reversed(executables)))
    except StopIteration:
        show_error('Launch Error',
                    'No valid version of MouseTracks found in the installation folder.\n\n'
                    'Please reinstall the application.')
        sys.exit(1)

    print(f'Launching {executable}...')

    # Start the child process
    cmd = [str(executable)]
    if '--installed' not in sys.argv:
        cmd.append('--installed')
    cmd.extend(sys.argv[1:])
    try:
        exit_code = subprocess.call(cmd, cwd=base_dir)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        sys.exit(1)
    except OSError as e:
        show_error('Launch Error', f'Failed to start application:\n{e}')
        sys.exit(1)


if __name__ == "__main__":
    main()
