import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from .. import ipc
from ..abstract import Component
from ...exceptions import ExitRequest
from ...file import MovementMaps, TrackingProfile, TrackingProfileLoader, get_filename
from ...legacy import keyboard
from ...utils import keycodes, get_cursor_pos
from ...utils.math import calculate_line, calculate_distance, calculate_pixel_offset
from ...utils.network import Interfaces
from ...utils.system import monitor_locations
from ...constants import DEFAULT_PROFILE_NAME, UPDATES_PER_SECOND, DOUBLE_CLICK_MS, DOUBLE_CLICK_TOL, RADIAL_ARRAY_SIZE, INACTIVITY_MS
from ...render import render, EmptyRenderError


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
    rect: tuple[int, int, int, int] | None


class Processing(Component):
    def __post_init__(self) -> None:
        self.tick = 0
        self._timestamp = None

        self.previous_mouse_click: PreviousMouseClick | None = None
        self.monitor_data = monitor_locations()
        self.previous_monitor = None

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
    def current_application(self, application: Application) -> None:
        """Update the currently loaded application."""
        if application == self._current_application:
            return
        self._current_application = application

        # Reset the cursor position
        self.profile.cursor_map.position = None

    def _send_profile_data(self, name: str) -> None:
        """Send all the stats for the profile."""
        profile = self.all_profiles[name]

        # Count total clicks
        clicks = 0
        for resolution_maps in profile.mouse_single_clicks.values():
            for array in resolution_maps.values():
                clicks += np.sum(array)

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
            buttons_pressed=sum(np.sum(array) for array in profile.button_presses.values()),
            elapsed_ticks=profile.elapsed,
            active_ticks=profile.active,
            inactive_ticks=profile.inactive,
            bytes_sent=sum(profile.data_upload.values()),
            bytes_recv=sum(profile.data_download.values()),
            config=profile.config,
        ))

    @property
    def profile_age_days(self) -> int:
        """Get the number of days since the profile was created.
        This is for use with the daily stats.
        """
        creation_day = self.profile.created // 86400
        current_day = self.timestamp // 86400
        return current_day - creation_day

    def _monitor_offset(self, pixel: tuple[int, int]) -> tuple[tuple[int, int], tuple[int, int]] | None:
        """Detect which monitor the pixel is on."""
        monitor_data = self.monitor_data
        if self.current_application is not None:
            rect = self.current_application.rect
            if rect is not None:
                monitor_data = [rect]

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

    def _arrays_for_rendering(self, profile: TrackingProfile, render_type: ipc.RenderType
                              ) -> dict[tuple[int, int], list[np.typing.ArrayLike]]:
        """Get a list of arrays to use for a render."""
        arrays: dict[tuple[int, int], list[np.typing.ArrayLike]] = defaultdict(list)
        match render_type:
            case ipc.RenderType.Time:
                arrays[0, 0].extend(profile.cursor_map.sequential_arrays.values())

            case ipc.RenderType.TimeHeatmap:
                arrays[0, 0].extend(profile.cursor_map.density_arrays.values())

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

            case ipc.RenderType.Thumbstick_Time:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.sequential_arrays
                    arrays[0, 0].extend(map.values())
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.sequential_arrays
                    arrays[1, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_Speed:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.speed_arrays
                    arrays[0, 0].extend(map.values())
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.speed_arrays
                    arrays[1, 0].extend(map.values())

            case ipc.RenderType.Thumbstick_Heatmap:
                for gamepad_maps in profile.thumbstick_l_map.values():
                    map = gamepad_maps.density_arrays
                    arrays[0, 0].extend(map.values())
                for gamepad_maps in profile.thumbstick_r_map.values():
                    map = gamepad_maps.density_arrays
                    arrays[1, 0].extend(map.values())

            case _:
                raise NotImplementedError(render_type)

        return arrays

    def _render_array(self, profile: TrackingProfile, render_type: ipc.RenderType,
                      width: int | None, height: int | None,
                      colour_map: str, sampling: int = 1) -> np.ndarray:
        """Render an array (tracks / heatmaps)."""
        is_heatmap = render_type in (ipc.RenderType.SingleClick, ipc.RenderType.DoubleClick, ipc.RenderType.HeldClick,
                                     ipc.RenderType.TimeHeatmap, ipc.RenderType.Thumbstick_Heatmap)
        is_speed = render_type in (ipc.RenderType.Speed, ipc.RenderType.Thumbstick_Speed)
        positional_arrays = self._arrays_for_rendering(profile, render_type)
        try:
            image = render(colour_map, positional_arrays, width, height, sampling, linear=is_heatmap or is_speed, blur=is_heatmap)
        except EmptyRenderError:
            image = np.ndarray([0, 0, 3])
        return image

    def _render_keyboard(self, profile: TrackingProfile, colour_map: str, sampling: int = 1) -> np.ndarray:
        """Render a keyboard image."""
        keyboard.GLOBALS.colour_map = colour_map
        keyboard.GLOBALS.multiplier = sampling

        pressed = {i: profile.key_presses[i] for i in map(int, keycodes.KEYBOARD_CODES)}
        held = {i: profile.key_held[i] for i in map(int, keycodes.KEYBOARD_CODES)}
        image = keyboard.DrawKeyboard(profile.name, profile.active, pressed, held).draw_image()

        # Convert back to array to send to GUI
        return np.asarray(image)

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
                if message.profile:
                    profile = self.all_profiles[message.profile]
                else:
                    profile = self.profile

                if message.type == ipc.RenderType.Keyboard:
                    # Double the sampling, since the default render is too small
                    sampling = message.sampling
                    if message.file_path is not None:
                        sampling *= 2
                    image = self._render_keyboard(profile, message.colour_map, sampling)

                else:
                    image = self._render_array(profile, message.type, message.width, message.height, message.colour_map, message.sampling)
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

                print(f'[Processing] {keycodes.KeyCode(message.keycode)} pressed.')
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

            case ipc.TrackingState():
                match message.state:
                    case ipc.TrackingState.State.Start:
                        self.profile.cursor_map.position = get_cursor_pos()
                    case ipc.TrackingState.State.Stop:
                        raise ExitRequest

            # Store the data for the newly detected application
            case ipc.TrackedApplicationDetected():
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
                profile.modified = True
                profile.config.track_mouse = message.enable

            case ipc.SetProfileKeyboardTracking():
                print(f'[Processing] Setting keyboard tracking state on {message.profile_name}: {message.enable}')
                profile = self.all_profiles[message.profile_name]
                profile.modified = True
                profile.config.track_keyboard = message.enable

            case ipc.SetProfileGamepadTracking():
                print(f'[Processing] Setting gamepad tracking state on {message.profile_name}: {message.enable}')
                profile = self.all_profiles[message.profile_name]
                profile.modified = True
                profile.config.track_gamepad = message.enable

            case ipc.SetProfileNetworkTracking():
                print(f'[Processing] Setting network tracking state on {message.profile_name}: {message.enable}')
                profile = self.all_profiles[message.profile_name]
                profile.modified = True
                profile.config.track_network = message.enable

            case ipc.DeleteMouseData():
                print(f'[Processing] Deleting all mouse data for {message.profile_name}...')
                profile = self.all_profiles[message.profile_name]
                profile.modified = True
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
                profile.modified = True
                profile.daily_keys = profile.daily_keys.as_zero()
                for code in keycodes.KEYBOARD_CODES:
                    profile.key_presses[code] = 0
                    profile.key_held[code] = 0

            case ipc.DeleteGamepadData():
                print(f'[Processing] Deleting all gamepad data for {message.profile_name}...')
                profile = self.all_profiles[message.profile_name]
                profile.modified = True
                profile.thumbstick_l_map.clear()
                profile.thumbstick_r_map.clear()
                profile.button_presses.clear()
                profile.button_held.clear()
                profile.daily_buttons = profile.daily_buttons.as_zero()

            case ipc.DeleteNetworkData():
                print(f'[Processing] Deleting all network data for {message.profile_name}...')
                profile = self.all_profiles[message.profile_name]
                profile.modified = True
                profile.data_interfaces.clear()
                profile.data_upload.clear()
                profile.data_download.clear()
                profile.daily_upload = profile.daily_upload.as_zero()
                profile.daily_download = profile.daily_download.as_zero()

            case ipc.LoadLegacyProfile():
                self.all_profiles[message.name] = TrackingProfile(message.name)
                self.all_profiles[message.name].import_legacy(message.path)

            case _:
                raise NotImplementedError(message)

    def run(self):
        """Listen for events to process."""
        while True:
            self._process_message(self.receive_data())
