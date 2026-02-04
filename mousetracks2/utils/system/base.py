"""Base functions for possible use in any OS.
Some of these are placeholders for use if a feature is missing support.
"""

import queue
import threading
import time
from pathlib import Path
from typing import Any, Self

from screeninfo import get_monitors as _get_monitors

from ...types import Rect, RectList


SUPPORTS_TRAY = True


def get_autostart() -> str | None:
    """Determine if running on startup."""
    raise NotImplementedError


def set_autostart(*args: str, ignore_args: tuple[str, ...] = ()) -> None:
    """Set to run on startup."""


def remove_autostart() -> None:
    """Stop running on startup."""


def is_elevated() -> bool:
    """Check if the script is running with admin privileges."""
    return False


def relaunch_as_elevated() -> None:
    """Relaunch the script with admin privileges."""


def monitor_locations(dpi_aware: bool = False) -> RectList:
    """Get the bounds of each monitor.
    This uses the cross platform library `screeninfo`.

    Note: This should not be used on Windows as of `screeninfo-1.8.1`.
    It involves calls to `user32.GetDC`, which eventually results in a
    state where the whole PC starts to lag, presumably due to resources
    not being completely released. It seems to be an issue with the API
    call itself as `screeninfo` releases the handle correctly.
    """
    return RectList(Rect.from_size(width=mon.width, height=mon.height, x=mon.x, y=mon.y)
                    for mon in _get_monitors())


class Window:
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    @classmethod
    def get_focused(cls) -> Self:
        return cls()

    @property
    def pid(self) -> int:
        return 0

    @pid.setter
    def pid(self, pid: int) -> None: ...

    @property
    def title(self) -> str:
        return ''

    @property
    def executable(self) -> str:
        return ''

    @property
    def rects(self) -> RectList:
        return RectList()

    @property
    def position(self) -> tuple[int, int]:
        return (0, 0)

    @property
    def size(self) -> tuple[int, int]:
        return (0, 0)


class MonitorEventsListener(threading.Thread):
    """Listen for monitor change events.

    The most basic implementation is to check every second for changes.
    If an operating system has hooks then this class can be subclassed.

    The initial event is triggered on startup.
    """

    def __init__(self) -> None:
        super().__init__(name='MonitorEventsListener', daemon=True)
        self._queue = queue.Queue()  # type: queue.Queue[None]
        self._running = True

    def run(self) -> None:
        while self._running:
            self.trigger()
            time.sleep(1)

    def stop(self) -> None:
        """Stops the thread."""
        self._running = False

    def trigger(self) -> None:
        """Trigger the event."""
        self._queue.put(None)

    @property
    def triggered(self) -> bool:
        """Determine if any event was set."""
        count = 0
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                return count > 0
            count += 1


def hide_child_process() -> None:
    """This is here to allow macOS to hide the child processes."""


def prepare_application_icon(icon_path: Path | str) -> None:
    """This runs in the GUI process."""
