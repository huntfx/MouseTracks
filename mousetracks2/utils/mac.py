"""Mac functions.
Thanks to u/zlft for the code.

This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from AppKit import NSEvent, NSScreen


def cursor_position():
    """Get the current mouse position.

    Returns:
        Tuple of the x and y coordinates of the mouse cursor.
    """
    d = NSEvent.mouseLocation()
    return (d.x, d.y)


def main_monitor_resolution():
    """Get the main screen resolution.
    Any secondary screens will be ignored.

    Returns:
        Tuple of the width and height of the main screen.
    """
    size = NSScreen.mainScreen().frame().size
    return (size.width, size.height)
