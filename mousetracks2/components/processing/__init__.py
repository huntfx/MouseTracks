import math
import multiprocessing
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import psutil
import numpy as np

from mousetracks.image import colours
from .. import ipc
from ...file import MovementMaps, TrackingProfile, TrackingProfileLoader, get_filename
from ...typing import ArrayLike
from ...utils.math import calculate_line, calculate_distance, calculate_pixel_offset
from ...utils.win import cursor_position, monitor_locations, MOUSE_BUTTONS, MOUSE_OPCODES, SCROLL_EVENTS
from ...constants import DEFAULT_PROFILE_NAME, UPDATES_PER_SECOND, DOUBLE_CLICK_MS, DOUBLE_CLICK_TOL, RADIAL_ARRAY_SIZE, INACTIVITY_MS
from ...render import render, EmptyRenderError


def get_interface_name_by_mac(mac_address: str) -> Optional[str]:
    """Get the name of the network interface by MAC address."""
    for interface_name, addresses in psutil.net_if_addrs().items():
        for addr in addresses:
            if addr.family == psutil.AF_LINK:
                if addr.address == mac_address:
                    return interface_name
    return None


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
        self._timestamp = None

        self.previous_mouse_click: Optional[PreviousMouseClick] = None
        self.monitor_data = monitor_locations()
        self.previous_monitor = None
        self.pause_tick = 0
        self.state = ipc.TrackingState.State.Pause

        # Load in the default profile
        self.all_profiles: dict[str, TrackingProfile] = TrackingProfileLoader()
        self._current_application = Application('', None)
        self.current_application = Application(DEFAULT_PROFILE_NAME, None)

    @property
    def timestamp(self) -> int:
        """Get the timestamp."""
        if self._timestamp is None:
            raise RuntimeError('no tick data received')
        return self._timestamp

    @timestamp.setter
    def timestamp(self, timestamp: int) -> None:
        """Set the timestamp."""
        self._timestamp = timestamp

    @property
    def profile(self) -> TrackingProfile:
        """Get the data for the current application."""
        return self.all_profiles[self.current_application.name]

    @property
    def current_application(self) -> Application:
        """Get the currently loaded application."""
        return self._current_application

    @current_application.setter
    def current_application(self, application: Application):
        """Update the currently loaded application."""
        if application == self._current_application:
            return
        self._current_application = application

        # Reset the cursor position
        self.profile.cursor_map.position = None

        # Count total clicks
        clicks = 0
        for resolution_maps in self.profile.mouse_single_clicks.values():
            for array in resolution_maps.values():
                clicks += np.sum(array)

        # Count scrolls
        scrolls = 0
        for opcode in SCROLL_EVENTS:
            scrolls += self.profile.key_held[opcode]

        # Send data back to the GUI
        self.q_send.put(ipc.ProfileLoaded(
            application=self.current_application.name,
            distance=self.profile.cursor_map.distance,
            cursor_counter=self.profile.cursor_map.counter,
            thumb_l_counter=self.profile.thumbstick_l_map[0].counter if self.profile.thumbstick_l_map else 0,
            thumb_r_counter=self.profile.thumbstick_r_map[0].counter if self.profile.thumbstick_r_map else 0,
            clicks=clicks,
            scrolls=scrolls,
            keys_pressed=np.sum(self.profile.key_presses),
            buttons_pressed=sum(np.sum(array) for array in self.profile.button_presses.values()),
            elapsed_ticks=self.profile.elapsed,
            active_ticks=self.profile.active,
            inactive_ticks=self.profile.inactive,
            bytes_sent=sum(self.profile.data_upload.values()),
            bytes_recv=sum(self.profile.data_download.values()),
        ))

    @property
    def profile_age_days(self) -> int:
        """Get the number of days since the profile was created.
        This is for use with the daily stats.
        """
        creation_day = self.profile.created // 86400
        current_day = self.timestamp // 86400
        return current_day - creation_day

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

    def _record_move(self, data: MovementMaps, position: tuple[int, int], force_monitor: Optional[tuple[int, int]] = None) -> float:
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

        return distance

    def _arrays_for_rendering(self, profile: TrackingProfile, render_type: ipc.RenderType) -> dict[tuple[int, int], list[ArrayLike]]:
        """Get a list of arrays to use for a render."""
        arrays: dict[tuple[int, int], list[ArrayLike]] = defaultdict(list)
        match render_type:
            case ipc.RenderType.Time:
                arrays[0, 0].extend(profile.cursor_map.sequential_arrays.values())

            case ipc.RenderType.TimeHeatmap:
                arrays[0, 0].extend(profile.cursor_map.density_arrays.values())

            # Subtract a value from each array and ensure it doesn't go below 0
            case ipc.RenderType.TimeSincePause:
                for array in profile.cursor_map.sequential_arrays.values():
                    partial_array = np.asarray(array).astype(np.int64) - self.pause_tick
                    partial_array[partial_array < 0] = 0
                    arrays[0, 0].append(partial_array)

            case ipc.RenderType.Speed:
                arrays[0, 0].extend(profile.cursor_map.speed_arrays.values())

            case ipc.RenderType.SingleClick:
                for map in profile.mouse_single_clicks.values():
                    arrays[0, 0].extend(map.values())

            case ipc.RenderType.DoubleClick:
                for map in profile.mouse_double_clicks.values():
                    arrays[0, 0].extend(map.values())

            case ipc.RenderType.HeldClick:
                for map in profile.mouse_held_clicks.values():
                    arrays[0, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_R:
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.sequential_arrays
                    arrays[0, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_L:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.sequential_arrays
                    arrays[0, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_C:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.sequential_arrays
                    arrays[0, 0].extend(map.values())
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.sequential_arrays
                    arrays[1, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_R_SPEED:
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.speed_arrays
                    arrays[0, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_L_SPEED:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.speed_arrays
                    arrays[0, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_C_SPEED:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.speed_arrays
                    arrays[0, 0].extend(map.values())
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.speed_arrays
                    arrays[1, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_R_Heatmap:
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.density_arrays
                    arrays[0, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_L_Heatmap:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.density_arrays
                    arrays[0, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_C_Heatmap:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.density_arrays
                    arrays[0, 0].extend(map.values())
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.density_arrays
                    arrays[1, 0].extend(map.values())

            case _:
                raise NotImplementedError(render_type)

        return arrays

    def _render_array(self, profile: TrackingProfile, render_type: ipc.RenderType, width: Optional[int], height: Optional[int],
                      colour_map: str, sampling: int = 1) -> np.ndarray:
        """Render an array (tracks / heatmaps)."""
        is_heatmap = render_type in (ipc.RenderType.SingleClick, ipc.RenderType.DoubleClick, ipc.RenderType.HeldClick, ipc.RenderType.TimeHeatmap,
                                     ipc.RenderType.Thumbstick_L_Heatmap, ipc.RenderType.Thumbstick_R_Heatmap, ipc.RenderType.Thumbstick_C_Heatmap)
        positional_arrays = self._arrays_for_rendering(profile, render_type)
        try:
            image = render(colour_map, positional_arrays, width, height, sampling, linear=is_heatmap, blur=is_heatmap)
        except EmptyRenderError:
            image = np.ndarray([0, 0, 3])
        return image

    def _record_active_tick(self, profile_name: str, ticks: int) -> None:
        profile = self.all_profiles[profile_name]
        profile.active += ticks
        profile.daily_ticks[self.profile_age_days, 1] += ticks

    def _record_inactive_tick(self, profile_name: str, ticks: int) -> None:
        profile = self.all_profiles[profile_name]
        profile.inactive += ticks
        profile.daily_ticks[self.profile_age_days, 2] += ticks

    def _save(self, profile_name: str) -> bool:
        """Save a profile to disk.
        See `ipc.SaveReady` for information on why the `inactivity`
        parameter is required.
        """
        print(f'[Processing] Saving {profile_name}...')
        profile = self.all_profiles[profile_name]
        if not profile.modified:
            print('[Processing] Skipping save, not modified')
            return False

        # To keep the active/inactive time in sync with elapsed,
        # temporarily add the current data to the profile
        # This is the same logic in the GUI
        inactivity_threshold = UPDATES_PER_SECOND * INACTIVITY_MS / 1000
        tick_diff = profile.elapsed - (profile.active + profile.inactive)
        if tick_diff > inactivity_threshold:
            self._record_inactive_tick(profile_name, tick_diff)
        elif tick_diff:
            self._record_active_tick(profile_name, tick_diff)

        result = profile.save(get_filename(profile_name))

        # Undo the temporary sync
        if tick_diff > inactivity_threshold:
            self._record_inactive_tick(profile_name, -tick_diff)
        elif tick_diff:
            self._record_active_tick(profile_name, -tick_diff)

        if result:
            print(f'[Processing] Saved {profile_name}')
            return True

        print(f'[Processing] Failed to save {profile_name}')
        return False

    def _process_message(self, message: ipc.Message) -> None:
        """Process an item of data."""
        match message:
            case ipc.Tick():
                # Set variables
                self.tick = message.tick
                self.timestamp = message.timestamp

                # Update profile data
                self.profile.elapsed += 1
                self.profile.daily_ticks[self.profile_age_days, 0] += 1

                # This message triggers once per tick, so the current profile is always "modified"
                self.profile.modified = True

            case ipc.Active():
                self._record_active_tick(message.profile_name, message.ticks)

            case ipc.Inactive():
                self._record_inactive_tick(message.profile_name, message.ticks)

            case ipc.RenderRequest():
                print('[Processing] Render request received...')
                if message.application:
                    profile = self.all_profiles[message.application]
                else:
                    profile = self.profile

                image = self._render_array(profile, message.type, message.width, message.height, message.colour_map, message.sampling)
                self.q_send.put(ipc.Render(image, message.sampling, message.thumbnail))

                print('[Processing] Render request completed')

            case ipc.MouseMove():
                distance = self._record_move(self.profile.cursor_map, message.position)
                self.profile.daily_distance[self.profile_age_days] += distance

            case ipc.MouseHeld():
                result = self._monitor_offset(message.position)
                if result is not None:
                    current_monitor, pixel = result
                    index = (pixel[1], pixel[0])
                    self.profile.mouse_held_clicks[message.button][current_monitor][index] += 1

            case ipc.MouseClick():
                previous = self.previous_mouse_click
                double_click = (
                    previous is not None
                    and previous.button == message.button
                    and previous.tick + (UPDATES_PER_SECOND * DOUBLE_CLICK_MS / 1000) > self.tick
                    and calculate_distance(previous.position, message.position) <= DOUBLE_CLICK_TOL
                    and not previous.double_clicked
                )

                if double_click:
                    arrays = self.profile.mouse_double_clicks[message.button]
                    print(f'[Processing] Mouse button {message.button} double clicked.')
                else:
                    arrays = self.profile.mouse_single_clicks[message.button]
                    print(f'[Processing] Mouse button {message.button} clicked.')

                result = self._monitor_offset(message.position)
                if result is not None:
                    current_monitor, pixel = result
                    index = (pixel[1], pixel[0])
                    arrays[current_monitor][index] += 1

                self.previous_mouse_click = PreviousMouseClick(message, self.tick, double_click)

            case ipc.KeyPress():
                if message.opcode not in MOUSE_BUTTONS:
                    print(f'[Processing] Key {message.opcode} pressed.')
                self.profile.key_presses[message.opcode] += 1
                self.profile.key_held[message.opcode] += 1

                if message.opcode in MOUSE_OPCODES:
                    self.profile.daily_clicks[self.profile_age_days] += 1
                else:
                    self.profile.daily_keys[self.profile_age_days] += 1

            case ipc.KeyHeld():
                if message.opcode in SCROLL_EVENTS:
                    print(f'[Processing] Scroll {message.opcode} triggered.')
                    self.profile.daily_scrolls[self.profile_age_days] += 1
                self.profile.key_held[message.opcode] += 1

            case ipc.ButtonPress():
                print(f'[Processing] Key {message.opcode} pressed.')
                self.profile.button_presses[message.gamepad][int(math.log2(message.opcode))] += 1
                self.profile.button_held[message.gamepad][int(math.log2(message.opcode))] += 1
                self.profile.daily_buttons[self.profile_age_days] += 1

            case ipc.ButtonHeld():
                self.profile.button_held[message.gamepad][int(math.log2(message.opcode))] += 1

            case ipc.MonitorsChanged():
                print(f'[Processing] Monitors changed.')
                self.monitor_data = message.data

            case ipc.ThumbstickMove():
                width = height = RADIAL_ARRAY_SIZE
                x = int((message.position[0] + 1) * (width - 1) / 2)
                y = int((message.position[1] + 1) * (height - 1) / 2)
                remapped = (x, height - y - 1)
                match message.thumbstick:
                    case ipc.ThumbstickMove.Thumbstick.Left:
                        self._record_move(self.profile.thumbstick_l_map[message.gamepad], remapped, (width, height))
                    case ipc.ThumbstickMove.Thumbstick.Right:
                        self._record_move(self.profile.thumbstick_r_map[message.gamepad], remapped, (width, height))
                    case _:
                        raise NotImplementedError(message.thumbstick)

            case ipc.DebugRaiseError():
                raise RuntimeError('test exception')

            case ipc.TrackingState():
                match message.state:
                    case ipc.TrackingState.State.Start:
                        self.profile.cursor_map.position = cursor_position()
                    case ipc.TrackingState.State.Stop:
                        raise ExitRequest
                    case ipc.TrackingState.State.Pause:
                        self.pause_tick = self.profile.cursor_map.counter
                self.state = message.state

            case ipc.ApplicationDetected():
                self.current_application = Application(message.name, message.rect)

            case ipc.Save():
                # Keep track of what saved and what didn't
                succeeded = []
                failed = []
                for name, profile in tuple(self.all_profiles.items()):
                    # If not modified since last time, unload it from memory
                    if not profile.modified:
                        print(f'[Processing] Unloading profile: {name}')
                        del self.all_profiles[name]

                    # Attempt the save
                    elif self._save(name):
                        succeeded.append(name)
                    else:
                        failed.append(name)
                self.q_send.put(ipc.SaveComplete(succeeded, failed))

            case ipc.DataTransfer():
                self.profile.data_upload[message.mac_address] += message.bytes_sent
                self.profile.data_download[message.mac_address] += message.bytes_recv
                self.profile.daily_upload[self.profile_age_days] += message.bytes_sent
                self.profile.daily_download[self.profile_age_days] += message.bytes_recv

                if message.mac_address not in self.profile.data_interfaces:
                    self.profile.data_interfaces[message.mac_address] = get_interface_name_by_mac(message.mac_address)

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
            traceback.print_exc()
            print(f'[Processing] Error shut down: {e}')

        self.q_send.put(ipc.ProcessShutDownNotification(ipc.Target.Processing))
        print('[Processing] Sent process closed notification.')


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
    Processing(q_send, q_receive).run()
