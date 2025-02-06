"""Mac specific functions.

Special thanks: u/zlft

This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from AppKit import NSEvent, NSScreen


def main_monitor_resolution():
    """Get the main screen resolution.
    Any secondary screens will be ignored.

    Returns:
        Tuple of the width and height of the main screen.
    """
    size = NSScreen.mainScreen().frame().size
    return (size.width, size.height)
