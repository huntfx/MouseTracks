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
    Does not include the start and end point.
    """
    result: list[tuple[int, int]] = []

    # Return nothing if the two points are the same
    if end is None or start == end:
        return result

    difference = (end[0] - start[0], end[1] - start[1])

    # Check if the points are on the same axis
    if not difference[0]:
        if difference[1] > 1:
            for i in range(1, difference[1]):
                result.append((start[0], start[1] + i))
        elif difference[1] < -1:
            for i in range(1, -difference[1]):
                result.append((start[0], start[1] - i))
        return result
    if not difference[1]:
        if difference[0] > 1:
            for i in range(1, difference[0]):
                result.append((start[0] + i, start[1]))
        elif difference[0] < -1:
            for i in range(1, -difference[0]):
                result.append((start[0] - i, start[1]))
        return result

    # Step along line by pixel until end is reached
    slope = difference[1] / difference[0]
    count = slope
    x, y = start
    x_neg = -1 if difference[0] < 0 else 1
    y_neg = -1 if difference[1] < 0 else 1

    for i in range(100000):
        # If y > x and both pos or both neg
        if slope >= 1 or slope <= 1:
            if count >= 1:
                y += y_neg
                count -= 1
            elif count <= -1:
                y += y_neg
                count += 1
            else:
                x += x_neg
                count += slope

        # If y < x and both pos or both neg
        elif slope:
            if count >= 1:
                y += y_neg
                count -= 1
            elif count <= -1:
                y += y_neg
                count += 1
            if -1 <= count <= 1:
                x += x_neg
            count += slope

        coordinate = (x, y)
        if coordinate == end:
            return result
        result.append(coordinate)

        # Quick fix since values such as x(-57, -53) y(-22, -94) are one off
        if end[0] in (x-1, x, x+1) and end[1] in (y-1, y, y+1):
            return result

    raise ValueError(f'failed to find path between {start}, {end}')


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
