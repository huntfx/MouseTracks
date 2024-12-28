import math
import multiprocessing
import traceback

import numpy as np
from scipy import ndimage

from .. import ipc
from ...utils.math import calculate_line, calculate_distance
from ...utils.win import cursor_position, monitor_locations


class ExitRequest(Exception):
    """Custom exception to raise and catch when an exit is requested."""


class PixelArray(dict):
    def __init__(self, dtype: np.dtype):
        self._dtype = dtype

    def __missing__(self, key: tuple[int, int]) -> np.ndarray:
        self[key] = value = np.zeros((key[1], key[0]), dtype=np.int64)
        return value


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

    indices_y = np.linspace(0, input_height - 1, target_height).astype(int)
    indices_x = np.linspace(0, input_width - 1, target_width).astype(int)
    return np.ascontiguousarray(pooled_full[indices_y][:, indices_x])


def generate_colour_lookup(*colours: tuple[int, int, int], steps: int = 256) -> np.ndarray:
    """Generate a color lookup table transitioning smoothly between given colors."""
    lookup = np.zeros((steps, 3), dtype=np.uint8)

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


class Processing:
    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        self.q_send = q_send
        self.q_receive = q_receive

        self.mouse_track_maps = PixelArray(np.uint32)  # Up to 4,294,967,295
        self.mouse_speed_maps = PixelArray(np.uint16)  # Up to 65,535
        self.mouse_move_count = 0

        self.mouse_distance = 0
        self.mouse_position = cursor_position()
        self.mouse_move_tick = 0
        self.monitor_data = monitor_locations()
        self.previous_monitor = None

    def _monitor_offset(self, pixel: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]]:
        """Detect which monitor the pixel is on."""
        for x1, y1, x2, y2 in self.monitor_data:
            if x1 <= pixel[0] < x2 and y1 <= pixel[1] < y2:
                return ((x2 - x1, y2 - y1), (x1, y1))

    def _process_message(self, message: ipc.Message) -> bool:
        """Process an item of data."""
        match message:
            case ipc.ThumbnailRequest(type=ipc.ThumbnailType.Time | ipc.ThumbnailType.Speed):
                x1, y1, x2, y2 = self.monitor_data[0]
                width = x2 - x1
                height = y2 - y1

                match message.type:
                    case ipc.ThumbnailType.Time:
                        maps = self.mouse_track_maps
                    case ipc.ThumbnailType.Speed:
                        maps = self.mouse_speed_maps
                array = maps[(width, height)]

                # Downscale and normalise values from 0 to 255
                downscaled_array = array_rescale(array, message.width, message.height)
                max_time = np.max(downscaled_array) or 1
                normalised_array = (255 * downscaled_array / max_time).astype(np.uint8)

                # Map it to a colour lookup table
                colour_lookup = generate_colour_lookup((0, 0, 0), (255, 0, 0), (255, 255, 255))
                coloured_array = colour_lookup[normalised_array]

                self.q_send.put(ipc.Thumbnail(message.type, coloured_array, self.mouse_move_tick))

            case ipc.MouseMove():
                print(f'[Processing] Mouse has moved to {message.position}')
                is_moving = message.tick == self.mouse_move_tick + 1

                # Calculate basic data
                distance_to_previous = calculate_distance(message.position, self.mouse_position)
                self.mouse_distance += distance_to_previous

                # Get all the pixels between the two points
                pixels = [message.position]
                if is_moving and self.mouse_position != message.position:
                    pixels.extend(calculate_line(message.position, self.mouse_position))
                    pixels.append(self.mouse_position)

                # Add the pixels to an array
                for pixel in pixels:
                    current_monitor, offset = self._monitor_offset(pixel)
                    x = pixel[0] - offset[0]
                    y = pixel[1] - offset[1]
                    self.mouse_track_maps[current_monitor][(y, x)] = self.mouse_move_count
                    self.mouse_speed_maps[current_monitor][(y, x)] = distance_to_previous

                # Update the saved data
                self.mouse_position = message.position
                self.mouse_move_tick = message.tick
                self.mouse_move_count += 1

            case ipc.MouseClick(double=True):
                print(f'[Processing] Mouse button {message.button} double clicked.')

            case ipc.MouseClick():
                print(f'[Processing] Mouse button {message.button} clicked.')

            case ipc.MonitorsChanged():
                print(f'[Processing] Monitors changed.')
                self.monitor_data = message.data

            case ipc.DebugRaiseError():
                raise RuntimeError('test exception')

            case ipc.TrackingState(state=ipc.TrackingState.State.Stop):
                raise ExitRequest


    def run(self) -> None:
        print('[Processing] Loaded.')

        try:
            while True:
                self._process_message(self.q_receive.get())

        except ExitRequest:
            print('[Processing] Shut down.')

        # Catch error after KeyboardInterrupt
        except EOFError:
            return

        except Exception as e:
            self.q_send.put(ipc.Traceback(e, traceback.format_exc()))


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue):
    Processing(q_send, q_receive).run()
