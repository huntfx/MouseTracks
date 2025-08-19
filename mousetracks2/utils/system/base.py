"""Base functions for possible use in any OS.
Some of these are placeholders for use if a feature is missing support.
"""

import queue
import shlex
import threading
import time
from pathlib import Path
from typing import Any, Self

from screeninfo import get_monitors as _get_monitors

from ...constants import SYS_EXECUTABLE, IS_BUILT_EXE


def get_autostart() -> str | None:
    """Determine if running on startup."""
    raise NotImplementedError


def set_autostart(*args: str) -> None:
    """Set to run on startup."""


def remove_autostart() -> None:
    """Stop running on startup."""


def remap_autostart(cmd: str) -> bool:
    """Check if remaping the executable is required.
    This is in case a user downloads a new version.
    It is only meant to run for built executables.
    """
    if not IS_BUILT_EXE:
        return False
    exe, *args = shlex.split(cmd)
    if IS_BUILT_EXE and Path(exe).resolve() != Path(SYS_EXECUTABLE).resolve():
        print(f'Autostart path is outdated. Correcting "{exe}" to "{SYS_EXECUTABLE}".')
        set_autostart(*args)
        return True
    return False


def is_elevated() -> bool:
    """Check if the script is running with admin privileges."""
    return False


def relaunch_as_elevated() -> None:
    """Relaunch the script with admin privileges."""


def monitor_locations() -> list[tuple[int, int, int, int]]:
    """Get the bounds of each monitor.
    This uses the cross platform library `screeninfo`.

    Note: This should not be used on Windows as of `screeninfo-1.8.1`.
    It involves calls to `user32.GetDC`, which eventually results in a
    state where the whole PC starts to lag, presumably due to resources
    not being completely released. It seems to be an issue with the API
    call itself as `screeninfo` releases the handle correctly.
    """
    return [(mon.x, mon.y, mon.x + mon.width, mon.y + mon.height) for mon in _get_monitors()]


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
    def rects(self) -> list[tuple[int, int, int, int]]:
        return []

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


