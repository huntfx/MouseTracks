import re

from .. import ipc
from ..abstract import Component
from ...applications import AppList
from ...constants import DEFAULT_PROFILE_NAME, TRACKING_IGNORE
from ...exceptions import ExitRequest
from ...utils.system.win32 import WindowHandle, get_window_handle



class AppDetection(Component):
    """Application detection component."""

    def __post_init__(self) -> None:
        self.applist = AppList()
        self._regex_cache: dict[str, re.Pattern] = {}
        self._previous_focus: tuple[str, str] = '', ''
        self._previous_app: tuple[str, str] | None = None
        self._previous_pos: tuple[int, int] | None = None
        self._previous_res: tuple[int, int] | None = None
        self._previous_rects: list[tuple[int, int, int, int]] = []

    def check_running_app(self) -> None:
        hwnd = get_window_handle()
        handle = WindowHandle(hwnd)
        exe = handle.pid.executable
        title = handle.title
        focus_changed = False

        # Display focus changes
        current_focus: tuple[str, str] = (exe, title)
        if self._previous_focus != current_focus:
            self._previous_focus = current_focus
            print(f'[Application Detection] Focus changed: {exe} ({title})')
            focus_changed = True

        # Determine if the current application is tracked
        current_app_name = self.applist.match(handle.pid.executable, title)
        if current_app_name is None or current_app_name == TRACKING_IGNORE:
            current_app = None
        else:
            current_app = current_app_name, exe

        # Print out any changes
        position = handle.pid.position
        resolution = handle.pid.size
        if current_app is not None:
            if current_app == self._previous_app:
                if resolution != self._previous_res:
                    print(f'[Application Detection] {current_app[0]} resized: {self._previous_res} -> {resolution}')
                elif position != self._previous_pos:
                    print(f'[Application Detection] {current_app[0]} moved: {self._previous_pos} -> {position}')
            else:
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
            if current_app is not None:
                print(f'[Application Detection] {current_app[0]} gained focus')

        rects = handle.pid.rects
        if current_app != self._previous_app or rects != self._previous_rects:
            if current_app is None:
                self.send_data(ipc.TrackedApplicationDetected(DEFAULT_PROFILE_NAME, None))
            elif app_is_windowed:
                self.send_data(ipc.TrackedApplicationDetected(current_app[0], int(handle.pid), handle.pid.rects))
            else:
                self.send_data(ipc.TrackedApplicationDetected(current_app[0], int(handle.pid)))

        self._previous_app = current_app
        self._previous_rects = rects

        if focus_changed:
            self.send_data(ipc.ApplicationFocusChanged(exe, title, current_app is not None))

    def _process_message(self, message: ipc.Message) -> None:
        """Process an item of data."""
        match message:
            case ipc.StopTracking() | ipc.Exit():
                raise ExitRequest

            case ipc.RequestRunningAppCheck():
                self.check_running_app()

            case ipc.DebugRaiseError():
                raise RuntimeError('[Application Detection] Test Exception')

    def run(self):
        """Listen for events to process."""
        for message in self.receive_data(blocking=True):
            self._process_message(message)
