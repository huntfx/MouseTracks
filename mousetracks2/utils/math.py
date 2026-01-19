"""General math functions."""


def calculate_distance(p1: tuple[int, int] | None, p2: tuple[int, int] | None) -> float:
    """Find the distance between two (x, y) coordinates."""
    if p1 is None or p2 is None or p1 == p2:
        return 0.0
    return ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5


def calculate_line(start: tuple[int, int] | None, end: tuple[int, int] | None) -> list[tuple[int, int]]:
    """Calculates path in terms of pixels between two points.
    Uses Bresenham's Line Algorithm.
    """
    if start is None or end is None or start == end:
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


def calculate_circle(radius: int, segments: tuple[bool, bool, bool, bool] = (True, True, True, True)
                     ) -> tuple[set[tuple[int, int]], set[tuple[int, int]]]:
    """Get the area and outline of a circle as pixels.
    Optionally pass in which segment is needed, as a tuple or number.

    Modified the bresenham complete circle algorithm from
    https://daniweb.com/programming/software-development/threads/321181
    """
    # Calculate the circle
    switch = 3 - (2 * radius)
    outline: set[tuple[int, int]] = set()
    area: set[tuple[int, int]] = set()
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


def calculate_pixel_offset(x: int, y: int, x1: int, y1: int, x2: int, y2: int
                           ) -> tuple[tuple[int, int], tuple[int, int]] | None:
    """Calculate the offset for a pixel within monitor rectangle coordinates.

    Returns:
        Tuple of resolution and relative coordinate.
        None if not within bounds.
    """
    if x1 <= x < x2 and y1 <= y < y2:
        return ((x2 - x1, y2 - y1), (x - x1, y - y1))
    return None


def calculate_monitor_index(pos: tuple[int, int],
                            monitors: list[tuple[int, int, int, int]]) -> int:
    """Determine which monitor a position lies on.

    In some cases, a logical coordinate may not strictly lie within a
    monitor's bounds due to Windows DPI scaling rounding errors. To
    handle this, a distance check is used, prioritising horizontal
    over vertical alignment to prevent jumps at certain intersections.

    Note: This is not an exact science and was determined via manual
    testing  using two side-by-side 1440p monitors. The right monitor
    was set to 225% scale (height 640), which allowed the cursor to
    land strictly on Y=640 rather than the expected max of 639. If the
    cursor is at maximum Y (640) and minimum X (2560), then standard
    checks fail. The horizontal weighting fixed this, and testing
    various other setups resulted in no noticeable issues.
    """
    x, y = pos

    # Fast method to determine if within bounds
    for i, (mx1, my1, mx2, my2) in enumerate(monitors):
        if mx1 <= x < mx2 and my1 <= y < my2:
            return i

    # Slower method to check positions outside of bounds
    best_index = 0
    min_score = float('inf')
    for i, (mx1, my1, mx2, my2) in enumerate(monitors):

        # Calculate how far out of bounds the pixel is
        dx = max(mx1 - x, 0, x - (mx2 - 1))
        dy = max(my1 - y, 0, y - (my2 - 1))

        # Apply a penalty to horizontal distance
        score = (dx * 2) + dy

        if score < min_score:
            min_score = score
            best_index = i

    return best_index


def logical_to_physical(pos: tuple[int, int],
                        logical_monitors: list[tuple[int, int, int, int]],
                        physical_monitors: list[tuple[int, int, int, int]],
                        ) -> tuple[int, int]:
    """Map a coordinate from logical to physical space.
    This is required when Windows scaling is used.

    Any out-of-bounds inputs are clamped to the nearest valid pixel.
    """
    idx = calculate_monitor_index(pos, logical_monitors)

    lx1, ly1, lx2, ly2 = logical_monitors[idx]
    px1, py1, px2, py2 = physical_monitors[idx]
    lx, ly = pos

    # Clamp the coordinate to the logical monitor bounds
    clamped_x = max(lx1, min(lx, lx2 - 1))
    clamped_y = max(ly1, min(ly, ly2 - 1))

    # Calculate scale factor
    l_w = max(1, lx2 - lx1)
    l_h = max(1, ly2 - ly1)
    scale_x = (px2 - px1) / l_w
    scale_y = (py2 - py1) / l_h

    # Map the relative position to physical space
    phys_x = px1 + ((clamped_x - lx1) * scale_x)
    phys_y = py1 + ((clamped_y - ly1) * scale_y)

    return round(phys_x), round(phys_y)
