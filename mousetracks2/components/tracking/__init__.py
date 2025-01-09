import multiprocessing
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterator, Optional
from uuid import getnode

import psutil
import pynput
import XInput

from . import utils
from .. import ipc
from ...constants import UPDATES_PER_SECOND
from ...utils.win import cursor_position, monitor_locations, check_key_press, MOUSE_BUTTONS, SCROLL_EVENTS
from ...utils.win import SCROLL_WHEEL_UP, SCROLL_WHEEL_DOWN, SCROLL_WHEEL_LEFT, SCROLL_WHEEL_RIGHT


XINPUT_OPCODES = {k: v for k, v in vars(XInput).items()
                  if isinstance(v, int) and k.split('_')[0] in ('BUTTON', 'STICK', 'TRIGGER')}


def get_mac_addresses() -> dict[str, Optional[str]]:
    """Fetch MAC addresses for all network interfaces."""
    mac_addresses: dict[str, str] = {}
    for interface_name, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == psutil.AF_LINK:  # Identifies MAC address family
                mac_addresses[interface_name] = addr.address
                break
        else:
            mac_addresses[interface_name] = None
    return mac_addresses


@dataclass
class DataState:
    tick: int = field(default=0)
    mouse_inactive: bool = field(default=False)
    mouse_clicks: dict[int, tuple[int, int]] = field(default_factory=dict)
    mouse_position: Optional[tuple[int, int]] = field(default_factory=cursor_position)
    monitors: list[tuple[int, int, int, int]] = field(default_factory=monitor_locations)
    gamepads_current: tuple[bool, bool, bool, bool] = field(default_factory=XInput.get_connected)
    gamepads_previous: tuple[bool, bool, bool, bool] = field(default_factory=XInput.get_connected)
    gamepad_force_recheck: bool = field(default=False)
    gamepad_stick_l_position: dict[int, Optional[tuple[int, int]]] = field(default_factory=lambda: defaultdict(int))
    gamepad_stick_r_position: dict[int, Optional[tuple[int, int]]] = field(default_factory=lambda: defaultdict(int))
    key_presses: dict[int, int] = field(default_factory=dict)
    button_presses: dict[int, dict[int, int]] = field(default_factory=lambda: defaultdict(dict))
    bytes_sent_previous: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    bytes_recv_previous: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    bytes_sent: dict[str, int] = field(default_factory=dict)
    bytes_recv: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        for connection_name, data in psutil.net_io_counters(pernic=True).items():
            self.bytes_sent_previous[connection_name] = data.bytes_sent
            self.bytes_recv_previous[connection_name] = data.bytes_recv


class Tracking:
    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        self.q_send = q_send
        self.q_receive = q_receive
        self.state = ipc.TrackingState.State.Pause

        self._interface_mac_addresses = get_mac_addresses()

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
                        self.data = DataState()
                    self.data.tick = tick
                    yield tick, self.data

                # When tracking is paused then stop here
                case ipc.TrackingState.State.Pause:
                    if state_changed:
                        print('[Tracking] Paused.')

                # Exit the loop when tracking is stopped
                case ipc.TrackingState.State.Stop:
                    print('[Tracking] Shut down.')
                    return

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
        press_start, press_latest = self.data.key_presses.get(opcode, (self.data.tick, 0))

        # Handle all standard keypresses
        if opcode <= 0xFF:
            # First press
            if press_latest != self.data.tick - 1:
                if opcode in MOUSE_BUTTONS:
                    self.send_data(ipc.MouseClick(opcode, self.data.mouse_position))
                self.send_data(ipc.KeyPress(opcode))

            # Being held
            else:
                if opcode in MOUSE_BUTTONS:
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

        self.data.key_presses[opcode] = (press_start, self.data.tick)

    def _run(self):
        print('[Tracking] Loaded.')

        last_activity = 0

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
                self.data.mouse_position = mouse_position
                last_activity = tick
                self._check_monitor_data(mouse_position)
                self.send_data(ipc.MouseMove(mouse_position))

            # Record key presses / mouse clicks
            for opcode in filter(check_key_press, range(0x01, 0xFF)):
                last_activity = tick
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
                    last_activity = tick
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

                if stick_l != data.gamepad_stick_l_position[gamepad]:
                    last_activity = tick
                    data.gamepad_stick_l_position[gamepad] = stick_l
                    self.send_data(ipc.ThumbstickMove(gamepad, ipc.ThumbstickMove.Thumbstick.Left, stick_l))

                if stick_r != data.gamepad_stick_r_position[gamepad]:
                    last_activity = tick
                    data.gamepad_stick_r_position[gamepad] = stick_r
                    self.send_data(ipc.ThumbstickMove(gamepad, ipc.ThumbstickMove.Thumbstick.Right, stick_r))

            if not tick % 60:
                for interface_name, counters in psutil.net_io_counters(pernic=True).items():
                    bytes_sent = counters.bytes_sent - data.bytes_sent_previous.get(interface_name, 0)
                    bytes_recv = counters.bytes_recv - data.bytes_recv_previous.get(interface_name, 0)
                    data.bytes_sent_previous[interface_name] += bytes_sent
                    data.bytes_recv_previous[interface_name] += bytes_recv

                    if bytes_sent or bytes_recv:
                        try:
                            mac_addr = self._interface_mac_addresses[interface_name]
                        except KeyError:
                            self._interface_mac_addresses.update(get_mac_addresses())
                            mac_addr = self._interface_mac_addresses[interface_name]

                        if mac_addr is not None:
                            self.send_data(ipc.DataTransfer(mac_addr, bytes_sent, bytes_recv))

            if tick and not tick % 3000:
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
