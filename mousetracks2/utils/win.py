"""Windows functions.

This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from ctypes import windll, Structure, c_long, byref


class POINT(Structure):
    _fields_ = [('x', c_long), ('y', c_long)]


def cursor_position():
    """Get the current mouse position.

    Returns:
        (x, y) coordinates

    Source: https://stackoverflow.com/a/24567802/2403000
    """
    cursor = POINT()
    windll.user32.GetCursorPos(byref(cursor))
    return (cursor.x, cursor.y)


def main_monitor_resolution():
    """Get the main screen resolution.
    Any secondary screens will be ignored.

    Returns:
        (width, height)
    """
    user32 = windll.user32
    return (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))
