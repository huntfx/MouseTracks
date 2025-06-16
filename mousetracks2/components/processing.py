import math
import os
import time
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Iterator, Literal

import numpy as np

from . import ipc
from .abstract import Component
from ..config.cli import CLI
from ..config.settings import GlobalConfig
from ..exceptions import ExitRequest
from ..export import Export
from ..file import ArrayResolutionMap, MovementMaps, TrackingProfile, TrackingProfileLoader, get_filename, santise_profile_name
from ..legacy import keyboard
from ..utils import keycodes, get_cursor_pos
from ..utils.math import calculate_line, calculate_distance, calculate_pixel_offset
from ..utils.network import Interfaces
from ..utils.system import monitor_locations
from ..constants import DEFAULT_PROFILE_NAME, UPDATES_PER_SECOND, DOUBLE_CLICK_MS, DOUBLE_CLICK_TOL, RADIAL_ARRAY_SIZE, DEBUG
from ..render import render, EmptyRenderError


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
    rects: list[tuple[int, int, int, int]] = field(default_factory=list)


class Processing(Component):
    def __post_init__(self) -> None:
        self.tick = 0
        self._timestamp = -1

        self.previous_mouse_click: PreviousMouseClick | None = None
        self.monitor_data = monitor_locations()
        self.previous_monitor = None

        # Load in the default profile
        self.all_profiles = TrackingProfileLoader()
        self._current_application = Application('', [])
        self.current_application = Application(DEFAULT_PROFILE_NAME, [])

    @property
    def timestamp(self) -> int:
        """Get the timestamp."""
        if self._timestamp < 0:
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
    def current_application(self, application: Application) -> None:
        """Update the currently loaded application."""
        if application == self._current_application:
            return
        self._current_application = application

        # Reset the data
        self.profile.cursor_map.position = None

    def _send_profile_data(self, name: str) -> None:
        """Send all the stats for the profile."""
        profile = self.all_profiles[name]
        profile._last_accessed = time.time()

        # Count total clicks
        clicks = 0
        for keycode in keycodes.MOUSE_CODES:
            clicks += profile.key_presses[keycode]

        # Count scrolls
        scrolls = 0
        for keycode in keycodes.SCROLL_CODES:
            scrolls += profile.key_held[keycode]

        # Count keypresses
        keys = 0
        for keycode in keycodes.KEYBOARD_CODES:
            keys += profile.key_presses[keycode]

            # CONTROL is triggered with L CONTROL, R CONTROL and R MENU
            if keycode == keycodes.VK_CONTROL:
                keys -= profile.key_presses[keycodes.VK_LCONTROL]
                keys -= profile.key_presses[keycodes.VK_RCONTROL]
                keys -= profile.key_presses[keycodes.VK_RMENU]

            # MENU is triggered with L MENU and R MENU
            elif keycode == keycodes.VK_MENU:
                keys -= profile.key_presses[keycodes.VK_LMENU]
                keys -= profile.key_presses[keycodes.VK_RMENU]

        # Get all resolutions and how much data they contain
        resolutions: dict[tuple[int, int], tuple[int, bool]] = {}
        for resolution, array in profile.cursor_map.density_arrays.items():
            resolutions[resolution] = (int(np.sum(array)), resolution not in profile.config.disabled_resolutions)

        # Send data back to the GUI
        self.send_data(ipc.ProfileData(
            profile_name=profile.name,
            distance=profile.cursor_map.distance,
            cursor_counter=profile.cursor_map.counter,
            thumb_l_counter=profile.thumbstick_l_map[0].counter if profile.thumbstick_l_map else 0,
            thumb_r_counter=profile.thumbstick_r_map[0].counter if profile.thumbstick_r_map else 0,
            clicks=clicks,
            scrolls=scrolls,
            keys_pressed=keys,
            buttons_pressed=sum(int(np.sum(array)) for array in profile.button_presses.values()),
            elapsed_ticks=profile.elapsed,
            active_ticks=profile.active,
            inactive_ticks=profile.inactive,
            bytes_sent=sum(profile.data_upload.values()),
            bytes_recv=sum(profile.data_download.values()),
            config=profile.config,
            resolutions=resolutions,
            multi_monitor=profile.config.multi_monitor,
        ))

    @property
    def profile_age_days(self) -> int:
        """Get the number of days since the profile was created.
        This is for use with the daily stats.
        """
        creation_day = self.profile.created // 86400
        current_day = self.timestamp // 86400
        return max(0, current_day - creation_day)

    def _monitor_offset(self, pixel: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]] | None:
        """Detect which monitor the pixel is on."""
        monitor_data = self.monitor_data
        if self.current_application.rects:
            monitor_data = self.current_application.rects

        single_monitor = CLI.single_monitor if self.profile.config.multi_monitor is None else not self.profile.config.multi_monitor
        if single_monitor:
            x_min, y_min, x_max, y_max = monitor_data[0]
            for x1, y1, x2, y2 in monitor_data[1:]:
                x_min = min(x_min, x1)
                y_min = min(y_min, y1)
                x_max = max(x_max, x2)
                y_max = max(y_max, y2)
            result = calculate_pixel_offset(pixel[0], pixel[1], x_min, y_min, x_max, y_max)
            if result is not None:
                return result

        else:
            for x1, y1, x2, y2 in monitor_data:
                result = calculate_pixel_offset(pixel[0], pixel[1], x1, y1, x2, y2)
                if result is not None:
                    return result

        return None

    def _record_move(self, data: MovementMaps, position: tuple[int, int],
                     force_monitor: tuple[int, int] | None = None) -> float:
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

    def _arrays_for_rendering(self, profile: TrackingProfile, render_type: ipc.RenderType,
                              left_clicks: bool = True, middle_clicks: bool = True, right_clicks: bool = True,
                              ) -> dict[tuple[int, int], list[np.typing.ArrayLike]]:
        """Get a list of arrays to use for a render."""
        def get_arrays(array_map: ArrayResolutionMap) -> Iterator[np.typing.ArrayLike]:
            for resolution, arrays in array_map.items():
                if resolution not in profile.config.disabled_resolutions:
                    yield arrays

        arrays: dict[tuple[int, int], list[np.typing.ArrayLike]] = defaultdict(list)
        match render_type:
            case ipc.RenderType.Time:
                arrays[0, 0].extend(get_arrays(profile.cursor_map.sequential_arrays))

            case ipc.RenderType.TimeHeatmap:
                arrays[0, 0].extend(get_arrays(profile.cursor_map.density_arrays))

            case ipc.RenderType.Speed:
                arrays[0, 0].extend(get_arrays(profile.cursor_map.speed_arrays))

            case ipc.RenderType.SingleClick:
                for keycode, map in profile.mouse_single_clicks.items():
                    if keycode == keycodes.VK_LBUTTON and not left_clicks:
                        continue
                    if keycode == keycodes.VK_MBUTTON and not middle_clicks:
                        continue
                    if keycode == keycodes.VK_RBUTTON and not right_clicks:
                        continue
                    arrays[0, 0].extend(get_arrays(map))

            case ipc.RenderType.DoubleClick:
                for keycode, map in profile.mouse_double_clicks.items():
                    if keycode == keycodes.VK_LBUTTON and not left_clicks:
                        continue
                    if keycode == keycodes.VK_MBUTTON and not middle_clicks:
                        continue
                    if keycode == keycodes.VK_RBUTTON and not right_clicks:
                        continue
                    arrays[0, 0].extend(get_arrays(map))

            case ipc.RenderType.HeldClick:
                for keycode, map in profile.mouse_held_clicks.items():
                    if keycode == keycodes.VK_LBUTTON and not left_clicks:
                        continue
                    if keycode == keycodes.VK_MBUTTON and not middle_clicks:
                        continue
                    if keycode == keycodes.VK_RBUTTON and not right_clicks:
                        continue
                    arrays[0, 0].extend(get_arrays(map))

            case ipc.RenderType.Thumbstick_Time:
                if left_clicks:
                    for gamepad_maps in profile.thumbstick_l_map.values():
                        map = gamepad_maps.sequential_arrays
                        arrays[0, 0].extend(map.values())
                if right_clicks:
                    for gamepad_maps in profile.thumbstick_r_map.values():
                        map = gamepad_maps.sequential_arrays
                        arrays[int(left_clicks), 0].extend(map.values())

            case ipc.RenderType.Thumbstick_Speed:
                if left_clicks:
                    for gamepad_maps in profile.thumbstick_l_map.values():
                        map = gamepad_maps.speed_arrays
                        arrays[0, 0].extend(map.values())
                if right_clicks:
                    for gamepad_maps in profile.thumbstick_r_map.values():
                        map = gamepad_maps.speed_arrays
                        arrays[int(left_clicks), 0].extend(map.values())

            case ipc.RenderType.Thumbstick_Heatmap:
                if left_clicks:
                    for gamepad_maps in profile.thumbstick_l_map.values():
                        map = gamepad_maps.density_arrays
                        arrays[0, 0].extend(map.values())
                if right_clicks:
                    for gamepad_maps in profile.thumbstick_r_map.values():
                        map = gamepad_maps.density_arrays
                        arrays[int(left_clicks), 0].extend(map.values())

            case _:
                raise NotImplementedError(render_type)

        return arrays

    def _render_array(self, profile: TrackingProfile, render_type: ipc.RenderType,
                      width: int | None, height: int | None, colour_map: str, sampling: int = 1,
                      padding: int = 0, contrast: float = 1.0, lock_aspect: bool = True,
                      clipping: float = 0.0, blur: float = 0.0, linear: bool = False,
                      left_clicks: bool = True, middle_clicks: bool = True, right_clicks: bool = True,
                      interpolation_order: Literal[0, 1, 2, 3, 4, 5] = 0) -> np.ndarray:
        """Render an array (tracks / heatmaps)."""
        # Get the arrays to render
        positional_arrays = self._arrays_for_rendering(profile, render_type, left_clicks=left_clicks,
                                                       middle_clicks=middle_clicks, right_clicks=right_clicks)

        # Add extra padding
        if padding is not None:
            for position, arrays in positional_arrays.items():
                positional_arrays[position] = [np.pad(array, padding) for array in arrays]

        # Adjust width/height if not locking the aspect ratio
        if not lock_aspect and width is not None and height is not None:
            width //= max(x for x, y in positional_arrays) - min(x for x, y in positional_arrays) + 1
            height //= max(y for x, y in positional_arrays) - min(y for x, y in positional_arrays) + 1

        # Do the render
        try:
            image = render(colour_map, positional_arrays, width, height, sampling,
                           lock_aspect=lock_aspect, linear=linear,
                           blur=blur, contrast=contrast, clipping=clipping,
                           interpolation_order=interpolation_order)
        except EmptyRenderError:
            image = np.ndarray([0, 0, 3])

        return image

    def _render_keyboard(self, profile: TrackingProfile, colour_map: str, data_set: str, sampling: int = 1) -> np.ndarray:
        """Render a keyboard image."""
        keyboard.GLOBALS.data_set = data_set
        keyboard.GLOBALS.colour_map = colour_map
        keyboard.GLOBALS.multiplier = max(1, sampling)

        pressed = {i: profile.key_presses[i] for i in map(int, keycodes.KEYBOARD_CODES)}
        held = {i: profile.key_held[i] for i in map(int, keycodes.KEYBOARD_CODES)}

        image = keyboard.DrawKeyboard(profile.name, profile.active, pressed, held).draw_image()

        # Convert back to array to send to GUI
        return np.asarray(image)

    def _get_tick_diff(self, profile_name: str) -> int:
        """Get the difference between elapsed ticks and recorded ticks.

        This should always return a positive integer, but a check is
        required as it's quite finicky and easy to break with updates.
        """
        profile = self.all_profiles[profile_name]
        tick_diff = profile.elapsed - (profile.active + profile.inactive)
        if tick_diff < 0:
            raise RuntimeError(f'unexpected tick difference, should be a positive number, got {tick_diff} '
                               f'(elapsed: {profile.elapsed}, active: {profile.active}, inactive: {profile.inactive})')
        return tick_diff

    def _record_active_tick(self, profile_name: str, ticks: int) -> None:
        profile = self.all_profiles[profile_name]
        profile.active += ticks
        profile.daily_ticks[self.profile_age_days, 1] += ticks

        if DEBUG:
            self._get_tick_diff(profile_name)

    def _record_inactive_tick(self, profile_name: str, ticks: int) -> None:
        profile = self.all_profiles[profile_name]
        profile.inactive += ticks
        profile.daily_ticks[self.profile_age_days, 2] += ticks

        if DEBUG:
            self._get_tick_diff(profile_name)

    def _export_stats(self, message: ipc.ExportStats) -> None:
        """Export a stats CSV file."""
        export = Export(self.all_profiles[message.profile])

        match message:
            case ipc.ExportMouseStats():
                export.mouse_stats(message.path)

            case ipc.ExportKeyboardStats():
                export.keyboard_stats(message.path)

            case ipc.ExportGamepadStats():
                export.gamepad_stats(message.path)

            case ipc.ExportNetworkStats():
                export.network_stats(message.path)

            case ipc.ExportDailyStats():
                export.daily_stats(message.path)

            case _:
                raise NotImplementedError(message)

        self.send_data(ipc.ExportStatsSuccessful(message))

    def _save(self, profile_name: str) -> bool:
        """Save a profile to disk.
        See `ipc.SaveReady` for information on why the `inactivity`
        parameter is required.
        """
        print(f'[Processing] Saving {profile_name}...')
        profile = self.all_profiles[profile_name]
        if not profile.is_modified:
            print('[Processing] Skipping save, not modified')
            return False

        # To keep the active/inactive time in sync with elapsed,
        # temporarily add the current data to the profile
        # This is the same logic in the GUI
        inactivity_threshold = UPDATES_PER_SECOND * GlobalConfig.inactivity_time
        tick_diff = self._get_tick_diff(profile_name)
        if tick_diff > inactivity_threshold:
            self._record_inactive_tick(profile_name, tick_diff)
        elif tick_diff:
            self._record_active_tick(profile_name, tick_diff)

        result = profile.save()

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
                self.profile.is_modified = True

            case ipc.Active():
                self._record_active_tick(message.profile_name, message.ticks)

            case ipc.Inactive():
                self._record_inactive_tick(message.profile_name, message.ticks)

            case ipc.RenderRequest():
                print('[Processing] Render request received...')
                if message.profile:
                    profile = self.all_profiles[message.profile]
                else:
                    profile = self.profile

                if message.type == ipc.RenderType.Keyboard:
                    # Double the sampling, since the default render is too small
                    sampling = message.sampling
                    if message.file_path is not None:
                        sampling *= 2

                    assert message.show_count != message.show_time
                    if message.show_count:
                        data_set = 'count'
                    if message.show_time:
                        data_set = 'time'
                    image = self._render_keyboard(profile, message.colour_map, data_set, sampling)

                else:
                    image = self._render_array(profile, message.type, message.width, message.height,
                                               message.colour_map, sampling=message.sampling,
                                               padding=message.padding, contrast=message.contrast,
                                               lock_aspect=message.lock_aspect, clipping=message.clipping,
                                               blur=message.blur, linear=message.linear,
                                               left_clicks=message.show_left_clicks,
                                               middle_clicks=message.show_middle_clicks,
                                               right_clicks=message.show_right_clicks,
                                               interpolation_order=message.interpolation_order)
                self.send_data(ipc.Render(image, message))

                print('[Processing] Render request completed')

            case ipc.MouseMove():
                if not self.profile.config.track_mouse:
                    return

                distance = self._record_move(self.profile.cursor_map, message.position)
                self.profile.daily_distance[self.profile_age_days] += distance

            case ipc.MouseHeld():
                if not self.profile.config.track_mouse:
                    return

                result = self._monitor_offset(message.position)
                if result is not None:
                    current_monitor, pixel = result
                    index = (pixel[1], pixel[0])
                    self.profile.mouse_held_clicks[message.button][current_monitor][index] += 1

            case ipc.MouseClick():
                if not self.profile.config.track_mouse:
                    return

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
                    print(f'[Processing] {keycodes.KeyCode(message.button)} double clicked.')
                else:
                    arrays = self.profile.mouse_single_clicks[message.button]
                    print(f'[Processing] {keycodes.KeyCode(message.button)} clicked.')

                result = self._monitor_offset(message.position)
                if result is not None:
                    current_monitor, pixel = result
                    index = (pixel[1], pixel[0])
                    arrays[current_monitor][index] += 1

                self.previous_mouse_click = PreviousMouseClick(message, self.tick, double_click)

            case ipc.KeyPress():
                if not self.profile.config.should_track_keycode(message.keycode):
                    return

                if message.keycode not in keycodes.CLICK_CODES:
                    print(f'[Processing] {keycodes.KeyCode(message.keycode)} pressed.')
                self.profile.key_presses[message.keycode] += 1
                self.profile.key_held[message.keycode] += 1

                if message.keycode in keycodes.MOUSE_CODES:
                    self.profile.daily_clicks[self.profile_age_days] += 1
                else:
                    self.profile.daily_keys[self.profile_age_days] += 1

            case ipc.KeyHeld():
                if not self.profile.config.should_track_keycode(message.keycode):
                    return

                if message.keycode in keycodes.SCROLL_CODES:
                    print(f'[Processing] {keycodes.KeyCode(message.keycode)} triggered.')
                    self.profile.daily_scrolls[self.profile_age_days] += 1
                self.profile.key_held[message.keycode] += 1

            case ipc.ButtonPress():
                if not self.profile.config.track_gamepad:
                    return

                print(f'[Processing] {keycodes.GamepadCode(message.keycode)} pressed.')
                self.profile.button_presses[message.gamepad][int(math.log2(message.keycode))] += 1
                self.profile.button_held[message.gamepad][int(math.log2(message.keycode))] += 1
                self.profile.daily_buttons[self.profile_age_days] += 1

            case ipc.ButtonHeld():
                if not self.profile.config.track_gamepad:
                    return

                self.profile.button_held[message.gamepad][int(math.log2(message.keycode))] += 1

            case ipc.MonitorsChanged():
                print(f'[Processing] Monitors changed.')
                self.monitor_data = message.data

            case ipc.ThumbstickMove():
                if not self.profile.config.track_gamepad:
                    return

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

            case ipc.TrackingStarted():
                self.profile.cursor_map.position = get_cursor_pos()

            case ipc.StopTracking() | ipc.Exit():
                raise ExitRequest

            case ipc.CurrentProfileChanged():
                self.current_application = Application(message.name, message.rects)

            case ipc.Save():
                # Keep track of what saved and what didn't
                succeeded = []
                failed = []

                profile_names = []
                if message.profile_name is not None:
                    if message.profile_name in self.all_profiles:
                        profile_names.append(message.profile_name)
                else:
                    profile_names.extend(profile.name for profile in self.all_profiles.values())

                for profile_name in profile_names:
                    profile = self.all_profiles[profile_name]

                    # If not modified since last time, unload it from memory
                    if not profile.is_modified:
                        print(f'[Processing] Unloading profile: {profile_name}')
                        del self.all_profiles[profile_name]

                    # Attempt the save
                    elif self._save(profile_name):
                        succeeded.append(profile_name)

                    else:
                        failed.append(profile_name)
                self.send_data(ipc.SaveComplete(succeeded, failed))

            case ipc.DataTransfer():
                if not self.profile.config.track_network:
                    return

                self.profile.data_upload[message.mac_address] += message.bytes_sent
                self.profile.data_download[message.mac_address] += message.bytes_recv
                self.profile.daily_upload[self.profile_age_days] += message.bytes_sent
                self.profile.daily_download[self.profile_age_days] += message.bytes_recv

                if message.mac_address not in self.profile.data_interfaces:
                    self.profile.data_interfaces[message.mac_address] = Interfaces.get_from_mac(message.mac_address).name

            case ipc.ProfileDataRequest(profile_name=name):
                if name is None:
                    name = DEFAULT_PROFILE_NAME
                self._send_profile_data(name)

            case ipc.SetProfileMouseTracking():
                print(f'[Processing] Setting mouse tracking state on {message.profile_name}: {message.enable}')
                profile = self.all_profiles[message.profile_name]
                profile.is_modified = True
                profile.config.track_mouse = message.enable

            case ipc.SetProfileKeyboardTracking():
                print(f'[Processing] Setting keyboard tracking state on {message.profile_name}: {message.enable}')
                profile = self.all_profiles[message.profile_name]
                profile.is_modified = True
                profile.config.track_keyboard = message.enable

            case ipc.SetProfileGamepadTracking():
                print(f'[Processing] Setting gamepad tracking state on {message.profile_name}: {message.enable}')
                profile = self.all_profiles[message.profile_name]
                profile.is_modified = True
                profile.config.track_gamepad = message.enable

            case ipc.SetProfileNetworkTracking():
                print(f'[Processing] Setting network tracking state on {message.profile_name}: {message.enable}')
                profile = self.all_profiles[message.profile_name]
                profile.is_modified = True
                profile.config.track_network = message.enable

            case ipc.DeleteMouseData():
                print(f'[Processing] Deleting all mouse data for {message.profile_name}...')
                profile = self.all_profiles[message.profile_name]
                profile.is_modified = True
                profile.cursor_map = type(profile.cursor_map)()
                profile.mouse_single_clicks.clear()
                profile.mouse_double_clicks.clear()
                profile.mouse_held_clicks.clear()
                profile.daily_distance = profile.daily_distance.as_zero()
                profile.daily_clicks = profile.daily_clicks.as_zero()
                profile.daily_scrolls = profile.daily_scrolls.as_zero()
                for code in keycodes.MOUSE_CODES + keycodes.SCROLL_CODES:
                    profile.key_presses[code] = 0
                    profile.key_held[code] = 0

            case ipc.DeleteKeyboardData():
                print(f'[Processing] Deleting all keyboard data for {message.profile_name}...')
                profile = self.all_profiles[message.profile_name]
                profile.is_modified = True
                profile.daily_keys = profile.daily_keys.as_zero()
                for code in keycodes.KEYBOARD_CODES:
                    profile.key_presses[code] = 0
                    profile.key_held[code] = 0

            case ipc.DeleteGamepadData():
                print(f'[Processing] Deleting all gamepad data for {message.profile_name}...')
                profile = self.all_profiles[message.profile_name]
                profile.is_modified = True
                profile.thumbstick_l_map.clear()
                profile.thumbstick_r_map.clear()
                profile.button_presses.clear()
                profile.button_held.clear()
                profile.daily_buttons = profile.daily_buttons.as_zero()

            case ipc.DeleteNetworkData():
                print(f'[Processing] Deleting all network data for {message.profile_name}...')
                profile = self.all_profiles[message.profile_name]
                profile.is_modified = True
                profile.data_interfaces.clear()
                profile.data_upload.clear()
                profile.data_download.clear()
                profile.daily_upload = profile.daily_upload.as_zero()
                profile.daily_download = profile.daily_download.as_zero()

            case ipc.DeleteProfile():
                print(f'[Processing] Deleting profile {message.profile_name}...')
                del self.all_profiles[message.profile_name]
                with suppress(FileNotFoundError):
                    os.remove(get_filename(message.profile_name))

            case ipc.ImportProfile():
                profile = self.all_profiles[message.name] = TrackingProfile.load(message.path)
                profile.is_modified = True

            case ipc.ImportLegacyProfile():
                profile = self.all_profiles[message.name] = TrackingProfile(message.name)
                profile.import_legacy(message.path)
                profile.is_modified = True

            case ipc.ExportStats():
                self._export_stats(message)

            case ipc.ToggleProfileResolution():
                profile = self.all_profiles[message.profile]
                profile.is_modified = True
                lst = profile.config.disabled_resolutions
                if message.enable:
                    del lst[lst.index(message.resolution)]
                else:
                    lst.append(message.resolution)

            case ipc.ToggleProfileMultiMonitor():
                profile = self.all_profiles[message.profile]
                profile.is_modified = True
                profile.config.multi_monitor = message.multi_monitor

            case _:
                raise NotImplementedError(message)

    def run(self) -> None:
        """Listen for events to process."""
        for message in self.receive_data(polling_rate=1 / UPDATES_PER_SECOND):
            self._process_message(message)
