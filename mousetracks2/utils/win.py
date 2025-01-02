"""Windows specific functions.

This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from contextlib import contextmanager
from typing import Optional

import pywintypes
import win32api
import win32con
import win32console
import win32gui
import win32process


MOUSE_BUTTONS = (win32con.VK_LBUTTON, win32con.VK_MBUTTON, win32con.VK_RBUTTON)


def cursor_position() -> Optional[tuple[int, int]]:
    """Get the current mouse position.

    Returns:
        (x, y) as integers
        None in the case of any error
    """
    try:
        return win32api.GetCursorPos()
    except win32api.error:
        return None


def main_monitor_resolution() -> tuple[int, int]:
    """Get the main screen resolution.
    Any secondary screens will be ignored.
    """
    return (win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
            win32api.GetSystemMetrics(win32con.SM_CYSCREEN))


def monitor_locations() -> list[tuple[int, int, int, int]]:
    """Get the location of each monitor.

    Returns:
        (x1, y1, x2, y2) for each monitor
    """
    return [m[2] for m in win32api.EnumDisplayMonitors()]


def check_key_press(key: int) -> bool:
    """Check if a key is being pressed.
    This also supports mouse clicks using win32con.VK_[L/M/R]BUTTON.

    Returns:
        True/False if the selected key has been pressed or not.
    """
    return win32api.GetKeyState(key) < 0


