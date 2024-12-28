import math
import multiprocessing
import numpy as np
import traceback

from .. import ipc
from ...utils.math import calculate_line, calculate_distance
from ...utils.win import cursor_position, monitor_locations

try:
    from scipy import ndimage
except ImportError:
    ndimage = None


class ExitRequest(Exception):
    """Custom exception to raise and catch when an exit is requested."""


class PixelArray(dict):
    def __init__(self, dtype: np.dtype):
        self._dtype = dtype

    def __missing__(self, key: tuple[int, int]) -> np.ndarray:
        self[key] = value = np.zeros((key[1], key[0]), dtype=np.int64)
        return value


def max_pool_downscale(array: np.ndarray, target_width: int, target_height: int) -> np.ndarray:
    """Downscale the array using max pooling with edge correction.

    All credit goes to ChatGPT here. With scipy it's a tiny bit faster
    but I've left both ways for the time being.
    """
    input_height, input_width = array.shape

    # Compute the pooling size
    block_width = input_width / target_width
    block_height = input_height / target_height

    # Use scipy
    if ndimage is not None:
        # Apply maximum filter with block size
        pooled_full = ndimage.maximum_filter(array, size=(int(math.ceil(block_height)), int(math.ceil(block_width))))

        # Downsample by slicing
        stride_y = input_height / target_height
        stride_x = input_width / target_width

        indices_y = (np.arange(target_height) * stride_y).astype(int)
        indices_x = (np.arange(target_width) * stride_x).astype(int)

        return np.ascontiguousarray(pooled_full[indices_y][:, indices_x])

    # Create an output array
    pooled = np.zeros((target_height, target_width), dtype=array.dtype)

    for y in range(target_height - 1):
        for x in range(target_width - 1):
            # Compute the bounds of the current block
            x_start = int(x * block_width)
            x_end = min(int((x + 1) * block_width), input_width)
            y_start = int(y * block_height)
            y_end = min(int((y + 1) * block_height), input_height)

            # Pool the maximum value from the block
            pooled[y, x] = array[y_start:y_end, x_start:x_end].max()

    return pooled


class Processing:
    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        self.q_send = q_send
        self.q_receive = q_receive

        self.mouse_track_maps = PixelArray(np.int32)  # Up to 2,147,483,648
        self.mouse_speed_maps = PixelArray(np.int16)  # Up to 32,767
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
            case ipc.ThumbnailRequest():
                x1, y1, x2, y2 = self.monitor_data[0]
                width = x2 - x1
                height = y2 - y1
                array = self.mouse_track_maps[(width, height)]

                # Resample the array to match the requested size
                downscaled = max_pool_downscale(array, message.width, message.height)

                # Normalize values from 0 to 255
                if np.any(downscaled):
                    downscaled = (255 * downscaled / np.max(downscaled))

                self.q_send.put(ipc.Thumbnail(downscaled, self.mouse_move_tick))

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
                for pixel in [self.mouse_position] + calculate_line(self.mouse_position, message.position) + [message.position]:
                    current_monitor, offset = self._monitor_offset(pixel)
                    x = pixel[0] - offset[0]
                    y = pixel[1] - offset[1]
                    self.mouse_track_maps[current_monitor][(y, x)] = self.mouse_move_count
                    self.mouse_speed_maps[current_monitor][(y, x)] = distance_to_previous

                # Update the saved data
                self.mouse_position = message.position
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
