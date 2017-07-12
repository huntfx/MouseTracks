from AppKit import NSScreen
from AppKit import NSEvent


def get_resolution():
    w = NSScreen.mainScreen().frame().size.width
    h = NSScreen.mainScreen().frame().size.height
    return (w, h)
 
 
def get_cursor_pos():
    d = NSEvent.mouseLocation()
    return (d.x, d.y)
