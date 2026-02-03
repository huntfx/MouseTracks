from typing import Self

from ...utils import Rect, RectList

from AppKit import NSRunningApplication
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGWindowListExcludeDesktopElements,
    kCGNullWindowID,
    kCGWindowOwnerPID,
    kCGWindowBounds,
    kCGWindowName
)


class Window:
    """macOS implementation of the Window class."""

    def __init__(self, app_instance: NSRunningApplication, window_info: dict | None) -> None:
        self._app = app_instance
        self._window_info = window_info or {}  # Quartz CGWindowList
        self._pid = self._app.processIdentifier()

    @classmethod
    def get_focused(cls) -> Self:
        # Get list of windows ordered front-to-back
        # Exclude desktop icons to reduce noise
        options = kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements
        window_list = CGWindowListCopyWindowInfo(options, kCGNullWindowID)

        for w in window_list:
            # Layer 0 is the standard application layer.
            # This skips the Menu Bar, Dock, and Floating overlays.
            if w.get('kCGWindowLayer', 0) == 0:
                pid = w.get(kCGWindowOwnerPID)
                app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                return cls(app, w)

        return cls(None, None)

    @property
    def pid(self) -> int:
        return self._pid

    @pid.setter
    def pid(self, pid: int) -> None:
        self._pid = pid

    @property
    def title(self) -> str:
        """Get the window title."""
        # Note: On macOS Catalina+, getting the window title requires Screen Recording permissions.
        # If permission is missing, this may return an empty string or just the app name.
        if self._window_info and kCGWindowName in self._window_info:
            return self._window_info[kCGWindowName] or ''

        # Fallback to the application name
        return self._app.localizedName() or ''

    @property
    def executable(self) -> str:
        """Get the executable path."""
        if self._app and self._app.executableURL():
            return self._app.executableURL().path()
        return ""

    @property
    def rects(self) -> RectList:
        """Get window geometry."""
        x, y, w, h = 0, 0, 0, 0
        if self._window_info:
            bounds = self._window_info.get(kCGWindowBounds)
            if bounds:
                x = int(bounds['X'])
                y = int(bounds['Y'])
                w = int(bounds['Width'])
                h = int(bounds['Height'])

        return RectList([Rect.from_size(width=w, height=h, x=x, y=y)])

    @property
    def position(self) -> tuple[int, int]:
        return self.rects[0].position

    @property
    def size(self) -> tuple[int, int]:
        return self.rects[0].size
