import multiprocessing
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import XInput

from . import utils
from .. import ipc
from ...utils.win import cursor_position, monitor_locations, check_key_press, MOUSE_BUTTONS


UPDATES_PER_SECOND = 60

DOUBLE_CLICK_TIME = 500


@dataclass
class DataState:
    mouse_inactive: bool = field(default=False)
    mouse_clicks: dict[int, tuple[int, int]] = field(default_factory=dict)
    mouse_position: Optional[tuple[int, int]] = field(default_factory=cursor_position)
    monitors: list[tuple[int, int, int, int]] = field(default_factory=monitor_locations)
    gamepads_current: tuple[bool, bool, bool, bool] = field(default_factory=XInput.get_connected)
    gamepads_previous: tuple[bool, bool, bool, bool] = field(default_factory=XInput.get_connected)
    gamepad_force_recheck: bool = field(default=False)
    key_presses: dict[int, int] = field(default_factory=dict)
    button_presses: dict[int, dict[int, int]] = field(default_factory=lambda: defaultdict(dict))


class Tracking:
    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        self.q_send = q_send
        self.q_receive = q_receive
        self.state = ipc.TrackingState.State.Pause

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

    def _run_with_state(self):
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
                        data = DataState()
                    yield tick, data

                # When tracking is paused then stop here
                case ipc.TrackingState.State.Pause:
                    if state_changed:
                        print('[Tracking] Paused.')

                # Exit the loop when tracking is stopped
                case ipc.TrackingState.State.Stop:
                    print('[Tracking] Shut down.')
                    return

    def _check_monitor_data(self, data: DataState, pixel: tuple[int, int]) -> None:
        """Check if the monitor data is valid for the pixel.
        If not, recalculate it and update the other components.
        """
        for x1, y1, x2, y2 in data.monitors:
            if x1 <= pixel[0] < x2 and y1 <= pixel[1] < y2:
                break
        else:
            print('[Tracking] Error with mouse position, refreshing monitor data...')
            self._refresh_monitor_data(data)

    def _refresh_monitor_data(self, data: DataState) -> None:
        """Check the monitor data is up to date.
        If not, then send a signal with the updated data.
        """
        data.monitors, old_data = monitor_locations(), data.monitors
        if old_data != data.monitors:
            print('[Tracking] Monitor change detected')
            self.send_data(ipc.MonitorsChanged(data.monitors))

    def _run(self):
        print('[Tracking] Loaded.')

        last_activity = 0

        for tick, data in self._run_with_state():
            self.send_data(ipc.Tick(tick))

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
                self._refresh_monitor_data(data)

            # Update mouse movement
            if mouse_position != data.mouse_position:
                data.mouse_position = mouse_position
                last_activity = tick
                self._check_monitor_data(data, mouse_position)
                self.send_data(ipc.MouseMove(mouse_position))

            # Record key presses / mouse clicks
            for opcode in filter(check_key_press, range(0x01, 0xFF)):
                last_activity = tick

                press_start, press_latest = data.key_presses.get(opcode, (0, 0))

                # First press
                if press_latest != tick - 1:
                    if opcode in MOUSE_BUTTONS:
                        self.send_data(ipc.MouseClick(opcode, mouse_position))
                    else:
                        self.send_data(ipc.KeyPress(opcode))
                    data.key_presses[opcode] = (tick, tick)

                # Being held
                else:
                    if opcode in MOUSE_BUTTONS:
                        self.send_data(ipc.MouseHeld(opcode, mouse_position))
                    else:
                        self.send_data(ipc.KeyHeld(opcode))
                    data.key_presses[opcode] = (press_start, tick)

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

                thumb_l, thumb_r = XInput.get_thumb_values(state)
                trig_l, trig_r = XInput.get_trigger_values(state)
                buttons = XInput.get_button_values(state)

                if not (thumb_l or thumb_r or trig_l or trig_r or buttons):
                    continue
                last_activity = tick

                for button, state in buttons.items():
                    if not state:
                        continue
                    opcode = getattr(XInput, f'BUTTON_{button}')

                    press_start, press_latest = data.button_presses.get(opcode, (0, 0))
                    if press_latest != tick - 1:
                        self.send_data(ipc.ButtonPress(gamepad, opcode))
                        data.button_presses[opcode] = (tick, tick)
                    else:
                        self.send_data(ipc.ButtonHeld(gamepad, opcode))
                        data.button_presses[opcode] = (press_start, tick)

                self.send_data(ipc.ThumbstickMove(gamepad, ipc.ThumbstickMove.Thumbstick.Left, thumb_l))
                self.send_data(ipc.ThumbstickMove(gamepad, ipc.ThumbstickMove.Thumbstick.Right, thumb_r))

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
            print('[Tracking] Error shut down.')

        self.q_send.put(ipc.ProcessShutDownNotification(ipc.Target.Tracking))
        print('[Tracking] Sent process closed notification.')


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
    Tracking(q_send, q_receive).run()
