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
from ...file import MovementMaps, ApplicationData, ApplicationDataLoader, get_filename
from ...typing import ArrayLike
from ...utils.math import calculate_line, calculate_distance, calculate_pixel_offset
from ...utils.win import cursor_position, monitor_locations
from ...constants import DEFAULT_APPLICATION_NAME, UPDATES_PER_SECOND, DOUBLE_CLICK_MS, DOUBLE_CLICK_TOL, RADIAL_ARRAY_SIZE
from ...render import render



class ExitRequest(Exception):
    """Custom exception to raise and catch when an exit is requested."""


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
class Application:
    name: str
    rect: Optional[tuple[int, int, int, int]]


class Processing:
    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        self.q_send = q_send
        self.q_receive = q_receive

        self.tick = 0

        self.previous_mouse_click: Optional[PreviousMouseClick] = None
        self.monitor_data = monitor_locations()
        self.previous_monitor = None
        self.pause_tick = 0
        self.state = ipc.TrackingState.State.Pause

        # Load in the default application
        self.all_application_data: dict[str, ApplicationData] = ApplicationDataLoader()
        self.default_application = Application(DEFAULT_APPLICATION_NAME, None)
        self._current_application = Application('', None)
        self.current_application = self.default_application

    @property
    def application_data(self) -> ApplicationData:
        """Get the data for the current application."""
        return self.all_application_data[self.current_application.name]

    @property
    def current_application(self) -> Application:
        """Get the currently loaded application."""
        return self._current_application

    @current_application.setter
    def current_application(self, application: Application):
        """Update the currently loaded application."""
        previous_data = self.application_data
        previous_app, self._current_application = self._current_application, application

        if application != previous_app:
            # Lock in the previous activity data
            previous_data.tick.current = self.tick
            previous_data.tick.set_active()

            # Start new activity data
            self.application_data.tick.current = self.application_data.tick.previous = self.tick

            # Reset the cursor position
            self.application_data.cursor_map.position = None

            clicks = 0
            for resolution_maps in self.application_data.mouse_single_clicks.values():
                for array in resolution_maps.values():
                    clicks += np.sum(array)

            # Send data back to the GUI
            self.q_send.put(ipc.ApplicationLoadedData(
                application=self.current_application.name,
                distance=self.application_data.cursor_map.distance,
                cursor_counter=self.application_data.cursor_map.counter,
                thumb_l_counter=self.application_data.thumbstick_l_map[0].counter if self.application_data.thumbstick_l_map else 0,
                thumb_r_counter=self.application_data.thumbstick_r_map[0].counter if self.application_data.thumbstick_r_map else 0,
                clicks=clicks,
                keys_pressed=np.sum(self.application_data.key_presses),
                buttons_pressed=sum(np.sum(array) for array in self.application_data.button_presses.values()),
                active_time=self.application_data.tick.activity,
                inactive_time=self.application_data.tick.inactivity,
            ))

    def _monitor_offset(self, pixel: tuple[int, int]) -> Optional[tuple[tuple[int, int], tuple[int, int]]]:
        """Detect which monitor the pixel is on."""
        use_app = self.current_application is not None and self.current_application.rect is not None
        if use_app:
            monitor_data = [self.current_application.rect]
        else:
            monitor_data = self.monitor_data

        for x1, y1, x2, y2 in monitor_data:
            result = calculate_pixel_offset(pixel[0], pixel[1], x1, y1, x2, y2)
            if result is not None:
                return result
        return None

    def _record_move(self, data: MovementMaps, position: tuple[int, int], force_monitor: Optional[tuple[int, int]] = None) -> None:
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
        if self.tick == data.tick:
            data.position = position

        distance = calculate_distance(position, data.position)
        data.distance += distance
        moving = self.tick == data.tick + 1

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
            data.sequential_arrays[current_monitor][index] = data.counter
            data.density_arrays[current_monitor][index] += 1
            if distance and moving:
                data.speed_arrays[current_monitor][index] = max(data.speed_arrays[current_monitor][index], int(100 * distance))

        # Update the saved data
        data.position = position
        data.counter += 1
        data.ticks += 1
        data.tick = self.tick

        if data.requires_compression():
            print(f'[Processing] Tracking threshold reached, reducing values...')
            data.run_compression()
            print(f'[Processing] Reduced all arrays')

    def _arrays_for_rendering(self, profile: ApplicationData, render_type: ipc.RenderType) -> list[ArrayLike]:
        """Get a list of arrays to use for a render."""
        arrays: list[ArrayLike] = []
        match render_type:
            case ipc.RenderType.Time:
                arrays.extend(profile.cursor_map.sequential_arrays.values())

            case ipc.RenderType.TimeHeatmap:
                arrays.extend(profile.cursor_map.density_arrays.values())

            # Subtract a value from each array and ensure it doesn't go below 0
            case ipc.RenderType.TimeSincePause:
                for array in profile.cursor_map.sequential_arrays.values():
                    partial_array = np.asarray(array).astype(np.int64) - self.pause_tick
                    partial_array[partial_array < 0] = 0
                    arrays.append(partial_array)

            case ipc.RenderType.Speed:
                arrays.extend(profile.cursor_map.speed_arrays.values())

            case ipc.RenderType.SingleClick:
                for map in profile.mouse_single_clicks.values():
                    arrays.extend(map.values())

            case ipc.RenderType.DoubleClick:
                for map in profile.mouse_double_clicks.values():
                    arrays.extend(map.values())

            case ipc.RenderType.HeldClick:
                for map in profile.mouse_held_clicks.values():
                    arrays.extend(map.values())

            case ipc.RenderType.Thumbstick_R:
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.sequential_arrays
                    arrays.extend(map.values())

            case ipc.RenderType.Thumbstick_L:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.sequential_arrays
                    arrays.extend(map.values())

            case ipc.RenderType.Thumbstick_R_SPEED:
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.speed_arrays
                    arrays.extend(map.values())

            case ipc.RenderType.Thumbstick_L_SPEED:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.speed_arrays
                    arrays.extend(map.values())

            case ipc.RenderType.Thumbstick_R_Heatmap:
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.density_arrays
                    arrays.extend(map.values())

            case ipc.RenderType.Thumbstick_L_Heatmap:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.density_arrays
                    arrays.extend(map.values())

            case _:
                raise NotImplementedError(render_type)

        return arrays

    def _render_array(self, profile: ApplicationData, render_type: ipc.RenderType, width: Optional[int], height: Optional[int],
                      colour_map: str, sampling: int = 1) -> np.ndarray:
        """Render an array (tracks / heatmaps)."""
        is_heatmap = render_type in (ipc.RenderType.SingleClick, ipc.RenderType.DoubleClick, ipc.RenderType.HeldClick,
                                     ipc.RenderType.TimeHeatmap, ipc.RenderType.Thumbstick_L_Heatmap, ipc.RenderType.Thumbstick_R_Heatmap)
        arrays = self._arrays_for_rendering(profile, render_type)
        image = render(colour_map, arrays, width, height, sampling, linear=is_heatmap, blur=is_heatmap)
        return image

    def _process_message(self, message: ipc.Message) -> None:
        """Process an item of data."""
        match message:
            # Update the current tick
            case ipc.Tick():
                self.tick = self.application_data.tick.current = message.tick

            case ipc.RenderRequest():
                print('[Processing] Render request received...')
                if message.application:
                    profile = self.all_application_data[message.application]
                else:
                    profile = self.application_data

                image = self._render_array(profile, message.type, message.width, message.height, message.colour_map, message.sampling)
                self.q_send.put(ipc.Render(image, message.sampling, message.thumbnail))

                print('[Processing] Render request completed')

            case ipc.MouseMove():
                self.application_data.tick.set_active()
                self._record_move(self.application_data.cursor_map, message.position)

            case ipc.MouseHeld():
                self.application_data.tick.set_active()

                result = self._monitor_offset(message.position)
                if result is not None:
                    current_monitor, pixel = result
                    index = (pixel[1], pixel[0])
                    self.application_data.mouse_held_clicks[message.button][current_monitor][index] += 1

            case ipc.MouseClick():
                self.application_data.tick.set_active()

                previous = self.previous_mouse_click
                double_click = (
                    previous is not None
                    and previous.button == message.button
                    and previous.tick + (UPDATES_PER_SECOND * DOUBLE_CLICK_MS / 1000) > self.tick
                    and calculate_distance(previous.position, message.position) <= DOUBLE_CLICK_TOL
                    and not previous.double_clicked
                )

                if double_click:
                    arrays = self.application_data.mouse_double_clicks[message.button]
                    print(f'[Processing] Mouse button {message.button} double clicked.')
                else:
                    arrays = self.application_data.mouse_single_clicks[message.button]
                    print(f'[Processing] Mouse button {message.button} clicked.')

                result = self._monitor_offset(message.position)
                if result is not None:
                    current_monitor, pixel = result
                    index = (pixel[1], pixel[0])
                    arrays[current_monitor][index] += 1

                self.previous_mouse_click = PreviousMouseClick(message, self.tick, double_click)

            case ipc.KeyPress():
                self.application_data.tick.set_active()
                print(f'[Processing] Key {message.opcode} pressed.')
                self.application_data.key_presses[message.opcode] += 1

            case ipc.KeyHeld():
                self.application_data.tick.set_active()
                self.application_data.key_held[message.opcode] += 1

            case ipc.ButtonPress():
                self.application_data.tick.set_active()
                print(f'[Processing] Key {message.opcode} pressed.')
                self.application_data.button_presses[message.gamepad][int(math.log2(message.opcode))] += 1

            case ipc.ButtonHeld():
                self.application_data.tick.set_active()
                self.application_data.button_held[message.gamepad][int(math.log2(message.opcode))] += 1

            case ipc.MonitorsChanged():
                print(f'[Processing] Monitors changed.')
                self.monitor_data = message.data

            case ipc.ThumbstickMove():
                self.application_data.tick.set_active()
                width = height = RADIAL_ARRAY_SIZE
                x = int((message.position[0] + 1) * (width - 1) / 2)
                y = int((message.position[1] + 1) * (height - 1) / 2)
                remapped = (x, height - y - 1)
                match message.thumbstick:
                    case ipc.ThumbstickMove.Thumbstick.Left:
                        self._record_move(self.application_data.thumbstick_l_map[message.gamepad], remapped, (width, height))
                    case ipc.ThumbstickMove.Thumbstick.Right:
                        self._record_move(self.application_data.thumbstick_r_map[message.gamepad], remapped, (width, height))
                    case _:
                        raise NotImplementedError(message.thumbstick)

            case ipc.DebugRaiseError():
                raise RuntimeError('test exception')

            case ipc.TrackingState():
                match message.state:
                    case ipc.TrackingState.State.Start:
                        self.application_data.cursor_map.position = cursor_position()
                    case ipc.TrackingState.State.Stop:
                        raise ExitRequest
                    case ipc.TrackingState.State.Pause:
                        self.pause_tick = self.application_data.cursor_map.counter
                self.state = message.state

            case ipc.Application():
                self.current_application = Application(message.name, message.rect)

            case ipc.Save():
                if message.application is None:
                    applications = self.all_application_data.keys()
                else:
                    applications = [message.application]

                for application in applications:
                    print(f'[Processing] Saving {application}...')
                    if self.all_application_data[application].modified:
                        self.all_application_data[application].save(get_filename(application))
                        print(f'[Processing] Saved {application}')
                    else:
                        print('[Processing] Skipping save, not modified')

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
            print(f'[Processing] Error shut down: {e}')

        self.q_send.put(ipc.ProcessShutDownNotification(ipc.Target.Processing))
        print('[Processing] Sent process closed notification.')


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
    Processing(q_send, q_receive).run()
