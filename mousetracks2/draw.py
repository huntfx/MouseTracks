import os

import numpy as np
from scipy.ndimage import binary_dilation, binary_fill_holes, center_of_mass
from PIL import Image, ImageDraw, ImageFont


KAPPA = 4 * (2 ** 0.5 - 1) / 3  # Cubic Bezier approximation of a circle quadrant


def calculate_bezier(width: int, height: int, start_pos: tuple[int, int], start_cp: tuple[int, int],
    end_pos: tuple[int, int], end_cp: tuple[int, int], thickness: int, num_steps: int = 1000) -> np.ndarray:
    """Calculates a boolean mask for a cubic Bezier curve.

    Parameters:
        width: The width of the target numpy array
        height: The height of the target numpy array.
        start_pos: The (x, y) starting point of the curve.
        start_cp: The (x, y) control point associated with the start point.
        end_pos: The (x, y) ending point of the curve.
        end_cp: The (x, y) control point associated with the end point.
        thickness: The desired thickness of the curve in pixels.
        num_steps: The number of points to calculate along the curve's path.
            Too few and gaps will be visible.

    Returns:
        A boolean numpy array of shape (height, width).

    Raises:
        ValueError: If thickness is less than 1.
    """
    if thickness < 1:
        raise ValueError('thickness too low')
    p0 = np.array(start_pos)
    p1 = np.array(start_cp)
    p2 = np.array(end_cp)
    p3 = np.array(end_pos)
    t = np.linspace(0, 1, num_steps)
    t_col = t[:, np.newaxis]
    curve_points = (
        (1 - t_col) ** 3 * p0 +
        3 * (1 - t_col) ** 2 * t_col * p1 +
        3 * (1 - t_col) * t_col ** 2 * p2 +
        t_col ** 3 * p3
    )
    curve_points_int = np.round(curve_points).astype(int)
    canvas = np.zeros((height, width), dtype=bool)
    x_coords = np.clip(curve_points_int[:, 0], 0, width - 1)
    y_coords = np.clip(curve_points_int[:, 1], 0, height - 1)
    canvas[y_coords, x_coords] = True
    if thickness > 1:
        struct = np.ones((thickness, thickness), dtype=bool)
        canvas = binary_dilation(canvas, structure=struct)
    return canvas


def shift_2d(arr: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """Shift a 2D array horizontally or vertically."""
    shifted = np.zeros(arr.shape, dtype=arr.dtype)
    height, width = arr.shape
    src_y_start = max(0, -dy)
    src_y_end = height + min(0, -dy)
    src_x_start = max(0, -dx)
    src_x_end = width + min(0, -dx)
    dst_y_start = max(0, dy)
    dst_y_end = height + min(0, dy)
    dst_x_start = max(0, dx)
    dst_x_end = width + min(0, dx)

    # Check overlap based on start/end indices directly
    y_overlap = (src_y_end > src_y_start) and (dst_y_end > dst_y_start)
    x_overlap = (src_x_end > src_x_start) and (dst_x_end > dst_x_start)

    if y_overlap and x_overlap:
        # Calculate the height and width of the overlapping region
        overlap_h = min(src_y_end, height) - src_y_start
        overlap_w = min(src_x_end, width) - src_x_start
        # Ensure slicing uses calculated height/width, respecting bounds
        value = arr[src_y_start:src_y_start + overlap_h, src_x_start:src_x_start + overlap_w]
        shifted[dst_y_start:dst_y_start + overlap_h, dst_x_start:dst_x_start + overlap_w] = value
    return shifted


def create_rounded_rect(x: int, y: int, width: int, height: int, radius: int,
                        ) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Generates vertices and control points for a rounded rectangle."""
    if radius < 0:
        radius = 0
    max_radius = min(width / 2, height / 2)
    if radius > max_radius:
        radius = max_radius

    x0, y0 = x, y
    x1, y1 = x + width, y + height
    r = radius
    k = KAPPA

    vertices = [
        (x0 + r, y0), (x1 - r, y0),  # Top edge points
        (x1, y0 + r), (x1, y1 - r),  # Right edge points
        (x1 - r, y1), (x0 + r, y1),  # Bottom edge points
        (x0, y1 - r), (x0, y0 + r),  # Left edge points
    ]

    control_points = [
        (x0 + r, y0), (x1 - r, y0),  # Top line: v0 -> v1
        (x1 - r * (1 - k), y0), (x1, y0 + r * (1 - k)),  # Top-right corner: v1 -> v2
        (x1, y0 + r), (x1, y1 - r),  # Right line: v2 -> v3
        (x1, y1 - r * (1 - k)), (x1 - r * (1 - k), y1),  # Bottom-right corner: v3 -> v4
        (x1 - r, y1), (x0 + r, y1),  # Bottom line: v4 -> v5
        (x0 + r * (1 - k), y1), (x0, y1 - r * (1 - k)),  # Bottom-left corner: v5 -> v6
        (x0, y1 - r), (x0, y0 + r),  # Left line: v6 -> v7
        (x0, y0 + r * (1 - k)), (x0 + r * (1 - k), y0)  # Top-left corner: v7 -> v0
    ]
    return vertices, control_points


class Polygon:
    """Represents a polygon with Bezier curve edges."""

    AlignLeft = 1
    AlignCentreH = 2
    AlignRight = 4
    AlignTop = 8
    AlignCentreV = 16
    AlignBottom = 32
    AlignCentre = AlignCentreH | AlignCentreV

    def __init__(self, width: int, height: int, vertices: list[tuple[int, int]],
                 control_points: list[tuple[int, int]], thickness: int = 1) -> None:
        """Creates a Polygon object and calculates internal masks.

        Parameters:
            width: The width of the internal canvas.
            height: The height of the internal canvas.
            vertices: A list of (x, y) tuples defining the main vertices. Min 3.
            control_points: A list of (x, y) control point tuples.
                Must have exactly `2 * len(vertices)` elements.
                `control_points[2 * i]` controls curve leaving `vertices[i]`.
                `control_points[2 * i + 1]` controls curve entering `vertices[i + 1]`.
            thickness: The thickness for the outline.

        Raises:
            ValueError: If validation of vertices, control points, or thickness fails.
        """
        num_vertices = len(vertices)
        if num_vertices < 3:
            raise ValueError('not enough vertices')
        if len(control_points) != 2 * num_vertices:
            raise ValueError(f'expected {2 * num_vertices} control points for '
                             f'{num_vertices} vertices, but got {len(control_points)}')
        if thickness < 1:
            raise ValueError('thickness too low')

        self.array = np.zeros((height, width, 4), dtype=np.uint8)

        # Precalculate the masks
        self._outline_mask = np.zeros((height, width), dtype=bool)
        for i in range(num_vertices):
            start_pos = vertices[i]
            end_pos = vertices[(i + 1) % num_vertices]
            start_cp = control_points[2 * i]
            end_cp = control_points[2 * i + 1]

            edge_mask = calculate_bezier(
                width=width,
                height=height,
                start_pos=start_pos,
                start_cp=start_cp,
                end_pos=end_pos,
                end_cp=end_cp,
                thickness=thickness,
            )
            self._outline_mask |= edge_mask
        self._fill_mask = binary_fill_holes(self._outline_mask)

    def fill(self, colour: tuple[int, int, int, int], offset: tuple[int, int] | None = None) -> None:
        """Fills the polygon's interior with an optional offset.

        Parameters:
            colour: The colour to use when drawing.
            offset: Specify the shift offset in pixels.
        """
        mask = self._fill_mask
        if offset is not None and any(offset):
            mask = shift_2d(mask, offset[0], offset[1])
        self.array[mask] = colour

    def draw_outline(self, color: tuple[int, int, int, int], offset: tuple[int, int] | None = None) -> None:
        """Draws the polygon's outline.

        Parameters:
            colour: The colour to use when drawing.
            offset: Specify the shift offset in pixels.
        """
        mask = self._outline_mask
        if offset is not None and any(offset):
            mask = shift_2d(mask, offset[0], offset[1])
        self.array[mask] = color

    def draw_text(self, text: str, colour: tuple[int, int, int], align: int = AlignCentre,
                  size: int = 20, offset: tuple[int, int] = (0, 0)) -> None:
        """Draws text over the polygon.

        Parameters:
            text: The text to draw.
            colour: The colour to use when drawing.
            size: The desired font size in points.
            offset: Specify the shift offset in pixels.
        """
        font = ImageFont.truetype('arial.ttf', size)

        target_x = 0.0
        target_y = 0.0
        h_anchor = 'm'
        v_anchor = 'm'

        # Calculate bounding box of the filled polygon
        rows, cols = np.where(self._fill_mask)
        min_x = np.min(cols)
        max_x = np.max(cols)
        min_y = np.min(rows)
        max_y = np.max(rows)
        center_y = (min_y + max_y) / 2.0
        center_x = (min_x + max_x) / 2.0

        # Horizontal Alignment
        if align & self.AlignLeft:
            target_x = min_x
            h_anchor = 'l'
        elif align & self.AlignRight:
            target_x = max_x
            h_anchor = 'r'
        else:
            target_x = center_x
            h_anchor = 'm'

        # Vertical Alignment
        if align & self.AlignTop:
            target_y = min_y
            v_anchor = 't'
        elif align & self.AlignBottom:
            target_y = max_y
            v_anchor = 'b'
        else:
            target_y = center_y
            v_anchor = 'm'

        # Adjust position with offset
        target_x += offset[0]
        target_y += offset[1]

        img_pil = Image.fromarray(self.array)
        draw = ImageDraw.Draw(img_pil)
        draw.text((target_x, target_y), text, fill=colour, font=font, anchor=h_anchor + v_anchor)
        self.array = np.asarray(img_pil)


def create_controller_body(width: int, height: int):
    """Create the body of a controller.

    Note:
        This was done by manually plotting points using
        https://www.desmos.com/calculator/cahqdxeshd.

        Here are the rough rules for the right side that were used for
        this function:
        - Top: (0, 8), (3, 8) -> (6, 7), (6, 8)
        - Right: (6, 7), (6.5, 6.5) -> (7, -3.5), (11, -2.5)
        - Bottom: (7, -3.5), (0.5, 3.5) -> (0, 0), (4, 0)

    TODO:
        R shoulder:
            (2.5, 8) (3, 8) -> (3.5, 8.5), (3, 8.5)
            (3.5, 8.5), (4.5, 8.5) -> (6, 7), (6, 7.5)
        A: midpoint (4.5, 4), radius 1
        B: midpoint (5.75, 5.25)
        X: midpoint (3.25, 5.25)
        Y: midpoint (4.5, 6.25)
        LS: midpoint (-4.5, 5.25), radius: 2
        RS: midpoint (2.25, 2.75)
        DPAD: midpoint (-2.25, 2.25), radius: 2.5
        START: midpoint (1.25, 5.25), radius: 0.75
        SELECT: midpoint (-1.25, 5.25)
    """
    vertices = [
        (0, 8),
        (6, 7),
        (7, -3.5),
        (0, 0),
        (-7, -3.5),
        (-6, 7),
    ]
    control_points = [
        (3, 8), (5, 8),
        (6.5, 6.5), (11, -2.5),
        (3.5, 0.5), (4, -0.05),
        (-4, -0.05), (-3.5, 0.5),
        (-11, -2.5), (-6.5, 6.5),
        (-5, 8), (-3, 8),
    ]

    # R sholder
    # vertices = [
    #     (2.5, 8),
    #     (3.5, 8.5),
    #     (6, 7),
    # ]
    # control_points = [
    #     (3, 8), (3, 8.5),
    #     (4.5, 8.5), (6, 7.5),
    #     (6, 7), (2.5, 8),
    # ]

    # Split to x/y lists for easier editing
    vx, vy = zip(*vertices)
    cx, cy = zip(*control_points)

    # Flip the Y axis
    vy = [-y for y in vy]
    cy = [-y for y in cy]

    # Shift to (0, 0)
    vx_min = min(vx)
    vx = [x - vx_min for x in vx]
    cx = [x - vx_min for x in cx]
    vy_min = min(vy)
    vy = [y - vy_min for y in vy]
    cy = [y - vy_min for y in cy]

    # Calculate scale factor
    x_scale = (0.8 * width) / max(vx)
    y_scale = (0.8 * height) / max(vy)
    scale = min(x_scale, y_scale)

    # Calculate centre offset
    x_offset = (width - max(vx) * scale) / 2
    y_offset = (height - max(vy) * scale) / 2

    vertices = [(x * scale + x_offset, y * scale + y_offset) for x, y in zip(vx, vy)]
    control_points = [(x * scale + x_offset, y * scale + y_offset) for x, y in zip(cx, cy)]
    return vertices, control_points


def calculate_circle(width: int, height: int, centre: tuple[int, int], radius: int):
    r = radius
    k = KAPPA
    rk = r * k
    cx, cy = centre

    vertices = [
        (cx + r, cy),
        (cx, cy + r),
        (cx - r, cy),
        (cx, cy - r),
    ]
    control_points = [
        (cx + r, cy + rk), (cx + rk, cy + r),
        (cx - rk, cy + r), (cx - r, cy + rk),
        (cx - r, cy - rk), (cx - rk, cy - r),
        (cx + rk, cy - r), (cx + r, cy - rk),
    ]
    return vertices, control_points


if __name__ == '__main__':
    vertices, control_points = create_rounded_rect(x=50, y=40, width=200, height=150, radius=30)
    vertices, control_points = create_controller_body(2560, 1080)
    vertices, control_points = calculate_circle(2560, 1080, (500, 500), 40)
    poly = Polygon(width=2560, height=1080, vertices=vertices, control_points=control_points, thickness=3)
    poly.fill((105, 105, 105, 255), (5, 5))
    poly.fill((211, 211, 211, 255))
    poly.draw_outline((0, 0, 0, 255))
    poly.draw_text('test', (0, 0, 0), size=30)

    final_image = Image.fromarray(poly.array)
    final_image.show()
