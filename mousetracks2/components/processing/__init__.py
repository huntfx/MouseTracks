import math
import multiprocessing
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import ndimage

from mousetracks.image import colours
from .. import ipc
from ...file import IntArrayHandler, MapData, ApplicationData
from ...utils.math import calculate_line, calculate_distance, calculate_pixel_offset
from ...utils.win import cursor_position, monitor_locations, MOUSE_BUTTONS


UPDATES_PER_SECOND = 60

DOUBLE_CLICK_MS = 500
"""Maximum time in ms where a double click is valid."""

DOUBLE_CLICK_TOL = 8
"""Maximum pixels where a double click is valid."""

INACTIVITY_MS = 300000
"""Time in ms before the user is classed as "inactive"."""


def array_target_resolution(resolution_arrays: list[tuple[tuple[int, int], IntArrayHandler]],
                            width: Optional[int] = None, height: Optional[int] = None) -> tuple[int, int]:
    """Calculate a target resolution.
    If width or height is given, then it will be used.
    The aspect ratio is taken into consideration.
    """
    if width is not None and height is not None:
        return width, height

    popularity = defaultdict(int)
    for res, handler in resolution_arrays:
        popularity[res] += np.sum(handler.array > 0)
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


@dataclass
class Application:
    name: str
    position: Optional[tuple[int, int]]
    resolution: Optional[tuple[int, int]]


class Processing:
    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        self.q_send = q_send
        self.q_receive = q_receive

        self._app_data: dict[str, ApplicationData] = defaultdict(ApplicationData)
        self.tick = Tick()

        self.previous_mouse_click: Optional[PreviousMouseClick] = None
        self.monitor_data = monitor_locations()
        self.previous_monitor = None
        self.pause_tick = 0
        self.state = ipc.TrackingState.State.Pause
        self._current_app: Application = None

    @property
    def app(self) -> ApplicationData:
        """Get the data for the current application."""
        if self._current_app is None:
            return self._app_data['Main']
        return self._app_data[self._current_app.name]

    def _monitor_offset(self, pixel: tuple[int, int]) -> Optional[tuple[tuple[int, int], tuple[int, int]]]:
        """Detect which monitor the pixel is on."""
        use_app = self._current_app is not None and self._current_app.position is not None
        if use_app:
            monitor_data = [self._current_app.position]
        else:
            monitor_data = self.monitor_data

        for x1, y1, x2, y2 in monitor_data:
            result = calculate_pixel_offset(pixel[0], pixel[1], x1, y1, x2, y2)
            if result is not None:
                return result
        return None

    def _record_move(self, data: MapData, position: tuple[int, int], force_monitor: Optional[tuple[int, int]] = None) -> None:
        """Record a movement for time and speed.

        There are some caveats that are hard to handle. If a mouse is
        programmatically moved, then it will jump to a location on the
        screen. A check can be done to skip drawing if the cursor wasn't
        previously moving, but the first frame of movement wil also
        always get skipped. Detecting the vector of movement didn't
        work as well as expected, and would have been too complex to
        maintain.

        There's never been an issue with the original script, so the
        behaviour has been copied.
        - Time tracks are fully recorded, and will capture jumps.
        This is fine as those tracks will be buried over time.
        - Speed tracks are only recorded if the cursor was previously
        moving, the downside being it will still record any jumps while
        moving, and will always skip the first frame of movement.
        """
        # If the ticks match then overwrite the old data
        if self.tick.current == data.move_tick:
            data.position = position

        distance = calculate_distance(position, data.position)
        data.distance += distance
        moving = self.tick.current == data.move_tick + 1

        # Add the pixels to an array
        for pixel in calculate_line(position, data.position):
            if force_monitor is None:
                result = self._monitor_offset(pixel)
                if result is None:
                    continue
                current_monitor, pixel = result
            else:
                current_monitor = force_monitor

            index = (pixel[1], pixel[0])
            data.time_arrays[current_monitor][index] = data.move_count
            data.count_arrays[current_monitor][index] += 1
            if distance and moving:
                data.speed_arrays[current_monitor][index] = max(data.speed_arrays[current_monitor][index], int(100 * distance))

        # Update the saved data
        data.position = position
        data.move_count += 1
        data.move_tick = self.tick.current

        if data.requires_compression():
            print(f'[Processing] Tracking threshold reached, reducing values...')
            data.compress()
            print(f'[Processing] Reduced all arrays')

    def _render_array(self, message: ipc.RenderRequest):
        """Render an array (tracks / heatmaps)."""
        print('[Processing] Render request received...')
        width = message.width
        height = message.height

        if message.application:
            app_data = self._app_data[message.application]
        else:
            app_data = self.app

        # Choose the data to render
        maps: list[tuple[tuple[int, int], IntArrayHandler]]
        match message.type:
            case ipc.RenderType.Time:
                maps = [(res, handler) for res, handler in app_data.cursor_map.time_arrays.items()]

            case ipc.RenderType.TimeHeatmap:
                maps = [(res, handler) for res, handler in app_data.cursor_map.count_arrays.items()]

            # Subtract a value from each array and ensure it doesn't go below 0
            case ipc.RenderType.TimeSincePause:
                maps = []
                for res, handler in app_data.cursor_map.time_arrays.items():
                    partial_array = handler.array.astype(np.int64) - self.pause_tick
                    partial_array[partial_array < 0] = 0
                    maps.append((res, IntArrayHandler(partial_array)))

            case ipc.RenderType.Speed:
                maps = [(res, handler) for res, handler in app_data.cursor_map.speed_arrays.items()]

            case ipc.RenderType.SingleClick:
                maps = []
                for map in app_data.mouse_single_clicks.values():
                    maps.extend((res, handler) for res, handler in map.items())

            case ipc.RenderType.DoubleClick:
                maps = []
                for map in app_data.mouse_double_clicks.values():
                    maps.extend((res, handler) for res, handler in map.items())

            case ipc.RenderType.HeldClick:
                maps = []
                for map in app_data.mouse_held_clicks.values():
                    maps.extend((res, handler) for res, handler in map.items())

            case ipc.RenderType.Thumbstick_R:
                maps = []
                for gamepad_maps in app_data.thumbstick_r_map.values():
                    map = gamepad_maps.time_arrays
                    maps.extend((res, handler) for res, handler in map.items())

            case ipc.RenderType.Thumbstick_L:
                maps = []
                for gamepad_maps in app_data.thumbstick_l_map.values():
                    map = gamepad_maps.time_arrays
                    maps.extend((res, handler) for res, handler in map.items())

            case ipc.RenderType.Thumbstick_R_SPEED:
                maps = []
                for gamepad_maps in app_data.thumbstick_r_map.values():
                    map = gamepad_maps.speed_arrays
                    maps.extend((res, handler) for res, handler in map.items())

            case ipc.RenderType.Thumbstick_L_SPEED:
                maps = []
                for gamepad_maps in app_data.thumbstick_l_map.values():
                    map = gamepad_maps.speed_arrays
                    maps.extend((res, handler) for res, handler in map.items())

            case ipc.RenderType.Thumbstick_R_Heatmap:
                maps = []
                for gamepad_maps in app_data.thumbstick_r_map.values():
                    map = gamepad_maps.count_arrays
                    maps.extend((res, handler) for res, handler in map.items())

            case ipc.RenderType.Thumbstick_L_Heatmap:
                maps = []
                for gamepad_maps in app_data.thumbstick_l_map.values():
                    map = gamepad_maps.count_arrays
                    maps.extend((res, handler) for res, handler in map.items())

            case ipc.RenderType.Trigger:
                maps = []
                for gamepad_maps in app_data.trigger_map.values():
                    map = gamepad_maps.time_arrays
                    maps.extend((res, handler) for res, handler in map.items())

            case ipc.RenderType.TriggerHeatmap:
                maps = []
                for gamepad_maps in app_data.trigger_map.values():
                    map = gamepad_maps.count_arrays
                    maps.extend((res, handler) for res, handler in map.items())

            case _:
                raise NotImplementedError(message.type)

        # Find the largest most common resolution
        width, height = array_target_resolution(maps, width, height)

        # Apply the sampling amount
        scale_width = int(width * message.sampling)
        scale_height = int(height * message.sampling)

        # Scale all arrays to the same size and combine
        if maps:
            rescaled_arrays = [array_rescale(handler.array, scale_width, scale_height) for res, handler in maps]
            final_array = np.maximum.reduce(rescaled_arrays)
        else:
            final_array = np.zeros((scale_height, scale_width), dtype=np.int8)

        # Special case for heatmaps
        if message.type in (ipc.RenderType.SingleClick, ipc.RenderType.DoubleClick, ipc.RenderType.HeldClick, ipc.RenderType.TriggerHeatmap,
                            ipc.RenderType.TimeHeatmap, ipc.RenderType.Thumbstick_L_Heatmap, ipc.RenderType.Thumbstick_R_Heatmap):
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

        self.q_send.put(ipc.Render(message.type, coloured_array, message.sampling))
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
                self._record_move(self.app.cursor_map, message.position)

            case ipc.MouseHeld():
                self.tick.set_active()

                result = self._monitor_offset(message.position)
                if result is not None:
                    current_monitor, pixel = result
                    index = (pixel[1], pixel[0])
                    self.app.mouse_held_clicks[message.button][current_monitor][index] += 1

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
                    arrays = self.app.mouse_double_clicks[message.button]
                    print(f'[Processing] Mouse button {message.button} double clicked.')
                else:
                    arrays = self.app.mouse_single_clicks[message.button]
                    print(f'[Processing] Mouse button {message.button} clicked.')

                result = self._monitor_offset(message.position)
                if result is not None:
                    current_monitor, pixel = result
                    index = (pixel[1], pixel[0])
                    arrays[current_monitor][index] += 1

                self.previous_mouse_click = PreviousMouseClick(message, self.tick.current, double_click)

            case ipc.KeyPress():
                self.tick.set_active()
                print(f'[Processing] Key {message.opcode} pressed.')
                self.app.key_presses[message.opcode] += 1

            case ipc.KeyHeld():
                self.tick.set_active()
                self.app.key_held[message.opcode] += 1

            case ipc.ButtonPress():
                self.tick.set_active()
                print(f'[Processing] Key {message.opcode} pressed.')
                self.app.button_presses[message.gamepad][int(math.log2(message.opcode))] += 1

            case ipc.ButtonHeld():
                self.tick.set_active()
                self.app.button_held[message.gamepad][int(math.log2(message.opcode))] += 1

            case ipc.MonitorsChanged():
                print(f'[Processing] Monitors changed.')
                self.monitor_data = message.data

            case ipc.ThumbstickMove():
                self.tick.set_active()
                width = height = 2048
                x = int((message.position[0] + 1) * (width - 1) / 2)
                y = int((message.position[1] + 1) * (height - 1) / 2)
                remapped = (x, height - y - 1)
                match message.thumbstick:
                    case ipc.ThumbstickMove.Thumbstick.Left:
                        self._record_move(self.app.thumbstick_l_map[message.gamepad], remapped, (width, height))
                    case ipc.ThumbstickMove.Thumbstick.Right:
                        self._record_move(self.app.thumbstick_r_map[message.gamepad], remapped, (width, height))
                    case _:
                        raise NotImplementedError(message.thumbstick)

            case ipc.TriggerMove():
                width = height = 2048
                x = int(message.left * (width - 1))
                y = int(message.right * (height - 1))
                self._record_move(self.app.trigger_map[message.gamepad], (x, y), (width, height))

            case ipc.DebugRaiseError():
                raise RuntimeError('test exception')

            case ipc.TrackingState():
                match message.state:
                    case ipc.TrackingState.State.Start:
                        self.app.cursor_map.position = cursor_position()
                    case ipc.TrackingState.State.Stop:
                        raise ExitRequest
                    case ipc.TrackingState.State.Pause:
                        self.pause_tick = self.app.cursor_map.move_count
                self.state = message.state

            case ipc.NoApplication():
                changed = self._current_app is not None
                self._current_app = None

                if changed:
                    self.app.cursor_map.position = cursor_position()

            case ipc.Application():
                app = Application(message.name, message.position, message.resolution)
                changed = self._current_app != app
                self._current_app = app

                if changed:
                    self.app.cursor_map.position = cursor_position()

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
