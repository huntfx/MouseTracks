"""Linux specific functions.
These are untested and may not work.
"""

from Xlib import display


def monitor_locations() -> list[tuple[int, int, int, int]]:
    """Get the location of each monitor.

    Returns:
        List of (x1, y1, x2, y2) tuples representing monitor bounds.
    """
    monitors = []
    d = display.Display()
    root = d.screen().root
    resources = root.xinerama_query_screens()

    for screen in resources:
        x1, y1 = screen.x_org, screen.y_org
        x2, y2 = x1 + screen.width, y1 + screen.height
        monitors.append((x1, y1, x2, y2))

    return monitors
