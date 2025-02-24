import math
import sys
from collections import defaultdict

import numpy as np
try:
    from scipy import ndimage
except ModuleNotFoundError:
    sys.path.append('resources/build')
    from scipy import ndimage

from .legacy import colours


class EmptyRenderError(ValueError):
    """Raise when a render is requested with not enough data.

    For example if only height is given with no arrays, then it's not
    possible to calculate the correct width and render an empty image.
    """

    def __init__(self) -> None:
        super().__init__('input arrays cannot be empty if size not defined')


def array_target_resolution(arrays: list[np.typing.ArrayLike], width: int | None = None,
                            height: int | None = None, lock_aspect: bool = False) -> tuple[int, int]:
    """Calculate a target resolution.
    If width or height is given, then it will be used.
    The aspect ratio can be taken into consideration.
    """
    # If not keeping aspect, return the given width and height
    if width is not None and height is not None and not lock_aspect:
        return width, height

    # Calculate the most common aspect ratio
    popularity: dict[tuple[int, int], int] = defaultdict(int)
    for array in map(np.asarray, arrays):
        res_y, res_x = array.shape
        popularity[(res_x, res_y)] += np.sum(np.greater(array, 0))
    threshold = max(popularity.values()) * 0.9
    _width, _height = max(res for res, value in popularity.items() if value >= threshold)
    aspect = _width / _height

    # Calculate the resolutions from the given width / height
    if width is not None:
        result_width = width, int(width / aspect)
    if height is not None:
        result_height = int(height * aspect), height

    # Handle when only one resolution is given
    if width is None:
        if height is None:
            return _width, _height
        return result_height
    if height is None:
        return result_width

    # Select the smallest if both dimensions are given
    width_prod = result_width[0] * result_width[1]
    height_prod = result_height[0] * result_height[1]
    if height_prod > width_prod:
        return result_width
    return result_height


def array_to_uint8(array: np.ndarray) -> np.ndarray:
    """Normalise an array to map it's values from 0-255."""
    max_value = np.max(array)
    if not max_value:
        return np.zeros(array.shape, dtype=np.uint8)
    return (array.astype(np.float64) * (255 / max_value)).astype(np.uint8)


def gaussian_size(width, height, multiplier: float = 0.0125):
    """Choose a gaussian blur amount to use for a given resolution."""
    return min(width, height) * multiplier


def array_rescale(array: np.typing.ArrayLike, target_width: int, target_height: int) -> np.ndarray:
    """Rescale the array with the correct filtering."""
    array = np.asarray(array)
    input_height, input_width = array.shape

    # No rescaling required
    if target_height == input_height and target_width == input_width:
        return np.asarray(array)

    # Upscale without blurring
    if target_height > input_height or target_width > input_width:
        zoom_factor = (target_height / input_height, target_width / input_width)
        return ndimage.zoom(array, zoom_factor, order=0)

    # Downscale without losing detail (credit to ChatGPT)
    block_height = input_height / target_height
    block_width = input_width / target_width
    pooled_full = ndimage.maximum_filter(array, size=(int(math.ceil(block_height)), int(math.ceil(block_width))))

    indices_y = np.linspace(0, input_height - 1, target_height).astype(np.uint64)
    indices_x = np.linspace(0, input_width - 1, target_width).astype(np.uint64)
    return np.ascontiguousarray(pooled_full[indices_y][:, indices_x])


def generate_colour_lookup(*colours: tuple[int, ...], steps: int = 256) -> np.ndarray:
    """Generate a color lookup table transitioning smoothly between given colors."""
    lookup = np.zeros((steps, 4), dtype=np.uint8)

    # Fix for single inputs
    if len(colours) == 1:
        colours = (colours[0], colours[0])

    num_transitions = len(colours) - 1
    steps_per_transition = steps // num_transitions
    remaining_steps = steps % num_transitions  # Distribute extra steps evenly

    start_index = 0
    for i in range(num_transitions):
        # Determine start and end colors for the current transition
        start_color = np.array(colours[i])
        end_color = np.array(colours[i + 1])

        # Adjust steps for the last transition to include any remaining steps
        current_steps = steps_per_transition + (i < remaining_steps)

        # Linearly interpolate between start_color and end_color
        for j in range(current_steps):
            t = j / (current_steps - 1)  # Normalized position (0 to 1)
            lookup[start_index + j] = (1 - t) * start_color + t * end_color

        start_index += current_steps

    return lookup


def render(colour_map: str, positional_arrays: dict[tuple[int, int], list[np.typing.ArrayLike]],
           width: int | None = None, height: int | None = None, sampling: int = 1, lock_aspect: bool = True,
           linear: bool = False, blur: float = 0.0, contrast: float = 1.0,
           clipping: float = 0.0) -> np.ndarray:
    """Combine a group of arrays into a single array for rendering.

    Parameters:
        colour_map: Must be either a predefined or manually defined map.
            See `config/colours.txt` for examples.
        positional_arrays: Dict of draw position and list of arrays.
            For now it only supports (0, 0) and (0, 1) for left and
            right.
        width: Force a particular width.
            If not set, the aspect ratio will be used to calculate it.
        height: Force a particular height.
            If not set, the aspect ratio will be used to calculate it.
        sampling: How many pixels to calculate per pixel.
            Setting this value to 2 will upscale everything to twice the
            target resolution.
            It ensures a more accurate representation when combining
            different resolutions together.
        lock_aspect: Force the aspect ratio to its recommended value.
        linear: Remap the array to linear values.
            This will ensure a smooth gradient.
        blur: Blur the array with a gaussian sigma of this value.
        contrast: Adjust the array contrast.
            This works by spacing out or reducing values.
        clipping: Clip the upper range to a percentage.
            This can be used on a heatmap if there's a single hotspot
            dominating the image.
    """
    # Calculate width / height
    all_arrays = []
    for arrays in positional_arrays.values():
        all_arrays.extend(arrays)
    if all_arrays:
        width, height = array_target_resolution(all_arrays, width, height, lock_aspect)
    if not width or not height:
        raise EmptyRenderError

    scale_width = width * sampling
    scale_height = height * sampling

    # Rescale the arrays to the target size and combine them
    combined_arrays: dict[tuple[int, int], np.ndarray] = {}
    for pos, arrays in positional_arrays.items():
        if arrays:
            rescaled = [array_rescale(array, scale_width, scale_height) for array in arrays]
            combined_arrays[pos] = np.maximum.reduce(rescaled)
        else:
            combined_arrays[pos] = np.zeros([scale_height, scale_width], dtype=np.uint8)

    # Convert to linear arrays
    if linear:
        combined_arrays = {pos: np.unique(array, return_inverse=True)[1]
                           for pos, array in combined_arrays.items()}

    # Apply gaussian blur
    if blur:
        combined_arrays = {pos: ndimage.gaussian_filter(array.astype(np.float64),
                                                        sigma=gaussian_size(scale_width, scale_height, blur))
                           for pos, array in combined_arrays.items()}

    # Equalise the max values
    if len(combined_arrays) > 1:
        max_values = {pos: max(1, np.max(array)) for pos, array in combined_arrays.items()}
        max_value = max(max_values.values())
        combined_arrays = {pos: combined_arrays[pos].astype(np.float64) * (max_value / value)
                           for pos, value in max_values.items()}

    # Combine all positional arrays into one big array
    combined_array = combine_array_grid(combined_arrays, scale_width, scale_height)

    # Clip the maximum values
    if clipping:
        sorted_values, linear_mapping = np.unique(combined_array, return_inverse=True)
        max_value = sorted_values[int(np.max(linear_mapping) * (1 - clipping))]
        combined_array[combined_array > max_value] = max_value

    # Update the contrast
    if contrast != 1.0:

        max_value = np.max(combined_array)
        max_value_log = np.log(max_value)
        limit = np.log(np.finfo(combined_array.dtype).max)

        # Prevent overflow errors by reducing the array range
        if True:
            target = limit / contrast
            if np.log(max_value) > target:
                new_max = int(np.exp(target))  # int conversion to round down
                combined_array /= (max_value / new_max)

        # Prevent overflow errors by limiting the contrast value
        # This is less preferable as it sets a hard limit
        else:
            if contrast * max_value_log > limit:
                contrast = int(limit) / max_value_log  # int conversion to round down

        combined_array **= contrast

    # Convert the array to 0-255 and map to a colour lookup table
    try:
        colour_map_data = colours.calculate_colour_map(colour_map)
    except Exception:  # Old code - just fallback to tranparent
        colour_map_data = [(0, 0, 0, 0)]

    colour_lookup = generate_colour_lookup(*colour_map_data)
    return colour_lookup[array_to_uint8(combined_array)]


def combine_array_grid(positional_arrays: dict[tuple[int, int], np.ndarray],
                       scale_width: int, scale_height: int) -> np.ndarray:
    """Combine arrays based on their positions and offsets."""
    if not positional_arrays:
        return np.zeros((scale_height, scale_width), dtype=np.float64)

    if len(set(array.shape for array in positional_arrays.values())) != 1:
        raise ValueError('all arrays must be the same size')

    # Determine the total required size
    min_col = min(pos[0] for pos in positional_arrays)
    max_col = max(pos[0] for pos in positional_arrays)
    min_row = min(pos[1] for pos in positional_arrays)
    max_row = max(pos[1] for pos in positional_arrays)
    total_width = scale_width * (max(0, max_col) - min(0, min_col) + 1)
    total_height = scale_height * (max(0, max_row) - min(0, min_row) + 1)

    # Create the combined array
    combined_array = np.zeros((total_height, total_width), dtype=np.float64)
    for (col, row), array in positional_arrays.items():
        x = col * scale_width
        y = row * scale_height
        combined_array[y: y + scale_height, x:x + scale_width] = array

    return combined_array
