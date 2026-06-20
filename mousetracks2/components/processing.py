import math
import time
from collections import defaultdict
from contextlib import suppress
from dataclasses import dataclass
from typing import Iterator, Literal

import numpy as np
import numpy.typing as npt
from send2trash import send2trash

from . import ipc
from .abstract import AppComponent, MonitorComponent
from ..config import GlobalConfig
from ..context import CTX
from ..exceptions import ExitRequest
from ..export import Export
from ..file import ArrayResolutionMap, MovementMaps, TrackingProfile, TrackingProfileLoader, get_filename
from ..legacy import keyboard
from ..types import Application
from ..utils import keycodes
from ..utils.math import calculate_distance
from ..utils.input import get_cursor_pos
from ..utils.interface import Interfaces
from ..utils.system import hide_child_process
from ..constants import UPDATES_PER_SECOND, DOUBLE_CLICK_MS, DOUBLE_CLICK_TOL, RADIAL_ARRAY_SIZE, DEBUG
from ..render import render, EmptyRenderError, LayerBlend


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


class Processing(AppComponent, MonitorComponent):
    """Process raw input events into tracking data and handle render requests.

    Maintains tracking profiles for each application, updating movement,
    click, keyboard, gamepad, and network data as events arrive.
    """

    target = ipc.Target.Processing

    def __post_init__(self) -> None:
        hide_child_process()

        self.tick = 0
        self._timestamp = -1
        self.is_playback = CTX.playback_file is not None

        self.previous_mouse_click: PreviousMouseClick | None = None
        self.previous_monitor = None

        # Load in the default profile
        self.all_profiles = TrackingProfileLoader()

        self.config = GlobalConfig()

        # Reset the cursor position on focused application change
        def on_application_change(app: Application) -> None:
            self.profile.cursor_map.position = None
        self.register_app_change_hook(on_application_change)

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
        return self.all_profiles[self.focused_app.name]

    def _send_profile_data(self, profile: TrackingProfile) -> None:
        """Send all the stats for the profile."""
        profile.last_accessed = time.time()

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


    def is_single_monitor_mode(self) -> bool:
        """Determine if running in single or multi monitor mode."""
        if self.profile.config.multi_monitor is None:
            return bool(CTX.single_monitor)
        return not self.profile.config.multi_monitor

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
        # Convert pixels from logical coordinates to physical
        old_position = data.position
        new_position = position

        # If the ticks match then overwrite the old data
        if self.tick == data.tick:
            data.position = position

        distance = calculate_distance(old_position, new_position)
        data.distance += distance
        moving = self.tick == data.tick + 1

        # Add the pixels to an array
        for current_monitor, pixel in self.iter_pixel_line(old_position, new_position, force_monitor):
            index = (pixel[1], pixel[0])
            data.sequential_arrays[current_monitor][index] = data.counter
            data.density_arrays[current_monitor][index] += 1
            if distance and moving:
                data.speed_arrays[current_monitor][index] = max(data.speed_arrays[current_monitor][index], round(100 * distance))

        # Update the saved data
        data.position = position
        data.counter += 1
        data.ticks += 1
        data.tick = self.tick

        if data.requires_decay():
            print('[Processing] Tracking threshold reached, reducing values...')
            data.run_decay()
            print('[Processing] Reduced all arrays')

        return distance

    def _handle_mouse_move(self, profile: TrackingProfile, message: ipc.MouseMove) -> None:
        """Record a mouse movement event into the given profile."""
        if not profile.config.track_mouse or self.app_resizing:
            return

        distance = self._record_move(profile.cursor_map, message.position)
        profile.daily_distance[profile.age_days(self.timestamp)] += distance

    def _handle_mouse_held(self, profile: TrackingProfile, message: ipc.MouseHeld) -> None:
        """Record a held mouse button event into the given profile."""
        if not profile.config.track_mouse or self.app_resizing:
            return

        result = self.get_render_space_offset(message.position)
        if result is None:
            return

        current_monitor, pixel = result
        index = (pixel[1], pixel[0])
        profile.mouse_held_clicks[message.button][current_monitor][index] += 1

    def _handle_key_press(self, profile: TrackingProfile, message: ipc.KeyPress) -> None:
        """Record a key press event into the given profile."""
        if not profile.config.should_track_keycode(message.keycode):
            return
        if message.keycode not in keycodes.CLICK_CODES:
            print(f'[Processing] {keycodes.KeyCode(message.keycode)} pressed.')
        profile.key_presses[message.keycode] += 1
        profile.key_held[message.keycode] += 1
        if message.keycode in keycodes.MOUSE_CODES:
            profile.daily_clicks[profile.age_days(self.timestamp)] += 1
        else:
            profile.daily_keys[profile.age_days(self.timestamp)] += 1

    def _handle_key_held(self, profile: TrackingProfile, message: ipc.KeyHeld) -> None:
        """Record a key held event into the given profile."""
        if not profile.config.should_track_keycode(message.keycode):
            return
        if message.keycode in keycodes.SCROLL_CODES:
            print(f'[Processing] {keycodes.KeyCode(message.keycode)} triggered.')
            profile.daily_scrolls[profile.age_days(self.timestamp)] += 1
        profile.key_held[message.keycode] += 1

    def _handle_mouse_click(self, profile: TrackingProfile, message: ipc.MouseClick) -> None:
        """Record a mouse click event into the given profile."""
        if not profile.config.track_mouse:
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
            arrays = profile.mouse_double_clicks[message.button]
            print(f'[Processing] {keycodes.KeyCode(message.button)} double clicked.')
        else:
            arrays = profile.mouse_single_clicks[message.button]
            print(f'[Processing] {keycodes.KeyCode(message.button)} clicked.')
        result = self.get_render_space_offset(message.position)
        if result is not None:
            current_monitor, pixel = result
            index = (pixel[1], pixel[0])
            arrays[current_monitor][index] += 1
        self.previous_mouse_click = PreviousMouseClick(message, self.tick, double_click)

    def _handle_button_press(self, profile: TrackingProfile, message: ipc.ButtonPress) -> None:
        """Record a gamepad button press event into the given profile."""
        if not profile.config.track_gamepad:
            return
        print(f'[Processing] {keycodes.GamepadCode(message.keycode)} pressed.')
        profile.button_presses[message.gamepad][int(math.log2(message.keycode))] += 1
        profile.button_held[message.gamepad][int(math.log2(message.keycode))] += 1
        profile.daily_buttons[profile.age_days(self.timestamp)] += 1

    def _handle_button_held(self, profile: TrackingProfile, message: ipc.ButtonHeld) -> None:
        """Record a gamepad button held event into the given profile."""
        if not profile.config.track_gamepad:
            return
        profile.button_held[message.gamepad][int(math.log2(message.keycode))] += 1

    def _handle_thumbstick_move(self, profile: TrackingProfile, message: ipc.ThumbstickMove) -> None:
        """Record a thumbstick movement event into the given profile."""
        if not profile.config.track_gamepad:
            return
        width = height = RADIAL_ARRAY_SIZE
        x = round((message.position[0] + 1) * (width - 1) / 2)
        y = round((message.position[1] + 1) * (height - 1) / 2)
        remapped = (x, height - y - 1)
        match message.thumbstick:
            case ipc.ThumbstickMove.Thumbstick.Left:
                self._record_move(profile.thumbstick_l_map[message.gamepad], remapped, (width, height))
            case ipc.ThumbstickMove.Thumbstick.Right:
                self._record_move(profile.thumbstick_r_map[message.gamepad], remapped, (width, height))
            case _:
                raise NotImplementedError(message.thumbstick)

    def _handle_data_transfer(self, profile: TrackingProfile, message: ipc.DataTransfer) -> None:
        """Record a network data transfer event into the given profile."""
        if not profile.config.track_network:
            return
        profile.data_upload[message.mac_address] += message.bytes_sent
        profile.data_download[message.mac_address] += message.bytes_recv
        profile.daily_upload[profile.age_days(self.timestamp)] += message.bytes_sent
        profile.daily_download[profile.age_days(self.timestamp)] += message.bytes_recv
        if message.mac_address not in profile.data_interfaces:
            profile.data_interfaces[message.mac_address] = Interfaces.get_from_mac(message.mac_address).name

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
            case ipc.RenderType.MouseMovement:
                arrays[0, 0].extend(get_arrays(profile.cursor_map.sequential_arrays))

            case ipc.RenderType.MousePosition:
                arrays[0, 0].extend(get_arrays(profile.cursor_map.density_arrays))

            case ipc.RenderType.MouseSpeed:
                arrays[0, 0].extend(get_arrays(profile.cursor_map.speed_arrays))

            case ipc.RenderType.SingleClick:
                for keycode, res_map in profile.mouse_single_clicks.items():
                    if keycode == keycodes.VK_LBUTTON and not left_clicks:
                        continue
                    if keycode == keycodes.VK_MBUTTON and not middle_clicks:
                        continue
                    if keycode == keycodes.VK_RBUTTON and not right_clicks:
                        continue
                    arrays[0, 0].extend(get_arrays(res_map))

            case ipc.RenderType.DoubleClick:
                for keycode, res_map in profile.mouse_double_clicks.items():
                    if keycode == keycodes.VK_LBUTTON and not left_clicks:
                        continue
                    if keycode == keycodes.VK_MBUTTON and not middle_clicks:
                        continue
                    if keycode == keycodes.VK_RBUTTON and not right_clicks:
                        continue
                    arrays[0, 0].extend(get_arrays(res_map))

            case ipc.RenderType.HeldClick:
                for keycode, res_map in profile.mouse_held_clicks.items():
                    if keycode == keycodes.VK_LBUTTON and not left_clicks:
                        continue
                    if keycode == keycodes.VK_MBUTTON and not middle_clicks:
                        continue
                    if keycode == keycodes.VK_RBUTTON and not right_clicks:
                        continue
                    arrays[0, 0].extend(get_arrays(res_map))

            case ipc.RenderType.ThumbstickMovement:
                if left_clicks:
                    for gamepad_maps in profile.thumbstick_l_map.values():
                        resolution_map = gamepad_maps.sequential_arrays
                        arrays[0, 0].extend(resolution_map.values())
                if right_clicks:
                    for gamepad_maps in profile.thumbstick_r_map.values():
                        resolution_map = gamepad_maps.sequential_arrays
                        arrays[int(left_clicks), 0].extend(resolution_map.values())

            case ipc.RenderType.ThumbstickSpeed:
                if left_clicks:
                    for gamepad_maps in profile.thumbstick_l_map.values():
                        resolution_map = gamepad_maps.speed_arrays
                        arrays[0, 0].extend(resolution_map.values())
                if right_clicks:
                    for gamepad_maps in profile.thumbstick_r_map.values():
                        resolution_map = gamepad_maps.speed_arrays
                        arrays[int(left_clicks), 0].extend(resolution_map.values())

            case ipc.RenderType.ThumbstickPosition:
                if left_clicks:
                    for gamepad_maps in profile.thumbstick_l_map.values():
                        resolution_map = gamepad_maps.density_arrays
                        arrays[0, 0].extend(resolution_map.values())
                if right_clicks:
                    for gamepad_maps in profile.thumbstick_r_map.values():
                        resolution_map = gamepad_maps.density_arrays
                        arrays[int(left_clicks), 0].extend(resolution_map.values())

            case _:
                raise NotImplementedError(render_type)

        return arrays

    def _render_array(self, profile: TrackingProfile, render_type: ipc.RenderType,
                      width: int | None, height: int | None, colour_map: str, sampling: int = 1,
                      padding: int = 0, contrast: float = 1.0, lock_aspect: bool = True,
                      clipping: float = 0.0, blur: float = 0.0, linear: bool = False, invert: bool = False,
                      left_clicks: bool = True, middle_clicks: bool = True, right_clicks: bool = True,
                      interpolation_order: Literal[0, 1, 2, 3, 4, 5] = 0) -> npt.NDArray[np.uint8]:
        """Render an array (tracks / heatmaps)."""
        # Get the arrays to render
        positional_arrays = self._arrays_for_rendering(profile, render_type, left_clicks=left_clicks,
                                                       middle_clicks=middle_clicks, right_clicks=right_clicks)

        # Add extra padding
        if padding:
            for position, arrays in positional_arrays.items():
                positional_arrays[position] = [np.pad(array, padding) for array in arrays]

        # Adjust width/height if not locking the aspect ratio
        if positional_arrays and not lock_aspect and width is not None and height is not None:
            width_items = max(x for x, y in positional_arrays) - min(x for x, y in positional_arrays) + 1
            height_items = max(y for x, y in positional_arrays) - min(y for x, y in positional_arrays) + 1
            width = round(width / width_items)
            height = round(height / height_items)

        # Do the render
        try:
            image = render(colour_map, positional_arrays, width, height, sampling,
                           lock_aspect=lock_aspect, linear=linear, invert=invert,
                           blur=blur, contrast=contrast, clipping=clipping,
                           interpolation_order=interpolation_order)
        except EmptyRenderError:
            image = np.ndarray([0, 0, 4], dtype=np.uint8)

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
        profile.daily_ticks[profile.age_days(self.timestamp), 1] += ticks

        if DEBUG:
            self._get_tick_diff(profile_name)

    def _record_inactive_tick(self, profile_name: str, ticks: int) -> None:
        profile = self.all_profiles[profile_name]
        profile.inactive += ticks
        profile.daily_ticks[profile.age_days(self.timestamp), 2] += ticks

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
        Temporarily adjusts active/inactive ticks to keep them in sync with
        elapsed before saving, then reverts the adjustment afterwards.
        """
        print(f'[Processing] Saving {profile_name}...')
        profile = self.all_profiles[profile_name]
        if not profile.is_modified:
            print('[Processing] Skipping save, not modified')
            return False

        # To keep the active/inactive time in sync with elapsed,
        # temporarily add the current data to the profile
        # This is the same logic in the GUI
        inactivity_threshold = UPDATES_PER_SECOND * self.config.inactivity_time
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

    def save(self, profile_name: str | None = None) -> tuple[list[str], list[str]]:
        """Save all loaded profiles to disk, unloading unmodified ones.
        If `profile_name` is given, only that profile is processed.
        """
        succeeded: list[str] = []
        failed: list[str] = []

        profile_names = []
        if profile_name is not None:
            if profile_name in self.all_profiles:
                profile_names.append(profile_name)
        else:
            profile_names.extend(profile.name for profile in self.all_profiles.values())

        for name in profile_names:
            profile = self.all_profiles[name]
            if not profile.is_modified:
                print(f'[Processing] Unloading profile: {name}')
                del self.all_profiles[name]
            elif self._save(name):
                succeeded.append(name)
            else:
                failed.append(name)

        return succeeded, failed

    def _process_message(self, message: ipc.Message) -> None:
        """Process an item of data."""
        match message:
            case ipc.Tick():
                # Set variables
                self.tick = message.tick
                self.timestamp = message.timestamp

                # Update profile data
                self.profile.elapsed += 1
                self.profile.daily_ticks[self.profile.age_days(self.timestamp), 0] += 1

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

                if message.type == ipc.RenderType.KeyboardHeatmap:
                    # Double the sampling, since the default render is too small
                    sampling = message.sampling
                    if message.file_path is not None:
                        sampling *= 2

                    data_set = 'time' if message.show_keyboard_time else 'count'
                    image = self._render_keyboard(profile, message.colour_map, data_set, sampling)

                else:
                    image = self._render_array(profile, message.type, message.width, message.height,
                                               message.colour_map, sampling=message.sampling,
                                               padding=message.padding, contrast=message.contrast,
                                               lock_aspect=message.lock_aspect, clipping=message.clipping,
                                               blur=message.blur, linear=message.linear, invert=message.invert,
                                               left_clicks=message.show_left_clicks,
                                               middle_clicks=message.show_middle_clicks,
                                               right_clicks=message.show_right_clicks,
                                               interpolation_order=message.interpolation_order)
                self.send_data(ipc.Render(image, message))

                print('[Processing] Render request completed')

            case ipc.RenderLayerRequest():
                print('[Processing] Render request received...')
                if not message.layers:
                    return

                if message.layers[0].request.profile:
                    profile = self.all_profiles[message.layers[0].request.profile]
                else:
                    profile = self.profile

                # Intercept if a keyboard render
                for layer in message.layers:
                    if layer.request.type == ipc.RenderType.KeyboardHeatmap:
                        self.send_data(layer.request)
                        return

                layer_blend = None

                for i, layer in enumerate(message.layers):
                    request = layer.request

                    # Use the resolution of the first layer
                    if layer_blend is None:
                        width = request.width
                        height = request.height
                        lock_aspect = request.lock_aspect
                    # Reuse the same resolution
                    else:
                        height, width = layer_blend.image.shape[:2]
                        width //= max(1, request.sampling)
                        height //= max(1, request.sampling)
                        lock_aspect = False

                    # Render the layer
                    if request.layer_visible:
                        _image = self._render_array(
                            profile=profile,
                            render_type=request.type,
                            colour_map=request.colour_map,
                            width=width,
                            height=height,
                            lock_aspect=lock_aspect,
                            sampling=request.sampling,
                            padding=request.padding,
                            contrast=request.contrast,
                            clipping=request.clipping,
                            blur=request.blur,
                            linear=request.linear,
                            invert=request.invert,
                            left_clicks=request.show_left_clicks,
                            middle_clicks=request.show_middle_clicks,
                            right_clicks=request.show_right_clicks,
                            interpolation_order=request.interpolation_order,
                        )

                    # If not visible, skip here unless there aren't any other visible layers
                    elif i or any(_layer.request.layer_visible for _layer in message.layers):
                        continue

                    # If a single invisible layer, then do a quick render to get the resolution
                    else:
                        _image = self._render_array(
                            profile=profile,
                            render_type=request.type,
                            colour_map='BlackToWhite',
                            width=width,
                            height=height,
                            lock_aspect=lock_aspect,
                            blur=0,
                            left_clicks=False,
                            middle_clicks=False,
                            right_clicks=False,
                        )
                    image = np.divide(_image.astype(np.float64), 255)

                    # Setup the base layer
                    if layer_blend is None:
                        layer_blend = LayerBlend(np.zeros(image.shape, dtype=np.float64))

                    # Add the new layer
                    if request.layer_visible:
                        # Ensure initial layer has alpha
                        if not i:
                            layer.channels |= ipc.Channel.A
                        layer_blend.blend(layer.blend_mode, image, opacity=layer.opacity / 100.0, channels=layer.channels)

                if layer_blend is None:
                    return

                # Add checkerboards to preview render backgrounds
                if message.layers[0].request.file_path is None:
                    layer_blend.add_checkerbox()

                self.send_data(ipc.Render(layer_blend.to_uint8(), request))
                print('[Processing] Render request completed')

            case ipc.MouseMove():
                self._handle_mouse_move(self.profile, message)

            case ipc.MouseHeld():
                self._handle_mouse_held(self.profile, message)

            case ipc.MouseClick():
                self._handle_mouse_click(self.profile, message)

            case ipc.KeyPress():
                self._handle_key_press(self.profile, message)

            case ipc.KeyHeld():
                self._handle_key_held(self.profile, message)

            case ipc.ButtonPress():
                self._handle_button_press(self.profile, message)

            case ipc.ButtonHeld():
                self._handle_button_held(self.profile, message)

            case ipc.MonitorsChanged():
                print('[Processing] Monitors changed.')
                self.set_monitor_data(message.data)

            case ipc.ThumbstickMove():
                self._handle_thumbstick_move(self.profile, message)

            case ipc.DebugRaiseError():
                raise RuntimeError('test exception')

            case ipc.StartPlayback():
                self.is_playback = True

            case ipc.StopPlayback():
                self.is_playback = False

            case ipc.TrackingStarted():
                self.profile.cursor_map.position = None if self.is_playback else get_cursor_pos()

            case ipc.StartRecording():
                # Send a snapshot of the current state so the recording
                self.send_data(ipc.MonitorsChanged(data=self._monitor_data))
                self.send_data(ipc.CurrentProfileChanged(
                    name=self.focused_app.name,
                    process_id=None,
                    rects=self.focused_app.rects,
                ))
                if self.profile.cursor_map.position is not None:
                    self.send_data(ipc.MouseMove(position=self.profile.cursor_map.position))
                for gamepad, maps in self.profile.thumbstick_l_map.items():
                    if maps.position is not None:
                        self.send_data(ipc.ThumbstickMove(
                            gamepad=gamepad,
                            thumbstick=ipc.ThumbstickMove.Thumbstick.Left,
                            position=maps.position,
                        ))
                for gamepad, maps in self.profile.thumbstick_r_map.items():
                    if maps.position is not None:
                        self.send_data(ipc.ThumbstickMove(
                            gamepad=gamepad,
                            thumbstick=ipc.ThumbstickMove.Thumbstick.Right,
                            position=maps.position,
                        ))

            case ipc.StopTracking() | ipc.Exit():
                raise ExitRequest

            case ipc.CurrentProfileChanged():
                self.focused_app = Application(message.name, message.rects)

            case ipc.Save():
                succeeded, failed = self.save(message.profile_name)
                self.send_data(ipc.SaveComplete(succeeded, failed))

            case ipc.DataTransfer():
                self._handle_data_transfer(self.profile, message)

            case ipc.ProfileDataRequest():
                profile = self.all_profiles[message.sanitised_name]
                profile.name = message.profile_name  # Ensure the name gets updated
                self._send_profile_data(profile)

            case ipc.SetProfileTracking():
                self._set_profile_tracking_state(message.profile_name, message.device, message.enable)

            case ipc.DeleteData():
                self._delete_profile_data(message.profile_name, message.devices)

            case ipc.DeleteProfile():
                self._delete_profile(message.profile_name)

            case ipc.ImportProfile():
                profile = self.all_profiles[message.name] = TrackingProfile.load(message.path)
                profile.name = message.name
                profile.is_modified = True

            case ipc.ImportLegacyProfile():
                profile = TrackingProfile(message.name)
                if profile.import_legacy(message.path):
                    profile.is_modified = True
                    self.all_profiles[message.name] = profile
                else:
                    self.send_data(ipc.FailedProfileImport(message))

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

    def _set_profile_tracking_state(self, profile_name: str, devices: ipc.Device, enable: bool) -> None:
        """Enable or disable tracking for one or more devices."""
        profile = self.all_profiles[profile_name]
        profile.is_modified = True
        for device in ipc.Device:
            if device.name is not None and devices & device:
                print(f'[Processing] Setting {device.name.lower()} tracking state on {profile_name}: {enable}')
                setattr(profile.config, f'track_{device.name.lower()}', enable)

    def _delete_profile(self, profile_name: str) -> None:
        """Delete a profile entirely."""
        print(f'[Processing] Deleting profile {profile_name}...')
        del self.all_profiles[profile_name]
        with suppress(FileNotFoundError):
            send2trash(get_filename(profile_name))

    def _delete_profile_data(self, profile_name: str, devices: ipc.Device) -> None:
        """Delete tracking data for one or more devices."""
        device_names = ', '.join(device.name.lower() for device in ipc.Device
                                 if device.name is not None and devices & device)
        print(f'[Processing] Deleting {device_names} data for {profile_name}...')

        profile = self.all_profiles[profile_name]
        profile.is_modified = True

        if devices & ipc.Device.Mouse:
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

        if devices & ipc.Device.Keyboard:
            profile.daily_keys = profile.daily_keys.as_zero()
            for code in keycodes.KEYBOARD_CODES:
                profile.key_presses[code] = 0
                profile.key_held[code] = 0

        if devices & ipc.Device.Gamepad:
            profile.thumbstick_l_map.clear()
            profile.thumbstick_r_map.clear()
            profile.button_presses.clear()
            profile.button_held.clear()
            profile.daily_buttons = profile.daily_buttons.as_zero()

        if devices & ipc.Device.Network:
            profile.data_interfaces.clear()
            profile.data_upload.clear()
            profile.data_download.clear()
            profile.daily_upload = profile.daily_upload.as_zero()
            profile.daily_download = profile.daily_download.as_zero()

    def run(self) -> None:
        """Listen for events to process."""
        for message in self.receive_data(polling_rate=1 / UPDATES_PER_SECOND):
            self._process_message(message)
