import multiprocessing
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterator

import psutil
import pynput
import XInput  # type: ignore

from . import utils
from .. import ipc
from ...constants import UPDATES_PER_SECOND, INACTIVITY_MS, DEFAULT_PROFILE_NAME
from ...utils.network import Interfaces
from ...utils.win import cursor_position, monitor_locations, check_key_press, MOUSE_BUTTONS, SCROLL_EVENTS
from ...utils.win import SCROLL_WHEEL_UP, SCROLL_WHEEL_DOWN, SCROLL_WHEEL_LEFT, SCROLL_WHEEL_RIGHT


XINPUT_OPCODES = {k: v for k, v in vars(XInput).items()
                  if isinstance(v, int) and k.split('_')[0] in ('BUTTON', 'STICK', 'TRIGGER')}


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
    mouse_position: tuple[int, int] | None = field(default_factory=cursor_position)
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


class Tracking:
    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        self.q_send = q_send
        self.q_receive = q_receive
        self.state = ipc.TrackingState.State.Pause
        self.profile_name = DEFAULT_PROFILE_NAME

        # Setup pynput listeners
        # TODO: link up the other callbacks
        self._pynput_mouse_listener = pynput.mouse.Listener(on_move=None, on_click=None, on_scroll=self._pynput_mouse_scroll)
        self._pynput_keyboard_listener = pynput.keyboard.Listener(on_press=None, on_release=None)

        self._pynput_mouse_listener.start()
        self._pynput_keyboard_listener.start()

    def send_data(self, message: ipc.Message):
        self.q_send.put(message)

    def _receive_data(self):
        while not self.q_receive.empty():
            message = self.q_receive.get()

            match message:
                case ipc.TrackingState():
                    self.state = message.state

                case ipc.DebugRaiseError():
                    raise RuntimeError('[Tracking] Test Exception')

                case ipc.ApplicationDetected():
                    if message.name != self.profile_name:
                        self.data.tick_modified = self.data.tick_current
                        self._calculate_inactivity()
                    self.profile_name = message.name

    def _run_with_state(self) -> Iterator[tuple[int, DataState]]:
        previous_state = self.state
        for tick in utils.ticks(UPDATES_PER_SECOND):
            self._receive_data()

            state_changed = previous_state != self.state
            previous_state = self.state
            match self.state:

                # When tracking is started, reset the data
                case ipc.TrackingState.State.Start:
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
                case ipc.TrackingState.State.Pause:
                    if state_changed:
                        self.data.tick_modified = self.data.tick_current
                        self._calculate_inactivity()
                        print('[Tracking] Paused.')

                # Exit the loop when tracking is stopped
                case ipc.TrackingState.State.Stop:
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

    def _pynput_mouse_scroll(self, x: int, y: int, dx: int, dy: int) -> None:
        """Triggers on mouse scroll.
        The scroll vector is mostly -1, 0 or 1, but support has been
        added in case it can go outside this range.
        """
        if dx > 0:
            for _ in range(dx):
                self._key_press(SCROLL_WHEEL_RIGHT)
        elif dx < 0:
            for _ in range(-dx):
                self._key_press(SCROLL_WHEEL_LEFT)
        if dy > 0:
            for _ in range(dy):
                self._key_press(SCROLL_WHEEL_UP)
        elif dy < 0:
            for _ in range(-dy):
                self._key_press(SCROLL_WHEEL_DOWN)

    def _key_press(self, opcode: int) -> None:
        """Handle key presses."""
        self.data.tick_modified = self.data.tick_current

        press_start, press_latest = self.data.key_presses.get(opcode, (self.data.tick_current, 0))

        # Handle all standard keypresses
        if opcode <= 0xFF:
            # First press
            if press_latest != self.data.tick_current - 1:
                if opcode in MOUSE_BUTTONS and self.data.mouse_position is not None:
                    self.send_data(ipc.MouseClick(opcode, self.data.mouse_position))
                self.send_data(ipc.KeyPress(opcode))

            # Being held
            else:
                if opcode in MOUSE_BUTTONS and self.data.mouse_position is not None:
                    self.send_data(ipc.MouseHeld(opcode, self.data.mouse_position))
                self.send_data(ipc.KeyHeld(opcode))

        # Special case for scroll events
        # It is being sent to the "held" array instead of "pressed"
        # since the events will vastly outnumber individual key presses
        # Also note that multiple events may be sent per tick
        elif opcode in SCROLL_EVENTS:
            self.send_data(ipc.KeyHeld(opcode))

        else:
            raise RuntimeError(f'unexpected opcode: {opcode}')

        self.data.key_presses[opcode] = (press_start, self.data.tick_current)

    def _run(self):
        print('[Tracking] Loaded.')

        for tick, data in self._run_with_state():
            self.send_data(ipc.Tick(tick, int(time.time())))

            mouse_position = cursor_position()

            # Check if mouse position is inactive (such as a screensaver)
            if mouse_position is None:
                if not data.mouse_inactive:
                    print('[Tracking] Mouse Undetected.')
                    data.mouse_inactive = True
                continue
            if data.mouse_inactive:
                print('[Tracking] Mouse detected.')
                data.mouse_inactive = False

            # Check resolution and update if required
            if tick and not tick % 60:
                self._refresh_monitor_data()
                self.send_data(ipc.RequestRunningAppCheck())

            # Update mouse movement
            if mouse_position != data.mouse_position:
                self.data.tick_modified = self.data.tick_current
                self.data.mouse_position = mouse_position
                self._check_monitor_data(mouse_position)
                self.send_data(ipc.MouseMove(mouse_position))

            # Record key presses / mouse clicks
            for opcode in filter(check_key_press, range(0x01, 0xFF)):
                self._key_press(opcode)

            # Determine which gamepads are connected
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
                    opcode = XINPUT_OPCODES[button]

                    press_start, press_latest = data.button_presses.get(opcode, (0, 0))
                    if press_latest != tick - 1:
                        self.send_data(ipc.ButtonPress(gamepad, opcode))
                        data.button_presses[opcode] = (tick, tick)
                    else:
                        self.send_data(ipc.ButtonHeld(gamepad, opcode))
                        data.button_presses[opcode] = (press_start, tick)

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
            if tick and not tick % (UPDATES_PER_SECOND * 60 * 5):
                self.send_data(ipc.Save())

    def run(self) -> None:
        print('[Tracking] Loaded.')

        try:
            self._run()

        # Catch error after KeyboardInterrupt
        except EOFError:
            print('[Tracking] Force shut down.')
            return

        except Exception as e:
            self.q_send.put(ipc.Traceback(e, traceback.format_exc()))
            print(f'[Tracking] Error shut down: {e}')

        finally:
            self._pynput_mouse_listener.stop()
            self._pynput_keyboard_listener.stop()

        self.q_send.put(ipc.ProcessShutDownNotification(ipc.Target.Tracking))
        print('[Tracking] Sent process closed notification.')


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
    Tracking(q_send, q_receive).run()
