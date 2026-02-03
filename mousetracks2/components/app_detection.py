from __future__ import annotations

import re
import sys
from collections import deque

import psutil

from . import ipc
from .abstract import Component
from ..applications import AppList, LOCAL_PATH
from ..constants import DEFAULT_PROFILE_NAME, TRACKING_IGNORE
from ..exceptions import ExitRequest
from ..types import RectList
from ..utils.system import Window


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
        self._previous_rects = RectList()
        self._fallback_title = ''
        self._fallback_pid = 0

        # Cache each process in case the fallback is required
        deque(psutil.process_iter(attrs=['pid', 'exe', 'create_time']), maxlen=0)

    def _pid_fallback(self, title: str) -> int:
        """Guess the PID of the selected application.
        It will search through all loaded applications without any
        window handles to determine if there's a match to anything that
        should be tracked. If so, it'll use the one with the highest
        PID, which indicates it's the most recently loaded.

        See the `WindowHandle` class for more details of why this is
        necessary. This method is not foolproof, and has been tweaked
        multiple times to try and make it work 100% of the time for the
        one use case I've come across.
        """
        from ..utils.system.win32 import PID

        matched_procs = []  # type: list[psutil.Process]
        invalid_exes = set()  # type: set[str]
        for proc in psutil.process_iter(attrs=['pid', 'exe', 'create_time']):
            pid = PID(proc.info['pid'])

            # Ignore if no executable
            if proc.info['exe'] is None:
                pass

            # If there are window handles, it's not valid for the callback
            elif pid.hwnds:
                invalid_exes.add(proc.info['exe'])

            # Check for a match
            elif proc.info['exe'] not in invalid_exes and self.applist.match(proc.info['exe'], title):
                print(f'[Application Detection] Fallback matched "{proc.info["exe"]}" with PID {proc.info["pid"]}')
                matched_procs.append(proc)

        # Sort by the latest creation time
        matched_procs.sort(key=lambda proc: proc.info['create_time'], reverse=True)

        # Find the first matched process without any valid hwnds
        for proc in matched_procs:
            if proc.info['exe'] not in invalid_exes:
                matched = proc.info['pid']
                break
        else:
            matched = 0

        print(f'[Application Detection] Fallback returning PID {matched}')
        return matched

    def check_running_app(self) -> None:
        window = Window.get_focused()
        title = window.title

        # Fallback is required
        if sys.platform == 'win32' and window.pid == 0 and title:
            # The title matches so reuse the match
            if title == self._fallback_title:
                window.pid = self._fallback_pid

            # Find a new match
            else:
                print(f'[Application Detection] PID returned 0 for an app with title "{title}",'
                      'running fallback function...')
                window.pid = self._fallback_pid = self._pid_fallback(title)
                self._fallback_title = title

        # Reset the fallback data
        else:
            self._fallback_pid = 0
            self._fallback_title = ''

        exe = window.executable
        focus_changed = False

        # Display focus changes
        current_focus: tuple[str, str] = (exe, title)
        if self._previous_focus != current_focus:
            self._previous_focus = current_focus
            print(f'[Application Detection] Focus changed: {exe} ({title})')
            focus_changed = True

        # Determine if the current application is tracked
        current_app_name = self.applist.match(exe, title)
        if current_app_name is None or current_app_name == TRACKING_IGNORE:
            current_app = None
            rects = RectList()
        else:
            current_app = current_app_name, exe
            rects = window.rects

        # Print out any changes
        position = window.position
        resolution = window.size
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
                self.send_data(ipc.TrackedApplicationDetected(current_app[0], window.pid, window.rects))
            else:
                self.send_data(ipc.TrackedApplicationDetected(current_app[0], window.pid))

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

    def run(self) -> None:
        """Listen for events to process."""
        for message in self.receive_data(polling_rate=0.25):
            self._process_message(message)
