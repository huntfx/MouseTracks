import plistlib
import shlex
from contextlib import suppress
from pathlib import Path
from typing import Self

from .base import Window as _Window
from ...constants import SYS_EXECUTABLE, PACKAGE_IDENTIFIER
from ...types import Rect, RectList

from AppKit import (  # type: ignore
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSRunningApplication,
)
from Quartz import (  # type: ignore
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGWindowListExcludeDesktopElements,
    kCGNullWindowID,
    kCGWindowOwnerPID,
    kCGWindowBounds,
    kCGWindowName,
)


SUPPORTS_TRAY = False  # Causes bugs when restoring

AUTOSTART_DIR = Path.home() / 'Library' / 'LaunchAgents'
AUTOSTART_FILE_PATH = AUTOSTART_DIR / f'{PACKAGE_IDENTIFIER}.plist'


class Window(_Window):
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
        return ''

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


def get_autostart() -> str | None:
    """Determine if running on startup by checking the LaunchAgent plist."""
    if not AUTOSTART_FILE_PATH.exists():
        return None

    try:
        with open(AUTOSTART_FILE_PATH, 'rb') as f:
            plist = plistlib.load(f)

        args = plist.get('ProgramArguments', [])
        return shlex.join(args)

    except (OSError, plistlib.InvalidFileException):
        return None


def set_autostart(*args: str, ignore_args: tuple[str, ...] = ()) -> None:
    """Set an executable to run on startup using a LaunchAgent."""
    program_args = [SYS_EXECUTABLE] + [arg for arg in args if arg not in ignore_args]

    plist_content = {
        'Label': PACKAGE_IDENTIFIER,
        'ProgramArguments': program_args,
        'RunAtLoad': True,
        # Optional: 'ProcessType': 'Interactive'
    }

    try:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUTOSTART_FILE_PATH, 'wb') as f:
            plistlib.dump(plist_content, f)

    except OSError as e:
        print(f'Error: Could not set autostart: {e}')


def remove_autostart() -> None:
    """Stop an executable running on startup."""
    with suppress(FileNotFoundError):
        AUTOSTART_FILE_PATH.unlink()


def hide_child_process() -> None:
    """Hide the child process from the dock."""
    NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)


def prepare_application_icon(icon_path: Path | str) -> None:
    """Prepare the icon to be shown."""
    icon_image = NSImage.alloc().initWithContentsOfFile_(str(Path(icon_path).resolve()))
    if icon_image:
        NSApplication.sharedApplication().setApplicationIconImage_(icon_image)
