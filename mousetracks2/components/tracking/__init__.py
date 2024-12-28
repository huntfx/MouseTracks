import multiprocessing
import time
from dataclasses import dataclass, field
from typing import Optional

from . import utils
from .. import ipc
from ...utils.win import cursor_position, monitor_locations, get_mouse_click


UPDATES_PER_SECOND = 60

DOUBLE_CLICK_TIME = 500


@dataclass
class DataState:
    mouse_inactive: bool = field(default=False)
    mouse_clicks: dict[int, tuple[int, int]] = field(default_factory=dict)
    mouse_position: Optional[tuple[int, int]] = field(default_factory=cursor_position)
    monitors: list[tuple[int, int, int, int]] = field(default_factory=monitor_locations)


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
            self._refresh_monitor_data(data)

    def _refresh_monitor_data(self, data: DataState) -> None:
        """Check the monitor data is up to date.
        If not, then send a signal with the updated data.
        """
        data.monitors, old_data = monitor_locations(), data.monitors
        if old_data != data.monitors:
            print('[Tracking] Monitor change detected')
            self.send_data(ipc.MonitorsChanged(data.monitors))

    def run(self):
        print('[Tracking] Loaded.')

        last_activity = 0
        mouse_double_click = DOUBLE_CLICK_TIME / 1000 * UPDATES_PER_SECOND

        for tick, data in self._run_with_state():
            # Check resolution and update if required
            if tick and not tick % 60:
                self._refresh_monitor_data(data)

            mouse_position = cursor_position()

            # Check if mouse position is inactive (such as a screensaver)
            # If so then wait and try again
            if mouse_position is None:
                if not data.mouse_inactive:
                    print('[Tracking] Mouse Undetected.')
                    data.mouse_inactive = True
                time.sleep(2)
                continue
            if data.mouse_inactive:
                print('[Tracking] Mouse detected.')
                data.mouse_inactive = False

            # Update mouse movement
            if mouse_position != data.mouse_position:
                data.mouse_position = mouse_position
                last_activity = tick
                self._check_monitor_data(data, mouse_position)
                self.send_data(ipc.MouseMove(tick, mouse_position))

            for mouse_button, clicked in get_mouse_click().items():
                if not clicked:
                    continue
                click_start, click_latest = data.mouse_clicks.get(mouse_button, (0, 0))
                last_activity = tick

                # First click
                if click_latest != tick - 1:
                    # Check if previous click was within the double click period
                    double_click = click_start + mouse_double_click > tick
                    self.send_data(ipc.MouseClick(mouse_button, mouse_position, double_click))
                    data.mouse_clicks[mouse_button] = (tick, tick)

                # Being held
                else:
                    data.mouse_clicks[mouse_button] = (click_start, tick)


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
    Tracking(q_send, q_receive).run()
