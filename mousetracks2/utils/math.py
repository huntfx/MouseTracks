"""General math functions.

This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import division

from typing import Optional


def calculate_distance(p1: tuple[int, int], p2: Optional[tuple[int, int]]) -> float:
    """Find the distance between two (x, y) coordinates."""
    if p2 is None or p1 == p2:
        return 0.0
    return ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5


def calculate_line(start: tuple[int, int], end: Optional[tuple[int, int]]) -> list[tuple[int, int]]:
    """Calculates path in terms of pixels between two points.
    Uses Bresenham's Line Algorithm.
    """
    if end is None or start == end:
        return []

    x1, y1 = start
    x2, y2 = end
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1

    err = dx - dy
    result = []

    while (x1, y1) != (x2, y2):
        # Step forward in the line
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy

        result.append((x1, y1))

    return result


def calculate_circle(radius, segments=(True, True, True, True)):
    """Get the area and outline of a circle as pixels.
    Optionally pass in which segment is needed, as a tuple or number.

    Modified the bresenham complete circle algorithm from
    daniweb.com/programming/software-development/threads/321181
    """
    if isinstance(segments, int):
        segments = [i == segments for i in range(4)]

    # Parse text input
    elif isinstance(segments, str):
        option = segments.lower()
        count = [0, 0, 0, 0]
        if 'top' in option:
            count[0] += 1
            count[3] += 1
        if 'bottom' in option:
            count[1] += 1
            count[2] += 1
        if 'left' in option:
            count[2] += 1
            count[3] += 1
        if 'right' in option:
            count[0] += 1
            count[1] += 1
        count_max = max(count)
        segments = [i == count_max for i in count]

    # Calculate the circle
    switch = 3 - (2 * radius)
    outline = set()
    area = set()
    x = 0
    y = radius
    last_y = None
    last_x = None
    while x <= y:

        # Calculate outline
        if segments[0]:
            outline.add((x, -y))
            outline.add((y, -x))
        if segments[1]:
            outline.add((y, x))
            outline.add((x, y))
        if segments[2]:
            outline.add((-x, y))
            outline.add((-y, x))
        if segments[3]:
            outline.add((-y, -x))
            outline.add((-x, -y))

        # Add to area
        if y != last_y:
            last_y = y
            if segments[0]:
                for i in range(0, x):
                    area.add((i, -y))
            if segments[1]:
                for i in range(0, x):
                    area.add((i, y))
            if segments[2]:
                for i in range(1-x, 1):
                    area.add((i, y))
            if segments[3]:
                for i in range(1-x, 1):
                    area.add((i, -y))

        if x != last_x:
            last_x = x
            if segments[0]:
                for i in range(0, y):
                    area.add((i, -x))
            if segments[1]:
                for i in range(0, y):
                    area.add((i, x))
            if segments[2]:
                for i in range(1-y, 1):
                    area.add((i, x))
            if segments[3]:
                for i in range(1-y, 1):
                    area.add((i, -x))

        if switch < 0:
            switch += 4 * x + 6
        else:
            switch += 4 * (x - y) + 10
            y = y - 1
        x = x + 1

    return (outline, area)
