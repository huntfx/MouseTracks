"""Playback component - caches live events for history playback, or replays a recording file.

In normal operation (no playback file) the component runs continuously, caching
incoming events into a history deque so they can be replayed later.

When launched with a recording file (--playback), it replays the stored events
back through the hub at the original tick rate instead.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Iterator

from . import ipc
from .abstract import Component
from .recording import read_recording
from ..constants import UPDATES_PER_SECOND
from ..context import CTX
from ..exceptions import ExitRequest
from ..utils.system import hide_child_process
from ..utils.timing import ticks


class Playback(Component):
    """Cache live events for history playback, or replay a .jsonl.gz recording."""

    target = ipc.Target.Playback

    def __post_init__(self) -> None:
        hide_child_process()
        self._is_playing_back = CTX.playback_file is not None
        self._history: deque[tuple[int, ipc.Message]] = deque()
        self._current_tick = 0
        self._history_length = 0

    def run(self) -> None:
        if CTX.playback_file is not None:
            self._run_file_playback()
        else:
            self._run_cache()

    def _run_cache(self) -> None:
        """Cache events from live tracking for history playback."""
        for message in self.receive_data(polling_rate=1 / UPDATES_PER_SECOND):
            match message:
                case ipc.Tick():
                    self._current_tick = message.tick
                    if self._history_length:
                        cutoff = message.tick - self._history_length
                        while self._history and self._history[0][0] < cutoff:
                            self._history.popleft()

                case ipc.SetHistoryLength():
                    self._history_length = message.ticks
                    if not message.ticks:
                        self._history.clear()

                case ipc.StopTracking() | ipc.Exit():
                    raise ExitRequest

                case _:
                    if self._history_length and not self._is_playing_back:
                        self._history.append((self._current_tick, message))

    def _run_file_playback(self) -> None:
        """Replay a recording file."""
        if CTX.playback_file is None:
            return
        self._replay(read_recording(str(CTX.playback_file)))

    def _replay(self, stream: Iterator[tuple[int, ipc.Message]]) -> None:
        """Replay events from an iterator of (tick, message) pairs at the live tick rate."""
        next_event = next(stream, None)
        if next_event is None:
            return
        start_tick = next_event[0]
        start_timestamp = int(time.time())

        paused = ready = False
        tick_offset = 0

        self.send_data(ipc.StartPlayback())

        for _tick in ticks(UPDATES_PER_SECOND):
            for message in self.receive_data():
                match message:
                    case ipc.PauseTracking():
                        paused = True
                    case ipc.StartTracking():
                        paused = False
                        self.send_data(ipc.TrackingStarted())
                    case ipc.StopTracking() | ipc.Exit():
                        raise ExitRequest
                    case ipc.AllComponentsLoaded():
                        ready = True

            if paused or not ready:
                tick_offset += 1
                continue

            tick = _tick - tick_offset
            recorded_tick = start_tick + tick
            timestamp = start_timestamp + tick // UPDATES_PER_SECOND
            self.send_data(ipc.Tick(recorded_tick, timestamp))

            while next_event is not None and next_event[0] <= recorded_tick:
                message = next_event[1]
                if isinstance(message, ipc.Tick):
                    start_timestamp = message.timestamp - tick // UPDATES_PER_SECOND
                self.send_data(message)
                next_event = next(stream, None)

            if next_event is None:
                break

        self.send_data(ipc.StopPlayback())
        self.send_data(ipc.PauseTracking())
