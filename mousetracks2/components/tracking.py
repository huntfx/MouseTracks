import time
import traceback
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from itertools import count
from typing import Iterator

import psutil
import pynput
try:
    import XInput  # type: ignore
except IOError:
    XInput = None

from . import ipc
from .abstract import Component
from ..config import CLI, GlobalConfig
from ..constants import UPDATES_PER_SECOND, DEFAULT_PROFILE_NAME
from ..exceptions import ExitRequest
from ..utils import keycodes
from ..utils.monitor import MonitorData
from ..utils.input import get_cursor_pos
from ..utils.interface import Interfaces
from ..utils.system import MonitorEventsListener, hide_child_process


if XInput is None:
    XINPUT_OPCODES = {}
else:
    XINPUT_OPCODES = {k: v for k, v in vars(XInput).items()
                      if isinstance(v, int) and hasattr(keycodes, k)}


def ticks(ups: int) -> Iterator[int]:
    """Count up at a constant speed.

    If any delay occurs, it will account for this and will continue to
    count at a constant rate, resuming from the previous tick.
    For example, if a PC gets put to sleep, then waking it up should
    resume from the tick it was put to sleep at.
    """
    start = time.time()
    for tick in count():
        yield tick

        # Calculate the expected time for the next tick
        expected = start + (tick + 1) / ups
        remaining = expected - time.time()

        # Adjust the start time to account for missed time
        if remaining < 0:
            missed_ticks = -int(remaining * ups)
            start += missed_ticks / ups
            continue

        time.sleep(remaining)


def _getConnectedGamepads() -> tuple[bool, bool, bool, bool]:
    """Determine which gamepad indexes are connected."""
    if XInput is None:
        return (False, False, False, False)
    return XInput.get_connected()


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
    monitors: MonitorData = field(default_factory=MonitorData)
    gamepads_current: tuple[bool, bool, bool, bool] = field(default_factory=_getConnectedGamepads)
    gamepads_previous: tuple[bool, bool, bool, bool] = field(default_factory=_getConnectedGamepads)
    gamepad_force_recheck: bool = field(default=False)
    gamepad_stick_l_position: dict[int, tuple[int, int]] = field(default_factory=dict)
    gamepad_stick_r_position: dict[int, tuple[int, int]] = field(default_factory=dict)
    key_presses: dict[int, tuple[int, int]] = field(default_factory=dict)
    button_presses: dict[int, tuple[int, int]] = field(default_factory=dict)
    bytes_sent_previous: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    bytes_recv_previous: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    bytes_sent: dict[str, int] = field(default_factory=dict)
    bytes_recv: dict[str, int] = field(default_factory=dict)
    pynput_opcodes: dict[int | keycodes.KeyCode, int] = field(default_factory=dict)
    pynput_quick_press: list[int | keycodes.KeyCode] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.tick_previous = self.tick_current - 1

    def reset_byte_counter(self) -> None:
        """Reset the byte counter to its current values."""
        self.bytes_sent_previous.clear()
        self.bytes_recv_previous.clear()
        for connection_name, counters in psutil.net_io_counters(pernic=True).items():
            self.bytes_sent_previous[connection_name] = counters.bytes_sent
            self.bytes_recv_previous[connection_name] = counters.bytes_recv


class Tracking(Component):
    def __post_init__(self) -> None:
        hide_child_process()

        self.state = ipc.TrackingState.Paused
        self.profile_name = DEFAULT_PROFILE_NAME
        self.autosave = True
        self.update_apps = True
        self.update_monitors = True

        config = GlobalConfig()
        self.track_mouse = not CLI.disable_mouse and config.track_mouse
        self.track_keyboard = not CLI.disable_keyboard and config.track_keyboard
        self.track_gamepad = not CLI.disable_gamepad and config.track_gamepad
        self.track_network = not CLI.disable_network and config.track_network

        # Setup pynput listeners
        self._pynput_mouse_listener = pynput.mouse.Listener(on_move=None,  # Out of bounds values during movement, don't use
                                                            on_click=self._pynput_mouse_click,
                                                            on_scroll=self._pynput_mouse_scroll)
        self._pynput_keyboard_listener = pynput.keyboard.Listener(on_press=self._pynput_key_press,
                                                                  on_release=self._pynput_key_release)

        self._pynput_mouse_listener.start()
        self._pynput_keyboard_listener.start()

        self._monitor_listener = MonitorEventsListener()
        self._monitor_listener.start()

    def _receive_data(self) -> None:
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

                case ipc.TrackedApplicationDetected():

                    # Profile has changed, so reset the data
                    if message.name != self.profile_name:
                        self.data.tick_modified = self.data.tick_current
                        self._calculate_inactivity()
                        self.data.pynput_opcodes.clear()
                        self.data.pynput_quick_press.clear()
                        self.profile_name = message.name

                    self.send_data(ipc.CurrentProfileChanged(message.name, message.process_id, message.rects))

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
                    if message.enable:
                        self.data.reset_byte_counter()

                case ipc.DebugDisableAppDetection():
                    print(f'[Tracking] Disabled check for running applications: {message.disable}')
                    self.update_apps = not message.disable

                case ipc.DebugDisableMonitorCheck():
                    print(f'[Tracking] Disabled check for monitor changes: {message.disable}')
                    self.update_monitors = not message.disable

                    if message.disable:
                        self._monitor_listener.stop()
                    else:
                        self._monitor_listener = MonitorEventsListener()
                        self._monitor_listener.start()

    def _run_with_state(self) -> Iterator[tuple[int, DataState]]:
        previous_state = self.state
        started = False
        for tick in ticks(UPDATES_PER_SECOND):
            self._receive_data()

            state_changed = previous_state != self.state
            previous_state = self.state
            match self.state:

                # When tracking is started, reset the data
                case ipc.TrackingState.Running:
                    if state_changed:
                        print('[Tracking] Started.')
                        self.data = DataState(tick)
                        started = True
                        if self.track_network:
                            self.data.reset_byte_counter()

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
                    if state_changed and started:
                        self.data.tick_modified = self.data.tick_current
                        self._calculate_inactivity()
                        print('[Tracking] Paused.')

                # Exit the loop when tracking is stopped
                case ipc.TrackingState.Stopped:
                    if started:
                        self.data.tick_modified = self.data.tick_current
                        self._calculate_inactivity()
                    print('[Tracking] Shut down.')
                    return

    def _calculate_inactivity(self) -> int:
        """Send the activity or inactivity ticks.
        This is required to keep the active and inactive time in sync
        with the elapsed time.
        """
        if self.data.tick_modified is None:
            return 0

        inactivity_threshold = UPDATES_PER_SECOND * GlobalConfig.inactivity_time
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
        for monitor in self.data.monitors.logical:  # TODO: Test
            x1, y1, x2, y2 = monitor.rect
            if x1 <= pixel[0] < x2 and y1 <= pixel[1] < y2:
                break
        else:
            print('[Tracking] Error with mouse position, refreshing monitor data...')
            self._refresh_monitor_data()

    def _refresh_monitor_data(self) -> None:
        """Check the monitor data is up to date.
        If not, then send a signal with the updated data.
        """
        self.data.monitors, old_data = MonitorData(), self.data.monitors
        if old_data != self.data.monitors:
            print('[Tracking] Monitor change detected')
            self.send_data(ipc.MonitorsChanged(self.data.monitors))

    @contextmanager
    def _exception_handler(self) -> Iterator[None]:
        """Custom exception handler to ensure an error is handled.

        This is used for the `pynput` threads, as any errors will
        otherwise just shut them down without affecting anything else.
        """
        try:
            yield
        except Exception as e:
            self.send_data(ipc.Traceback(e, traceback.format_exc()))

    def _pynput_mouse_click(self, x: int, y: int, button: pynput.mouse.Button, pressed: bool) -> None:
        """Triggers on mouse click."""
        if self.state != ipc.TrackingState.Running or not self.track_mouse:
            return

        with self._exception_handler():
            try:
                idx = ('left', 'middle', 'right', 'x1', 'x2').index(button.name)

            # Ignore anything unknown
            except ValueError:
                return

            if pressed:
                self.data.pynput_opcodes[keycodes.MOUSE_CODES[idx]] = self.data.tick_current
            elif keycodes.MOUSE_CODES[idx] in self.data.pynput_opcodes:
                del self.data.pynput_opcodes[keycodes.MOUSE_CODES[idx]]

    def _pynput_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Triggers on mouse scroll.
        The scroll vector is mostly -1, 0 or 1, but support has been
        added in case it can go outside this range.
        """
        if self.state != ipc.TrackingState.Running or not self.track_mouse:
            return

        with self._exception_handler():
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

        with self._exception_handler():
            vk = keycodes.KeyCode(key)
            self.data.pynput_opcodes[vk] = self.data.tick_current

    def _pynput_key_release(self, key: pynput.keyboard.KeyCode | pynput.keyboard.Key | None) -> None:
        """Handle when a key is released."""
        if self.state != ipc.TrackingState.Running or key is None:
            return

        with self._exception_handler():
            vk = keycodes.KeyCode(key)
            if vk in self.data.pynput_opcodes:
                recorded_tick = self.data.pynput_opcodes.pop(vk)

                # Some keyboard features may emit faster than a tick
                # If so, queue them in a separate list
                if recorded_tick == self.data.tick_current:
                    self.data.pynput_quick_press.append(vk)

    def _key_press(self, keycode: int | keycodes.KeyCode, quick_press: bool = False) -> None:
        """Handle key presses."""
        self.data.tick_modified = self.data.tick_current
        press_start, press_latest = self.data.key_presses.get(keycode, (self.data.tick_current, 0))

        # Handle all standard keypresses
        if keycode <= 0xFF:
            # First press
            if quick_press or press_latest != self.data.tick_current - 1:
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

    def run(self) -> None:
        """Run the tracking."""
        print('[Tracking] Loaded.')
        self.send_data(ipc.ComponentLoaded(ipc.Target.Tracking))

        for tick, data in self._run_with_state():
            self.send_data(ipc.Tick(tick, int(time.time())))

            # Check for loaded applications
            if self.update_apps and tick and not tick % int(UPDATES_PER_SECOND * GlobalConfig.application_check_frequency):
                self.send_data(ipc.RequestRunningAppCheck())

            # Update monitor data
            if self.update_monitors and self._monitor_listener.triggered:
                self._refresh_monitor_data()

            # Update mouse data
            if self.track_mouse:
                mouse_position = get_cursor_pos()

                # Check if mouse position is inactive (such as a screensaver)
                if mouse_position is None:
                    if not data.mouse_inactive:
                        print('[Tracking] Mouse Undetected.')
                        data.mouse_inactive = True

                else:
                    if data.mouse_inactive:
                        print('[Tracking] Mouse detected.')
                        data.mouse_inactive = False

                    # Update mouse movement
                    if mouse_position != data.mouse_position:
                        self.data.tick_modified = self.data.tick_current
                        self.data.mouse_position = mouse_position
                        self._check_monitor_data(mouse_position)
                        self.send_data(ipc.MouseMove(mouse_position))

            # Record key presses / mouse clicks
            for opcode in tuple(self.data.pynput_opcodes):
                self._key_press(opcode)
            while self.data.pynput_quick_press:
                self._key_press(self.data.pynput_quick_press.pop(), quick_press=True)

            # Determine which gamepads are connected
            if self.track_gamepad and XInput is not None:
                if not tick % int(UPDATES_PER_SECOND * GlobalConfig.gamepad_check_frequency) or data.gamepad_force_recheck:
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

            if self.track_network and not tick % UPDATES_PER_SECOND:
                for interface_name, counters in psutil.net_io_counters(pernic=True).items():
                    prev_sent = data.bytes_sent_previous.get(interface_name, 0)
                    prev_recv = data.bytes_recv_previous.get(interface_name, 0)

                    # If a network disconnects its counters will reset
                    if counters.bytes_sent < prev_sent or counters.bytes_recv < prev_recv:
                        prev_sent = prev_recv = 0
                    else:
                        bytes_sent = counters.bytes_sent - prev_sent
                        bytes_recv = counters.bytes_recv - prev_recv

                    data.bytes_sent_previous[interface_name] = counters.bytes_sent
                    data.bytes_recv_previous[interface_name] = counters.bytes_recv

                    if bytes_sent or bytes_recv:
                        mac_address = Interfaces.get_from_name(interface_name).mac
                        if mac_address is not None:
                            self.send_data(ipc.DataTransfer(mac_address, bytes_sent, bytes_recv))

            self._calculate_inactivity()

            # Save every 5 mins
            if self.autosave and tick and not tick % int(UPDATES_PER_SECOND * GlobalConfig.save_frequency):
                self.send_data(ipc.Save())

    def on_exit(self) -> None:
        """Close threads on exit."""
        self._pynput_mouse_listener.stop()
        self._pynput_keyboard_listener.stop()
        self._monitor_listener.stop()
