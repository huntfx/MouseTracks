import multiprocessing
import traceback
from typing import TYPE_CHECKING

from mousetracks.applications import RunningApplications, WindowFocus
from .. import ipc
from ..abstract import Component
from ...constants import DEFAULT_PROFILE_NAME
from ...exceptions import ExitRequest
from ...utils.win import monitor_locations


class AppDetection(Component):
    """Application detection component.

    This is using legacy code for the time being, just to get an inital
    version out the door. I plan to improve it at some point.
    """

    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        super().__init__(q_send, q_receive)

        self.running_apps = RunningApplications()
        self.previous_app: tuple[str, str] | None = None
        self.last_coordinates = None
        self.last_resolution = None

        self._previous_focus: tuple[str, str] = '', ''
        self._current_focus = self.running_apps.focused_exe, self.running_apps.focused_name

        self.state = ipc.TrackingState.State.Pause

    def _process_message(self, message: ipc.Message) -> None:
        """Process an item of data."""
        match message:
            case ipc.TrackingState():
                self.state = message.state
                if self.state == ipc.TrackingState.State.Stop:
                    raise ExitRequest

            # This is using the legacy app detection for the time being
            case ipc.RequestRunningAppCheck():
                self.running_apps.refresh()

                # Display the current focus for easier debugging
                self._current_focus = (self.running_apps.focused_exe, self.running_apps.focused_name)
                if self._previous_focus != self._current_focus:
                    self._previous_focus = self._current_focus
                    print(f'[Application Detection] Focus changed: {self._current_focus[0]} ({self._current_focus[1]})')

                current_app: tuple[str, str] | None = None
                focused = self.running_apps.focus

                app_position = app_resolution = None
                process_id: int | None = None
                app_is_windowed = False
                changed = False
                if focused is not None:
                    current_app = self.running_apps.check()  # (name, exe)
                    process_id = focused.pid

                    if current_app is not None:
                        app_position = focused.rect
                        app_resolution = focused.resolution

                        if current_app == self.previous_app:
                            if app_resolution != self.last_resolution:
                                changed = True
                                print(f'[Application Detection] {current_app[0]} resized: {self.last_resolution} -> {app_resolution}')
                            elif app_position != self.last_coordinates:
                                changed = True
                                print(f'[Application Detection] {current_app[0]} moved: {self.last_coordinates} -> {app_position}')
                        else:
                            changed = True
                            print(f'[Application Detection] {current_app[0]} loaded')

                        self.last_coordinates = app_position
                        self.last_resolution = app_resolution

                        # Somewhat hacky way to detect if the application is full screen spanning multiple monitors
                        # If this is the case, we want to record both monitors as normal
                        app_is_windowed = True
                        if app_resolution is not None:
                            x_min = x_max = y_min = y_max = 0
                            for x1, y1, x2, y2 in monitor_locations():
                                x_min = min(x_min, x1)
                                x_max = max(x_max, x2)
                                y_min = min(y_min, y1)
                                y_max = max(y_max, y2)
                            if (x_max - x_min, y_max - y_min) == app_resolution:
                                app_is_windowed = False

                if current_app != self.previous_app:
                    if focused is None:
                        if current_app is None:
                            if TYPE_CHECKING: assert self.previous_app is not None
                            print(f'[Application Detection] {self.previous_app[0]} ended')
                            changed = True
                        else:
                            print(f'[Application Detection] {current_app[0]} started')
                            changed = True

                    else:
                        if self.previous_app is not None:
                            print(f'[Application Detection] {self.previous_app[0]} lost focus')
                            changed = True
                        elif current_app is not None:
                            print(f'[Application Detection] {current_app[0]} gained focus')
                            changed = True

                if changed:
                    if current_app is None:
                        self.send_data(ipc.ApplicationDetected(DEFAULT_PROFILE_NAME, None, None))
                    elif app_is_windowed:
                        self.send_data(ipc.ApplicationDetected(current_app[0], process_id, app_position))
                    else:
                        self.send_data(ipc.ApplicationDetected(current_app[0], process_id, None))

                self.previous_app = current_app

            case ipc.DebugRaiseError():
                raise RuntimeError('[Application Detection] Test Exception')

    def run(self):
        """Listen for events to process."""
        while True:
            self._process_message(self.receive_data())
