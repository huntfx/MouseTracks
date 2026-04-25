import sys
import traceback
from contextlib import suppress
from types import TracebackType


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
        import tkinter as tk
        from tkinter import messagebox

        # Create a hidden root window so only the dialog shows
        root = tk.Tk()
        root.withdraw()

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
                from .system.windows import WindowHandle, get_window_handle
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
