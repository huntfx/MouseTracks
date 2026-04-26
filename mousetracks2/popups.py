import sys
import traceback
from contextlib import suppress
from pathlib import Path
from types import TracebackType


def _get_ghost_root():
    """Create an invisible root window that still appears in the taskbar."""
    import tkinter as tk

    root = tk.Tk()
    root.title('MouseTracks')
    root.geometry('0x0')

    # Make it completely transparent (Supported on Win/Mac, gracefully fails on unsupported Linux)
    with suppress(tk.TclError):
        root.attributes('-alpha', 0.0)

    root.eval('tk::PlaceWindow . center')
    root.attributes('-topmost', True)
    root.focus_force()

    return root


def show_error_dialog(exc_type: type[BaseException], exc_val: BaseException, exc_tb: TracebackType) -> bool:
    """Show a GUI error dialog.
    If it fails to launch, the console will be used instead.

    Returns True if a restart was requested.
    """
    full_traceback = ''.join(traceback.format_exception(exc_type, exc_val, exc_tb)).rstrip('\n')
    short_error = f'{exc_type.__name__}: {exc_val}'

    # Truncate traceback to prevent breaking native OS dialogs
    truncated_tb = full_traceback
    if len(truncated_tb) > 1500:
        truncated_tb = truncated_tb[-1500:] + '\n... (truncated)'

    # Print it out to the console before doing anything else
    print(full_traceback)
    print('MouseTracks encountered an unexpected error and shut down.')

    # Try to launch the GUI
    try:
        from tkinter import messagebox

        # Create a hidden root window so only the dialog shows
        root = _get_ghost_root()

        # Build the text for the dialog
        copy_msg = 'Press Ctrl+C to copy this error.\n\n' if sys.platform == 'win32' else ''
        prompt = (
            f'{short_error}\n\n'
            '--- Traceback ---\n'
            f'{truncated_tb}\n'
            '-----------------\n\n'
            f'{copy_msg}'
            'Would you like to launch MouseTracks again?'
        )

        # Use the native OS dialog
        result = messagebox.askretrycancel(
            title='MouseTracks Crash Reporter',
            message='MouseTracks encountered an unexpected error and shut down.',
            detail=prompt,
            icon=messagebox.ERROR,
        )

        root.destroy()
        return result

    # Catch ImportError (no tk installed) or tk.TclError (headless Linux with no display)
    except Exception:  # pylint: disable=broad-except

        # Ensure the console is visible
        if sys.platform == 'win32':
            with suppress(Exception):
                from .utils.system.windows import WindowHandle, get_window_handle
                handle = WindowHandle(get_window_handle(console=True))
                if handle is not None and handle.pid and handle.title:
                    handle.show()

        # Ask the user to restart
        while True:
            choice = input('Would you like to restart MouseTracks? [Y/n] ').strip().lower()
            match choice:
                case 'y' | '':
                    return True
                case 'n':
                    return False


def show_temp_warning_dialog() -> bool:
    """Show a GUI warning when running from a temporary directory.
    If it fails to launch, the console will be used instead.
    """
    message = 'Warning: MouseTracks is running from a temporary folder.'
    detail = (
        'Any settings or tracks saved during this session will be lost '
        'when the application closes.\n\n'
        'To save your data permanently, please extract the application '
        'from the ZIP file into a normal folder before running it.'
    )

    # Print to console as a baseline
    print(message)
    print(detail.replace('\n\n', '\n'))

    # Try to launch the GUI
    try:
        from tkinter import messagebox

        # Create a hidden root window so only the dialog shows
        root = _get_ghost_root()

        # Use the native OS warning dialog
        result = messagebox.askokcancel(
            title='MouseTracks Portable',
            message=message,
            detail=f'{detail}\n\nPress OK to ignore this warning and continue.',
        )

        root.destroy()
        return result

    # Catch ImportError (no tk installed) or tk.TclError (headless Linux with no display)
    except Exception:  # pylint: disable=broad-except

        # Ensure the console is visible
        if sys.platform == 'win32':
            with suppress(Exception):
                from .utils.system.windows import WindowHandle, get_window_handle
                handle = WindowHandle(get_window_handle(console=True))
                if handle is not None and handle.pid and handle.title:
                    handle.show()

        while True:
            choice = input('Would you like to ignore this warning and continue? [Y/n] ').strip().lower()
            match choice:
                case 'y' | '':
                    return True
                case 'n':
                    return False


def show_already_running_dialog(data_dir: Path | str) -> None:
    """Show a GUI error dialog when another instance is already running.
    If it fails to launch, the console will be used instead.
    """
    message = 'Error: Another instance of MouseTracks is already running.'
    detail = f'The application cannot start because the following data directory is already being written to:\n{data_dir}'

    # Print to console as a baseline
    print(message)
    print(f'Locked path: "{data_dir}"')

    # Try to launch the GUI
    try:
        from tkinter import messagebox

        # Create a hidden root window so only the dialog shows
        root = _get_ghost_root()

        # Use the native OS error dialog
        messagebox.showerror(
            title='MouseTracks',
            message=message,
            detail=detail,
        )

        root.destroy()

    # Catch ImportError (no tk installed) or tk.TclError (headless Linux with no display)
    except Exception:  # pylint: disable=broad-except

        # Ensure the console is visible
        if sys.platform == 'win32':
            with suppress(Exception):
                from .utils.system.windows import WindowHandle, get_window_handle
                handle = WindowHandle(get_window_handle(console=True))
                if handle is not None and handle.pid and handle.title:
                    handle.show()

        # Pause execution before the app abruptly exits
        input('Press enter to exit...')
