"""Linux functions.
Thanks to u/Astrrum for the code.

This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from Xlib.display import Display


def cursor_position():
    """Get the current mouse position.

    Returns:
        Tuple of the x and y coordinates of the mouse cursor.
    """
    d = Display().screen().root.query_pointer()
    return (d.root_x, d.root_y)


def main_monitor_resolution():
    """Get the main screen resolution.
    Any secondary screens will be ignored.

    Returns:
        (width, height)
    """
    d = Display().screen()
    return (d.width_in_pixels, d.height_in_pixels)
