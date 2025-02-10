"""MacOS specific functions.
These are untested and may not work.
"""

import Quartz  # type: ignore


def monitor_locations() -> list[tuple[int, int, int, int]]:
    """Get the location of each monitor.

    Returns:
        List of (x1, y1, x2, y2) tuples representing monitor bounds.
    """
    monitors = []
    screen_dict = Quartz.CGDisplayBounds  # Function to get display bounds

    for display in Quartz.CGDisplayActiveList():
        bounds = screen_dict(display)
        x1, y1 = int(bounds.origin.x), int(bounds.origin.y)
        x2, y2 = x1 + int(bounds.size.width), y1 + int(bounds.size.height)
        monitors.append((x1, y1, x2, y2))

    return monitors
