from __future__ import annotations

import sys
import traceback
from contextlib import suppress
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Callable, TypeVar

if TYPE_CHECKING:
    import tkinter as tk


T = TypeVar('T')


def _get_ghost_root() -> tk.Tk:
    """Create an invisible root window that still appears in the taskbar."""
    import tkinter as tk

    root = tk.Tk()
    root.title('MouseTracks')
    root.geometry('0x0')

    # Make it completely transparent (Supported on Win/Mac, gracefully fails on unsupported Linux)
    with suppress(tk.TclError):
        root.attributes('-alpha', 0.0)

    # Automatically grab the executable's icon
    if sys.platform == 'win32':
        with suppress(tk.TclError):
            root.iconbitmap(default=sys.executable)

    root.eval('tk::PlaceWindow . center')
    root.attributes('-topmost', True)
    root.focus_force()

    return root


def _unhide_console() -> None:
    """Attempt to unhide the Windows console."""
    if sys.platform != 'win32':
        return
    with suppress(Exception):
        from .utils.system.windows import WindowHandle, get_window_handle
        handle = WindowHandle(get_window_handle(console=True))
        if handle is not None and handle.pid and handle.title:
            handle.show()


def _prompt_yes_no(prompt: str) -> bool:
    """Ask a yes/no question via the console."""
    while True:
        match input(prompt).strip().lower():
            case 'y' | '':
                return True
            case 'n':
                return False


def _run_dialog(tk_action: Callable[[], T], console_action: Callable[[], T]) -> T:
    """Attempt to run a Tkinter dialog, falling back to the console if it fails."""
    try:
        root = _get_ghost_root()
        result = tk_action()
        root.destroy()
        return result

    except Exception:  # pylint: disable=broad-except
        _unhide_console()
        return console_action()


def show_error_dialog(exc_type: type[BaseException], exc_val: BaseException, exc_tb: TracebackType) -> bool:
    """Show a GUI error dialog.
    Returns True if a restart was requested.
    """
    full_traceback = ''.join(traceback.format_exception(exc_type, exc_val, exc_tb)).rstrip('\n')
    short_error = f'{exc_type.__name__}: {exc_val}'

    truncated_tb = full_traceback
    if len(truncated_tb) > 1500:
        truncated_tb = truncated_tb[-1500:] + '\n... (truncated)'

    # Base console prints happen unconditionally
    print(full_traceback)
    print('MouseTracks encountered an unexpected error and shut down.')

    def tk_action() -> bool:
        from tkinter import messagebox
        copy_msg = 'Press Ctrl+C to copy this error.\n\n' if sys.platform == 'win32' else ''
        prompt = (
            f'{short_error}\n\n'
            '--- Traceback ---\n'
            f'{truncated_tb}\n'
            '-----------------\n\n'
            f'{copy_msg}'
            'Would you like to launch MouseTracks again?'
        )
        return messagebox.askretrycancel(
            title='MouseTracks Crash Reporter',
            message='MouseTracks encountered an unexpected error and shut down.',
            detail=prompt,
            icon=messagebox.ERROR,
        )

    def console_action() -> bool:
        return _prompt_yes_no('Would you like to restart MouseTracks? [Y/n] ')

    return _run_dialog(tk_action, console_action)


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

    def tk_action() -> bool:
        from tkinter import messagebox
        return messagebox.askokcancel(
            title='MouseTracks',
            message=message,
            detail=f'{detail}\n\nPress OK to ignore this warning and continue.',
        )

    def console_action() -> bool:
        return _prompt_yes_no('Would you like to ignore this warning and continue? [Y/n] ')

    return _run_dialog(tk_action, console_action)


def show_already_running_dialog(data_dir: Path | str) -> None:
    """Show a GUI error dialog when another instance is already running."""
    message = 'Error: Another instance of MouseTracks is already running.'
    detail = f'The application cannot start because the following data directory is already being written to:\n{data_dir}'

    print(message)
    print(f'Locked path: "{data_dir}"')

    def tk_action() -> None:
        from tkinter import messagebox
        messagebox.showerror(
            title='MouseTracks',
            message=message,
            detail=detail,
        )

    def console_action() -> None:
        input('Press enter to exit...')

    return _run_dialog(tk_action, console_action)
