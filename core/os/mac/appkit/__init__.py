from __future__ import absolute_import
from AppKit import NSScreen
from AppKit import NSEvent


def get_resolution():
    w = NSScreen.mainScreen().frame().size.width
    h = NSScreen.mainScreen().frame().size.height
    return (w, h)


def get_cursor_pos():
    d = NSEvent.mouseLocation()
    return (d.x, d.y)


def get_monitor_locations():
    """Not tested."""
    result = []
    for screen in NSScreen.screens():
        rect = NSScreen.frame(screen)
        x, y = rect.origin.x, rect.origin.y
        width, height = rect.size.width, rect.size.height
        result.append(tuple(map(int, (x, y, x + width, y + height))))
    return result
