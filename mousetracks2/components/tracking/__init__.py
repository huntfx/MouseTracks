import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterator

import psutil
import pynput
import XInput  # type: ignore

from . import utils
from .. import ipc
from ..abstract import Component
from ...config import GlobalConfig
from ...constants import UPDATES_PER_SECOND, INACTIVITY_MS, DEFAULT_PROFILE_NAME
from ...exceptions import ExitRequest
from ...utils import get_cursor_pos, keycodes
from ...utils.network import Interfaces
from ...utils.system import monitor_locations


XINPUT_OPCODES = {k: v for k, v in vars(XInput).items()
                  if isinstance(v, int) and hasattr(keycodes, k)}


@dataclass
class DataState:
    """Store the current state of the data.
    This will all be reset whenever tracking restarts.
    """

    tick_current: int = field()
    tick_previous: int = field(default=-1)
    tick_modified: int | None = field(default=None)
    mouse_inactive: bool = field(default=False)
    mouse_clicks: dict[int, tuple[int, int]] = field(default_factory=dict)
    mouse_position: tuple[int, int] | None = field(default_factory=get_cursor_pos)
    monitors: list[tuple[int, int, int, int]] = field(default_factory=monitor_locations)
    gamepads_current: tuple[bool, bool, bool, bool] = field(default_factory=XInput.get_connected)
    gamepads_previous: tuple[bool, bool, bool, bool] = field(default_factory=XInput.get_connected)
    gamepad_force_recheck: bool = field(default=False)
    gamepad_stick_l_position: dict[int, tuple[int, int]] = field(default_factory=dict)
    gamepad_stick_r_position: dict[int, tuple[int, int]] = field(default_factory=dict)
    key_presses: dict[int, tuple[int, int]] = field(default_factory=dict)
    button_presses: dict[int, dict[int, int]] = field(default_factory=lambda: defaultdict(dict))
    bytes_sent_previous: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    bytes_recv_previous: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    bytes_sent: dict[str, int] = field(default_factory=dict)
    bytes_recv: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        self.tick_previous = self.tick_current - 1

        for connection_name, data in psutil.net_io_counters(pernic=True).items():
            self.bytes_sent_previous[connection_name] = data.bytes_sent
            self.bytes_recv_previous[connection_name] = data.bytes_recv


class Tracking(Component):
    def __post_init__(self) -> None:
        self.state = ipc.TrackingState.Paused
        self.profile_name = DEFAULT_PROFILE_NAME
        self.autosave = True

        config = GlobalConfig()
        self.track_mouse = config.track_mouse
        self.track_keyboard = config.track_keyboard
        self.track_gamepad = config.track_gamepad
        self.track_network = config.track_network

        # Setup pynput listeners
        self._pynput_opcodes: set[keycodes.KeyCode] = set()
        self._pynput_mouse_listener = pynput.mouse.Listener(on_move=None,  # Out of bounds values during movement, don't use
                                                            on_click=self._pynput_mouse_click,
                                                            on_scroll=self._pynput_mouse_scroll)
        self._pynput_keyboard_listener = pynput.keyboard.Listener(on_press=self._pynput_key_press,
                                                                  on_release=self._pynput_key_release)

        self._pynput_mouse_listener.start()
        self._pynput_keyboard_listener.start()

    def _receive_data(self):
        for message in self.receive_data():
            match message:
                case ipc.StartTracking():
                    self.state = ipc.TrackingState.Running
                    self.send_data(ipc.TrackingStarted())

                case ipc.PauseTracking():
                    self.state = ipc.TrackingState.Paused

                case ipc.StopTracking():
                    self.state = ipc.TrackingState.Stopped

                case ipc.Exit():
                    raise ExitRequest

                case ipc.DebugRaiseError():
                    raise RuntimeError('[Tracking] Test Exception')

                # Update the current profile
                case ipc.TrackedApplicationDetected():
                    if message.name != self.profile_name:
                        self.data.tick_modified = self.data.tick_current
                        self._calculate_inactivity()
                    self.profile_name = message.name

                case ipc.Autosave():
                    self.autosave = message.enabled
                    print(f'[Tracking] Autosave Enabled: {message.enabled}')

                case ipc.SetGlobalMouseTracking():
                    print(f'[Tracking] Tracking mouse data: {message.enable}')
                    self.track_mouse = message.enable

                case ipc.SetGlobalKeyboardTracking():
                    print(f'[Tracking] Tracking keyboard data: {message.enable}')
                    self.track_keyboard = message.enable

                case ipc.SetGlobalGamepadTracking():
                    print(f'[Tracking] Tracking gamepad data: {message.enable}')
                    self.track_gamepad = message.enable

                case ipc.SetGlobalNetworkTracking():
                    print(f'[Tracking] Tracking network data: {message.enable}')
                    self.track_network = message.enable

    def _run_with_state(self) -> Iterator[tuple[int, DataState]]:
        previous_state = self.state
        for tick in utils.ticks(UPDATES_PER_SECOND):
            self._receive_data()

            state_changed = previous_state != self.state
            previous_state = self.state
            match self.state:

                # When tracking is started, reset the data
                case ipc.TrackingState.Running:
                    if state_changed:
                        print('[Tracking] Started.')
                        self.data = DataState(tick)
                    self.data.tick_current = tick

                    # If pynput gets an event, the it may not be in sync
                    # with polling, and causes the processing component
                    # to be 1 tick off, where `active + inactive` is 1
                    # tick less than `elapsed`.
                    # It's not a permanent desync, but it could possibly
                    # have a race condition on save, so this fix will
                    # prevent that from happening.
                    if self.data.tick_modified == tick - 1:
                        self.data.tick_modified += 1

                    yield tick, self.data

                # When tracking is paused then stop here
                case ipc.TrackingState.Paused:
                    if state_changed:
                        self.data.tick_modified = self.data.tick_current
                        self._calculate_inactivity()
                        print('[Tracking] Paused.')

                # Exit the loop when tracking is stopped
                case ipc.TrackingState.Stopped:
                    self.data.tick_modified = self.data.tick_current
                    self._calculate_inactivity()
                    print('[Tracking] Shut down.')
                    return

    def _calculate_inactivity(self) -> int:
        """Send the activity or inactivity ticks.

        It took a few iterations but this stays completely in sync with
        the elapsed time if `force_update` is set on saving. This is
        required or inactivity will cause a desync.

        TODO: Testing needed on tracking pause/stop
        """
        if self.data.tick_modified is None:
            return 0

        inactivity_threshold = UPDATES_PER_SECOND * INACTIVITY_MS / 1000
        diff = self.data.tick_modified - self.data.tick_previous
        if diff > inactivity_threshold:
            self.send_data(ipc.Inactive(self.profile_name, diff))
        elif diff:
            self.send_data(ipc.Active(self.profile_name, diff))
        self.data.tick_previous = self.data.tick_modified
        self.data.tick_modified = None

        return diff

    def _check_monitor_data(self, pixel: tuple[int, int]) -> None:
        """Check if the monitor data is valid for the pixel.
        If not, recalculate it and update the other components.
        """
        for x1, y1, x2, y2 in self.data.monitors:
            if x1 <= pixel[0] < x2 and y1 <= pixel[1] < y2:
                break
        else:
            print('[Tracking] Error with mouse position, refreshing monitor data...')
            self._refresh_monitor_data()

    def _refresh_monitor_data(self) -> None:
        """Check the monitor data is up to date.
        If not, then send a signal with the updated data.
        """
        self.data.monitors, old_data = monitor_locations(), self.data.monitors
        if old_data != self.data.monitors:
            print('[Tracking] Monitor change detected')
            self.send_data(ipc.MonitorsChanged(self.data.monitors))

    def _pynput_mouse_click(self, x: int, y: int, button: pynput.mouse.Button, pressed: bool) -> None:
        """Triggers on mouse click."""
        if self.state != ipc.TrackingState.Running or not self.track_mouse:
            return

        try:
            idx = ('left', 'middle', 'right', 'x1', 'x2').index(button.name)

        # Ignore anything unknown
        except ValueError:
            return

        if pressed:
            self._pynput_opcodes.add(keycodes.MOUSE_CODES[idx])
        else:
            self._pynput_opcodes.discard(keycodes.MOUSE_CODES[idx])

    def _pynput_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Triggers on mouse scroll.
        The scroll vector is mostly -1, 0 or 1, but support has been
        added in case it can go outside this range.
        """
        if self.state != ipc.TrackingState.Running or not self.track_mouse:
            return

        if dx > 0:
            for _ in range(dx):
                self._key_press(keycodes.VK_SCROLL_RIGHT)
        elif dx < 0:
            for _ in range(-dx):
                self._key_press(keycodes.VK_SCROLL_LEFT)
        if dy > 0:
            for _ in range(dy):
                self._key_press(keycodes.VK_SCROLL_UP)
        elif dy < 0:
            for _ in range(-dy):
                self._key_press(keycodes.VK_SCROLL_DOWN)

    def _pynput_key_press(self, key: pynput.keyboard.KeyCode | pynput.keyboard.Key | None) -> None:
        """Handle when a key is pressed."""
        if self.state != ipc.TrackingState.Running or key is None or not self.track_keyboard:
            return

        if isinstance(key, pynput.keyboard.KeyCode):
            name = key.char
            vk = key.vk
        else:
            name = key.name
            vk = key.value.vk
        self._pynput_opcodes.add(vk)

    def _pynput_key_release(self, key: pynput.keyboard.KeyCode | pynput.keyboard.Key | None) -> None:
        """Handle when a key is released."""
        if self.state != ipc.TrackingState.Running or key is None:
            return

        if isinstance(key, pynput.keyboard.KeyCode):
            name = key.char
            vk = key.vk
        else:
            name = key.name
            vk = key.value.vk
        self._pynput_opcodes.discard(vk)

    def _key_press(self, keycode: int | keycodes.KeyCode) -> None:
        """Handle key presses."""
        self.data.tick_modified = self.data.tick_current
        press_start, press_latest = self.data.key_presses.get(keycode, (self.data.tick_current, 0))

        # Handle all standard keypresses
        if keycode <= 0xFF:
            # First press
            if press_latest != self.data.tick_current - 1:
                if keycode in keycodes.CLICK_CODES and self.data.mouse_position is not None:
                    self.send_data(ipc.MouseClick(int(keycode), self.data.mouse_position))
                self.send_data(ipc.KeyPress(int(keycode)))

            # Being held
            else:
                if keycode in keycodes.CLICK_CODES and self.data.mouse_position is not None:
                    self.send_data(ipc.MouseHeld(int(keycode), self.data.mouse_position))
                self.send_data(ipc.KeyHeld(int(keycode)))

        # Special case for scroll events
        # It is being sent to the "held" array instead of "pressed"
        # since the events will vastly outnumber individual key presses
        # Also note that multiple events may be sent per tick
        elif keycode in keycodes.SCROLL_CODES:
            self.send_data(ipc.KeyHeld(keycode))

        else:
            raise RuntimeError(f'unexpected keycode: {keycode}')

        self.data.key_presses[keycode] = (press_start, self.data.tick_current)

    def run(self):
        """Run the tracking."""
        print('[Tracking] Loaded.')

        for tick, data in self._run_with_state():
            self.send_data(ipc.Tick(tick, int(time.time())))

            if self.track_mouse:
                mouse_position = get_cursor_pos()

                # Check if mouse position is inactive (such as a screensaver)
                # If so then pause everything
                if mouse_position is None:
                    if not data.mouse_inactive:
                        print('[Tracking] Mouse Undetected.')
                        data.mouse_inactive = True
                    continue
                if data.mouse_inactive:
                    print('[Tracking] Mouse detected.')
                    data.mouse_inactive = False

                # Update mouse movement
                if mouse_position != data.mouse_position:
                    self.data.tick_modified = self.data.tick_current
                    self.data.mouse_position = mouse_position
                    self._check_monitor_data(mouse_position)
                    self.send_data(ipc.MouseMove(mouse_position))

            # Check resolution and update if required
            if tick and not tick % UPDATES_PER_SECOND:
                self._refresh_monitor_data()
                self.send_data(ipc.RequestRunningAppCheck())

            # Record key presses / mouse clicks
            for opcode in self._pynput_opcodes:
                self._key_press(opcode)

            # Determine which gamepads are connected
            if self.track_gamepad:
                if not tick % 60 or data.gamepad_force_recheck:
                    data.gamepads_current = XInput.get_connected()
                    data.gamepad_force_recheck = False

                    if data.gamepads_current != data.gamepads_previous:
                        print('[Tracking] Gamepad change detected')
                        data.gamepads_previous = data.gamepads_current

                for gamepad, active in enumerate(data.gamepads_current):
                    if not active:
                        continue

                    # Get a snapshot of the current gamepad state
                    try:
                        state = XInput.get_state(gamepad)
                    except XInput.XInputNotConnectedError:
                        data.gamepad_force_recheck = True
                        continue

                    stick_l, stick_r = XInput.get_thumb_values(state)
                    trig_l, trig_r = XInput.get_trigger_values(state)
                    buttons = XInput.get_button_values(state)

                    buttons['TRIGGER_LEFT'] = trig_l * 100 >= XInput.XINPUT_GAMEPAD_TRIGGER_THRESHOLD
                    buttons['TRIGGER_RIGHT'] = trig_r * 100 >= XInput.XINPUT_GAMEPAD_TRIGGER_THRESHOLD

                    for button, state in buttons.items():
                        if not state:
                            continue
                        self.data.tick_modified = self.data.tick_current
                        if button not in XINPUT_OPCODES:
                            button = f'BUTTON_{button}'
                        keycode = XINPUT_OPCODES[button]

                        press_start, press_latest = data.button_presses.get(keycode, (0, 0))
                        if press_latest != tick - 1:
                            self.send_data(ipc.ButtonPress(gamepad, keycode))
                            data.button_presses[keycode] = (tick, tick)
                        else:
                            self.send_data(ipc.ButtonHeld(gamepad, keycode))
                            data.button_presses[keycode] = (press_start, tick)

                    if stick_l != data.gamepad_stick_l_position.get(gamepad):
                        self.data.tick_modified = self.data.tick_current
                        data.gamepad_stick_l_position[gamepad] = stick_l
                        self.send_data(ipc.ThumbstickMove(gamepad, ipc.ThumbstickMove.Thumbstick.Left, stick_l))

                    if stick_r != data.gamepad_stick_r_position.get(gamepad):
                        self.data.tick_modified = self.data.tick_current
                        data.gamepad_stick_r_position[gamepad] = stick_r
                        self.send_data(ipc.ThumbstickMove(gamepad, ipc.ThumbstickMove.Thumbstick.Right, stick_r))

            if not tick % 60:
                for interface_name, counters in psutil.net_io_counters(pernic=True).items():
                    bytes_sent = counters.bytes_sent - data.bytes_sent_previous.get(interface_name, 0)
                    bytes_recv = counters.bytes_recv - data.bytes_recv_previous.get(interface_name, 0)
                    data.bytes_sent_previous[interface_name] += bytes_sent
                    data.bytes_recv_previous[interface_name] += bytes_recv

                    if bytes_sent or bytes_recv:
                        mac_address = Interfaces.get_from_name(interface_name).mac
                        if mac_address is not None:
                            self.send_data(ipc.DataTransfer(mac_address, bytes_sent, bytes_recv))

            self._calculate_inactivity()

            # Save every 5 mins
            if self.autosave and tick and not tick % (UPDATES_PER_SECOND * 60 * 5):
                self.send_data(ipc.Save())

    def on_exit(self) -> None:
        """Close threads on exit."""
        self._pynput_mouse_listener.stop()
        self._pynput_keyboard_listener.stop()
