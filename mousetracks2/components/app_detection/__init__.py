import multiprocessing
import traceback
from typing import Optional

from mousetracks.applications import RunningApplications
from .. import ipc
from ...constants import DEFAULT_PROFILE_NAME
from ...utils.win import monitor_locations


class ExitRequest(Exception):
    """Custom exception to raise and catch when an exit is requested."""


class AppDetection:
    """Application detection component.

    This is using legacy code for the time being, just to get an inital
    version out the door. I plan to improve it at some point.
    """

    def __init__(self, q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
        self.q_send = q_send
        self.q_receive = q_receive
        self.running_apps = RunningApplications()
        self.previous_app = None
        self.last_coordinates = None
        self.last_resolution = None

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

                current_app: Optional[tuple[str, str]] = None
                focused = self.running_apps.focus

                app_position = app_resolution = None
                process_id: Optional[int] = None
                app_is_windowed = False
                changed = False
                if focused is not None:
                    current_app: Optional[tuple[str, str]] = self.running_apps.check()  # (name, exe)
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
                            print(f'[Application Detection] {self.previous_app[0]} ended')
                            changed = True
                        elif current_app is not None:
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
                        self.q_send.put(ipc.ApplicationDetected(DEFAULT_PROFILE_NAME, None, None))
                    elif app_is_windowed:
                        self.q_send.put(ipc.ApplicationDetected(current_app[0], process_id, app_position))
                    else:
                        self.q_send.put(ipc.ApplicationDetected(current_app[0], process_id, None))

                self.previous_app = current_app

    def run(self) -> None:
        print('[Application Detection] Loaded.')

        try:
            while True:
                self._process_message(self.q_receive.get())

        except ExitRequest:
            print('[Application Detection] Shut down.')

        # Catch error after KeyboardInterrupt
        except EOFError:
            print('[Application Detection] Force shut down.')
            return

        except Exception as e:
            self.q_send.put(ipc.Traceback(e, traceback.format_exc()))
            print(f'[Application Detection] Error shut down: {e}')

        self.q_send.put(ipc.ProcessShutDownNotification(ipc.Target.AppDetection))
        print('[Application Detection] Sent process closed notification.')


def run(q_send: multiprocessing.Queue, q_receive: multiprocessing.Queue) -> None:
    AppDetection(q_send, q_receive).run()
