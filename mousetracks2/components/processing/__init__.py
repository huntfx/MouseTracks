import math
import multiprocessing
import traceback
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import ndimage

from mousetracks.image import colours
from .. import ipc
from ...utils.math import calculate_line, calculate_distance
from ...utils.win import cursor_position, monitor_locations


COMPRESSION_FACTOR = 1.1

COMPRESSION_THRESHOLD = 425000  # Max: 2 ** 64 - 1

UPDATES_PER_SECOND = 60

DOUBLE_CLICK_MS = 500
"""Maximum time in ms where a double click is valid."""

DOUBLE_CLICK_TOL = 8
"""Maximum pixels where a double click is valid."""

INACTIVITY_MS = 300000
"""Time in ms before the user is classed as "inactive"."""

INACTIVITY_MS = 2000


def array_target_resolution(resolution_arrays: dict[tuple[int, int], np.ndarray],
                            width: Optional[int] = None, height: Optional[int] = None) -> tuple[int, int]:
    """Calculate a target resolution.
    If width or height is given, then it will be used.
    The aspect ratio is taken into consideration.
    """
    if width is not None and height is not None:
        return width, height

    popularity = {}
    for res, handler in resolution_arrays.items():
        popularity[res] = np.sum(handler.array > 0)
    threshold = max(popularity.values()) * 0.9
    _width, _height = max(res for res, value in popularity.items() if value > threshold)

    if width is None and height is None:
        return _width, _height

    aspect = _width / _height
    if width is None:
        return int(height * aspect), height
    return width, int(width / aspect)


def array_to_uint8(array: np.ndarray) -> np.ndarray:
    """Normalise an array to map it's values from 0-255."""
    max_value = np.max(array)
    if not max_value:
        return np.zeros(array.shape, dtype=np.uint8)
    return (array.astype(np.float64) * (255 / max_value)).astype(np.uint8)


def gaussian_size(width, height, multiplier: float = 1.0, base: float = 0.0125):
    """Calculate size of gaussian blur."""
    return int(round(min(width, height) * base * multiplier))


class ExitRequest(Exception):
    """Custom exception to raise and catch when an exit is requested."""



class IntArrayHandler:
    """Create an integer array and update the dtype when required."""

    DTYPES = [np.uint16, np.uint32, np.uint64]
    MAX_VALUES = [np.iinfo(dtype).max for dtype in DTYPES]

    def __init__(self, shape: int | list[int]) -> None:
        self.array = np.zeros(shape, dtype=np.uint8)
        self.max_value = np.iinfo(np.uint8).max

    def __str__(self) -> str:
        return str(self.array)

    def __repr__(self) -> str:
        return repr(self.array)

    def __getitem__(self, item: any) -> int:
        """Get an array item."""
        return self.array[item]

    def __setitem__(self, item: any, value: int) -> None:
        """Set an array item, changing dtype if required."""
        if value > self.max_value:
            for dtype, max_value in zip(self.DTYPES, self.MAX_VALUES):
                if value < max_value:
                    self.max_value = max_value
                    self.array = self.array.astype(dtype)
                    break

        self.array[item] = value


class ResolutionArray(dict):
    """Store multiple arrays for different resolutions."""

    def __missing__(self, key: tuple[int, int]) -> IntArrayHandler:
        self[key] = IntArrayHandler([key[1], key[0]])
        return self[key]


def array_rescale(array: np.ndarray, target_width: int, target_height: int) -> np.ndarray:
    """Rescale the array with the correct filtering."""
    input_height, input_width = array.shape

    # No rescaling required
    if target_height == input_height and target_width == input_width:
        return array

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


def generate_colour_lookup(*colours: tuple[int, int, int, int], steps: int = 256) -> np.ndarray:
    """Generate a color lookup table transitioning smoothly between given colors."""
    lookup = np.zeros((steps, 4), dtype=np.uint8)

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



@dataclass
class PreviousMouseClick:
    """Store data related to the last mouse click."""
    message: ipc.MouseClick
    tick: int
    double_clicked: bool

    @property
    def button(self) -> int:
        """Get the message button."""
        return self.message.button

    @property
    def position(self) -> tuple[int, int]:
        """Get the message position."""
        return self.message.position

@dataclass
class Tick:
    """Store data related to ticks."""

    current: int = field(default=0)
    previous: int = field(default=0)
    active: int = field(default=0)
    inactive: int = field(default=0)

    @property
    def activity(self) -> int:
        """Get the number of active ticks."""
        amount = self.active
        if self.is_active:
            amount += self.since_active
        return amount

    @property
    def inactivity(self) -> int:
        """Get the number of inactive ticks."""
        amount = self.inactive
        if not self.is_active:
            amount += self.since_active
        return amount

    @property
    def is_active(self) -> bool:
        """Determine if currently active."""
        threshold = UPDATES_PER_SECOND * INACTIVITY_MS / 1000
        return self.since_active <= threshold

    @property
    def since_active(self) -> int:
        """Get the number of ticks since the last activity."""
        return self.current - self.previous

    def set_active(self) -> None:
        """Update the last tick activity."""
        if self.is_active:
            self.active += self.since_active
        else:
            self.inactive += self.since_active
        self.previous = self.current


class Processing:
    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        self.q_send = q_send
        self.q_receive = q_receive

        self.mouse_track_maps = ResolutionArray()
        self.mouse_speed_maps = ResolutionArray()
        self.mouse_single_clicks = ResolutionArray()
        self.mouse_double_clicks = ResolutionArray()
        self.mouse_held_clicks = ResolutionArray()
        self.mouse_move_count = 0
        self.key_held = IntArrayHandler(0xFF)
        self.key_presses = IntArrayHandler(0xFF)

        self.tick = Tick()

        self.mouse_distance = 0.0
        self.mouse_position = cursor_position()
        self.mouse_move_tick = 0
        self.previous_mouse_click: Optional[PreviousMouseClick] = None
        self.monitor_data = monitor_locations()
        self.previous_monitor = None
        self.pause_tick = 0
        self.state = ipc.TrackingState.State.Pause

    def _monitor_offset(self, pixel: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
        """Detect which monitor the pixel is on."""
        for x1, y1, x2, y2 in self.monitor_data:
            if x1 <= pixel[0] < x2 and y1 <= pixel[1] < y2:
                return ((x2 - x1, y2 - y1), (x1, y1))
        raise ValueError(f'coordinate {pixel} not in monitors')

    def _cursor_move(self, message: ipc.MouseMove) -> None:
        """Handle a mouse move message.

        There are some caveats that are hard to handle. If a mouse is
        programmatically moved, then it will jump to a location on the
        screen. A check can be done to skip drawing if the cursor wasn't
        previously moving, but the first frame of movement wil also
        always get skipped. Detecting the vector of movement was tried,
        but it was too overcomplicated and wasn't good enough.

        There's never been an issue with the original script, so the
        behaviour has been copied.
        - Time tracks are fully recorded, and will capture jumps.
        This is fine as those tracks will be buried over time.
        - Speed tracks are only recorded if the cursor was previously
        moving, the downside being it will still record any jumps while
        moving, and will always skip the first frame of movement.
        """
        print(f'[Processing] Mouse has moved to {message.position}')

        # If the ticks match then overwrite the old data
        if self.tick.current == self.mouse_move_tick:
            self.mouse_position = message.position

        distance = calculate_distance(message.position, self.mouse_position)
        moving = self.tick.current == self.mouse_move_tick + 1

        # Calculate the data
        pixels = calculate_line(message.position, self.mouse_position)
        if distance:
            self.mouse_distance += distance

        # Add the pixels to an array
        for pixel in pixels:
            current_monitor, offset = self._monitor_offset(pixel)
            index = (pixel[1] - offset[1], pixel[0] - offset[0])

            self.mouse_track_maps[current_monitor][index] = self.mouse_move_count
            if distance and moving:
                self.mouse_speed_maps[current_monitor][index] = max(self.mouse_speed_maps[current_monitor][index], int(100 * distance))

        # Update the saved data
        self.mouse_move_count += 1
        self.mouse_position = message.position
        self.mouse_move_tick = self.tick.current

        # Check if array compression is required
        # This is important for the time maps
        # For speed, it just helps flatten out values that are too large
        if self.mouse_move_count > COMPRESSION_THRESHOLD:
            print(f'[Processing] Tracking threshold reached, reducing values...')
            for maps in (self.mouse_track_maps, self.mouse_speed_maps):
                for res, array in maps.items():
                    maps[res] = (array / COMPRESSION_FACTOR).astype(array.dtype)
            print(f'[Processing] Reduced all arrays')

    def _render_array(self, message: ipc.RenderRequest):
        """Render an array (tracks / heatmaps)."""
        print('[Processing] Render request received...')
        width = message.width
        height = message.height

        # Choose the data to render
        maps: dict[tuple[int, int], np.ndarray]
        match message.type:
            case ipc.RenderType.Time:
                maps = self.mouse_track_maps

            # Subtract a value from each array and ensure it doesn't go below 0
            case ipc.RenderType.TimeSincePause:
                maps = {}
                for res, array in self.mouse_track_maps.items():
                    partial_array = array.astype(np.int64) - self.pause_tick
                    partial_array[partial_array < 0] = 0
                    maps[res] = partial_array

            case ipc.RenderType.Speed:
                maps = self.mouse_speed_maps

            case ipc.RenderType.SingleClick:
                maps = self.mouse_single_clicks

            case ipc.RenderType.DoubleClick:
                maps = self.mouse_double_clicks

            case ipc.RenderType.HeldClick:
                maps = self.mouse_held_clicks

            case _:
                raise NotImplementedError(message.type)

        # Find the largest most common resolution
        width, height = array_target_resolution(maps, width, height)

        # Apply the sampling amount
        scale_width = int(width * message.sampling)
        scale_height = int(height * message.sampling)

        # Scale all arrays to the same size and combine
        if maps:
            rescaled_arrays = [array_rescale(handler.array, scale_width, scale_height) for handler in maps.values()]
            final_array = np.maximum.reduce(rescaled_arrays)
        else:
            final_array = np.zeros((scale_height, scale_width), dtype=np.int8)

        # Special case for heatmaps
        if message.type in (ipc.RenderType.SingleClick, ipc.RenderType.DoubleClick, ipc.RenderType.HeldClick):
            # Convert the array to a linear array
            unique_values, unique_indexes = np.unique(final_array, return_inverse=True)

            # Apply a gaussian blur
            blur_amount = gaussian_size(scale_width, scale_height)
            final_array = ndimage.gaussian_filter(unique_indexes.astype(np.float64), sigma=blur_amount)

            # TODO: Reimplement the heatmap range clipping
            # It will be easier to test once saving works and a heavier heatmap can be used
            # min_value = np.min(heatmap)
            # all_values = np.sort(heatmap.ravel(), unique=True)
            # max_value = all_values[int(round(len(unique_values) * 0.005))]

        # Convert the array to 0-255 and map to a colour lookup table
        colour_lookup = generate_colour_lookup(*colours.calculate_colour_map(message.colour_map))
        coloured_array = colour_lookup[array_to_uint8(final_array)]

        self.q_send.put(ipc.Render(message.type, coloured_array, message.sampling, self.mouse_move_tick))
        print('[Processing] Render request completed')

    def _process_message(self, message: ipc.Message) -> None:
        """Process an item of data."""
        match message:
            # Update the current tick
            case ipc.Tick():
                self.tick.current = message.tick

            case ipc.RenderRequest():
                self._render_array(message)

            case ipc.MouseMove():
                self.tick.set_active()
                self._cursor_move(message)

            case ipc.MouseHeld():
                self.tick.set_active()

                current_monitor, offset = self._monitor_offset(message.position)
                index = (message.position[1] - offset[1], message.position[0] - offset[0])
                self.mouse_held_clicks[current_monitor][index] += 1

            case ipc.MouseClick():
                self.tick.set_active()

                previous = self.previous_mouse_click
                double_click = (
                    previous is not None
                    and previous.button == message.button
                    and previous.tick + (UPDATES_PER_SECOND * DOUBLE_CLICK_MS / 1000) > self.tick.current
                    and calculate_distance(previous.position, message.position) <= DOUBLE_CLICK_TOL
                    and not previous.double_clicked
                )

                if double_click:
                    arrays = self.mouse_double_clicks
                    print(f'[Processing] Mouse button {message.button} double clicked.')
                else:
                    arrays = self.mouse_single_clicks
                    print(f'[Processing] Mouse button {message.button} clicked.')

                current_monitor, offset = self._monitor_offset(message.position)
                index = (message.position[1] - offset[1], message.position[0] - offset[0])
                arrays[current_monitor][index] += 1

                self.previous_mouse_click = PreviousMouseClick(message, self.tick.current, double_click)

            case ipc.KeyPress():
                self.tick.set_active()
                print(f'[Processing] Key {message.opcode} pressed.')
                self.key_presses[message.opcode] += 1

            case ipc.KeyHeld():
                self.tick.set_active()
                self.key_held[message.opcode] += 1

            case ipc.MonitorsChanged():
                print(f'[Processing] Monitors changed.')
                self.monitor_data = message.data

            case ipc.DebugRaiseError():
                raise RuntimeError('test exception')

            case ipc.TrackingState():
                match message.state:
                    case ipc.TrackingState.State.Stop:
                        raise ExitRequest
                    case ipc.TrackingState.State.Pause:
                        self.pause_tick = self.mouse_move_count
                self.state = message.state

            case _:
                raise NotImplementedError(message)

    def run(self) -> None:
        print('[Processing] Loaded.')

        try:
            while True:
                self._process_message(self.q_receive.get())

        except ExitRequest:
            print('[Processing] Shut down.')

        # Catch error after KeyboardInterrupt
        except EOFError:
            print('[Processing] Force shut down.')
            return

        except Exception as e:
            self.q_send.put(ipc.Traceback(e, traceback.format_exc()))
            print('[Processing] Error shut down.')

        self.q_send.put(ipc.ProcessShutDownNotification(ipc.Target.Processing))
        print('[Processing] Sent process closed notification.')


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
    Processing(q_send, q_receive).run()
