import os
import re

from mousetracks.applications import AppList, TRACKING_WILDCARD
from .. import ipc
from ..abstract import Component
from ...constants import DEFAULT_PROFILE_NAME
from ...exceptions import ExitRequest
from ...utils.win import WindowHandle, get_window_handle


class AppDetection(Component):
    """Application detection component.

    This is using legacy code for the time being, just to get an inital
    version out the door. I plan to improve it at some point.
    """

    def __post_init__(self) -> None:
        self.state = ipc.TrackingState.State.Pause

        self._applist = AppList()
        self._regex_cache: dict[str, re.Pattern] = {}
        self._previous_focus: tuple[str, str] = '', ''
        self._previous_app: tuple[str, str] | None = None
        self._previous_pos: tuple[int, int, int, int] | None = None
        self._previous_res: tuple[int, int] | None = None

    def check_running_app(self):
        hwnd = get_window_handle()
        handle = WindowHandle(hwnd)
        exe = handle.exe
        title = handle.title

        # Display focus changes
        current_focus: tuple[str, str] = (exe, title)
        if self._previous_focus != current_focus:
            self._previous_focus = current_focus
            print(f'[Application Detection] Focus changed: {exe} ({title})')

        # Use legacy code to detect for anything defined in AppList.txt
        current_app: tuple[str, str] | None = None
        try:
            names: list[str] = self._applist[os.path.basename(handle.exe)]
        except KeyError:
            pass
        else:
            try:
                current_app = names[title], exe

            except KeyError:
                for name in names:
                    if name is None:
                        continue
                    if TRACKING_WILDCARD in name:
                        if name not in self._regex_cache:
                            pattern = name.replace(TRACKING_WILDCARD, '(.*)')
                            self._regex_cache[name] = re.compile(pattern)
                        if self._regex_cache[name].search(title) is not None:
                            break
                    elif name == title:
                        break

                # If not match then use default profile
                else:
                    current_app = names[None], exe

        # Perform checks
        changed = False
        position = handle.position
        resolution = handle.size

        if current_app is not None:
            if current_app == self._previous_app:
                if resolution != self._previous_res:
                    changed = True
                    print(f'[Application Detection] {current_app[0]} resized: {self._previous_res} -> {resolution}')
                elif position != self._previous_pos:
                    changed = True
                    print(f'[Application Detection] {current_app[0]} moved: {self._previous_pos} -> {position}')
            else:
                changed = True
                print(f'[Application Detection] {current_app[0]} loaded')

        self._previous_pos = position
        self._previous_res = resolution

        # Somewhat hacky way to detect if the application is full screen spanning multiple monitors
        # If this is the case, we want to record both monitors as normal
        # TODO: Find an application to test this with before enabling
        app_is_windowed = True
        # if app_resolution is not None:
        #     x_min = x_max = y_min = y_max = 0
        #     for x1, y1, x2, y2 in monitor_locations():
        #         x_min = min(x_min, x1)
        #         x_max = max(x_max, x2)
        #         y_min = min(y_min, y1)
        #         y_max = max(y_max, y2)
        #     if (x_max - x_min, y_max - y_min) == app_resolution:
        #         app_is_windowed = False

        if current_app != self._previous_app:
            if self._previous_app is not None:
                print(f'[Application Detection] {self._previous_app[0]} lost focus')
                changed = True
            if current_app is not None:
                print(f'[Application Detection] {current_app[0]} gained focus')
                changed = True

        if changed:
            if current_app is None:
                print(ipc.ApplicationDetected(DEFAULT_PROFILE_NAME, None, None))
                self.send_data(ipc.ApplicationDetected(DEFAULT_PROFILE_NAME, None, None))
            elif app_is_windowed:
                print(ipc.ApplicationDetected(current_app[0], handle.pid, handle.rect))
                self.send_data(ipc.ApplicationDetected(current_app[0], handle.pid, handle.rect))
            else:
                print(ipc.ApplicationDetected(current_app[0], handle.pid, None))
                self.send_data(ipc.ApplicationDetected(current_app[0], handle.pid, None))

        self._previous_app = current_app

    def _process_message(self, message: ipc.Message) -> None:
        """Process an item of data."""
        match message:
            case ipc.TrackingState():
                self.state = message.state
                if self.state == ipc.TrackingState.State.Stop:
                    raise ExitRequest

            case ipc.RequestRunningAppCheck():
                self.check_running_app()

            case ipc.DebugRaiseError():
                raise RuntimeError('[Application Detection] Test Exception')

    def run(self):
        """Listen for events to process."""
        while True:
            self._process_message(self.receive_data())
