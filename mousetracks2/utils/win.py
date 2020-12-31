"""Windows specific functions.

This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

import win32api
import win32con


def cursor_position():
    """Get the current mouse position.

    Returns:
        (x, y) as integers
        None in the case of any error
    """
    try:
        return win32api.GetCursorPos()
    except win32api.error:
        return None


def main_monitor_resolution():
    """Get the main screen resolution.
    Any secondary screens will be ignored.

    Returns:
        (width, height) as integers
    """
    return (win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
            win32api.GetSystemMetrics(win32con.SM_CYSCREEN))


def get_monitor_locations():
    """Get the location of each monitor.

    Returns:
        ((x1, y1, x2, y2),) as 4 integers for each monitor
    """
    return tuple(m[2] for m in win32api.EnumDisplayMonitors())


def check_key_press(key):
    """Check if a key is being pressed.
    This also supports mouse clicks using win32con.VK_[L/M/R]BUTTON.

    Returns:
        True/False if the selected key has been pressed or not.
    """
    return win32api.GetKeyState(key) < 0
