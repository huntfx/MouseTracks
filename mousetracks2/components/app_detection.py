import re
import sys

import psutil

from . import ipc
from .abstract import Component
from ..applications import AppList, LOCAL_PATH
from ..constants import DEFAULT_PROFILE_NAME, TRACKING_IGNORE
from ..exceptions import ExitRequest

if sys.platform == 'win32':
    from ..utils.system.win32 import PID, WindowHandle, get_window_handle
    SUPPORTED = True
else:
    SUPPORTED = False


class AppDetection(Component):
    """Application detection component."""

    def __post_init__(self) -> None:
        self.applist = AppList()
        self.applist.save()
        self._regex_cache: dict[str, re.Pattern] = {}
        self._previous_focus: tuple[str, str] = '', ''
        self._previous_app: tuple[str, str] | None = None
        self._previous_pos: tuple[int, int] | None = None
        self._previous_res: tuple[int, int] | None = None
        self._previous_rects: list[tuple[int, int, int, int]] = []

    def _pid_fallback(self, title: str) -> PID:
        """Guess the PID of the selected application.
        It will search through all loaded applications without any
        window handles to determine if there's a match to anything that
        should be tracked. If so, it'll use the one with the highest
        PID, which indicates it's the most recently loaded.

        See the `WindowHandle` class for more details of why this is
        necessary. This method is not foolproof, and loading a new
        tracked application will cause that one to take priority even
        if it's not focused.
        """
        matched = PID(0)
        for proc in psutil.process_iter(attrs=['pid', 'exe']):
            pid = PID(proc.info['pid'])
            if proc.info['exe'] is None or pid.hwnds:
                continue
            if self.applist.match(proc.info['exe'], title):
                print(f'[Application Detection] Fallback matched "{proc.info["exe"]}" with PID {proc.info["pid"]}')
                matched = pid
        print(f'[Application Detection] Fallback returning PID {int(matched)}')
        return matched

    def check_running_app(self) -> None:
        if not SUPPORTED:
            return

        hwnd = get_window_handle()
        handle = WindowHandle(hwnd)
        title = handle.title
        pid = handle.pid
        if pid == 0:
            print('[Application Detection] PID returned 0, running fallback function...')
            pid = self._pid_fallback(title)

        exe = handle.pid.executable
        focus_changed = False

        # Display focus changes
        current_focus: tuple[str, str] = (exe, title)
        if self._previous_focus != current_focus:
            self._previous_focus = current_focus
            print(f'[Application Detection] Focus changed: {exe} ({title})')
            focus_changed = True

        # Determine if the current application is tracked
        current_app_name = self.applist.match(pid.executable, title)
        if current_app_name is None or current_app_name == TRACKING_IGNORE:
            current_app = None
            rects = []
        else:
            current_app = current_app_name, exe
            rects = pid.rects

        # Print out any changes
        position = pid.position
        resolution = pid.size
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

        if current_app != self._previous_app or rects != self._previous_rects:
            if current_app is None:
                self.send_data(ipc.TrackedApplicationDetected(DEFAULT_PROFILE_NAME, None))
            elif app_is_windowed:
                self.send_data(ipc.TrackedApplicationDetected(current_app[0], int(pid), pid.rects))
            else:
                self.send_data(ipc.TrackedApplicationDetected(current_app[0], int(pid)))

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

            case ipc.ReloadAppList():
                self.applist.load(LOCAL_PATH)
                print(f'[Application Detection] Successfully reloaded "{LOCAL_PATH}"')

    def run(self):
        """Listen for events to process."""
        for message in self.receive_data(polling_rate=0.25):
            self._process_message(message)
