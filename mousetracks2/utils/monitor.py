from dataclasses import dataclass, field

from .system import monitor_locations
from ..types import RectList


def calculate_monitor_index(pos: tuple[int, int],
                            monitors: RectList) -> int:
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
    for i, (x1, y1, x2, y2) in enumerate(monitors.rects):
        if x1 <= x < x2 and y1 <= y < y2:
            return i

    # Slower method to check positions outside of bounds
    best_index = 0
    min_score = float('inf')
    for i, (x1, y1, x2, y2) in enumerate(monitors.rects):

        # Calculate how far out of bounds the pixel is
        dx = max(x1 - x, 0, x - (x2 - 1))
        dy = max(y1 - y, 0, y - (y2 - 1))

        # Apply a penalty to horizontal distance
        score = (dx * 2) + dy

        if score < min_score:
            min_score = score
            best_index = i

    return best_index


@dataclass
class MonitorData:
    """Store the logical and physical monitor locations."""

    logical: RectList = field(default_factory=RectList)
    physical: RectList = field(default_factory=RectList)

    def __post_init__(self) -> None:
        self.reload()

    def reload(self) -> None:
        """Reload the monitor data."""
        self.logical = monitor_locations(False)
        self.physical = monitor_locations(True)

    def coordinate(self, coordinate: tuple[int, int]) -> tuple[int, int]:
        """Map a coordinate from logical to physical space.
        This is required when Windows scaling is used.

        Any out-of-bounds inputs are clamped to the nearest valid pixel.
        """
        idx = calculate_monitor_index(coordinate, self.logical)

        lx1, ly1, lx2, ly2 = self.logical[idx].rect
        px1, py1, px2, py2 = self.physical[idx].rect
        lx, ly = coordinate

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
