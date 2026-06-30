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
from .recording import open_recording, read_recording, write_event, RECORDED_MESSAGE_TYPES
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
        self._history: deque[tuple[int, ipc.Message]] = deque()
        self._current_tick = 0
        self._current_timestamp = 0
        self._history_length = 0
        self._components_loaded = False

    def run(self) -> None:
        if CTX.playback_file is not None:
            self._run_file_playback()
        self._cache_live_events()

    def _cache_live_events(self) -> None:
        """Cache messages from live tracking."""
        for message in self.receive_data(polling_rate=1 / UPDATES_PER_SECOND):
            match message:
                case ipc.Tick():
                    self._current_tick = message.tick
                    self._current_timestamp = message.timestamp

                    # Trim the history length if required
                    if self._history_length:
                        cutoff = message.tick - self._history_length
                        while self._history and self._history[0][0] < cutoff:
                            self._history.popleft()

                case ipc.SetHistoryLength():
                    self._history_length = message.ticks
                    if not message.ticks:
                        self._history.clear()

                case ipc.AllComponentsLoaded():
                    self._components_loaded = True

                case ipc.ExportHistory():
                    self._export_history(message.path, message.start_percentage, message.end_percentage)

                case ipc.StartPlayback():
                    oldest_tick = self._current_tick - self._history_length
                    start_tick = oldest_tick + round(message.start_percentage * self._history_length)
                    end_tick = oldest_tick + round(message.end_percentage * self._history_length)
                    snapshot = (
                        (tick, msg) for tick, msg in self._history
                        if start_tick <= tick <= end_tick and type(msg) in RECORDED_MESSAGE_TYPES
                    )
                    self._replay(snapshot)

                # Don't record these events to history
                case ipc.StopPlayback() | ipc.PausePlayback() | ipc.ResumePlayback(): ...

                case ipc.StopTracking() | ipc.Exit():
                    raise ExitRequest

                # Record all other events in the history queue
                case _ if self._history_length and message.source != ipc.Target.Playback:
                    self._history.append((self._current_tick, message))

    def _export_history(self, path: str, start_percentage: float, end_percentage: float) -> None:
        """Export a slice of the history to disk."""
        # Safety check - this shouldn't ever happen
        if not self._history or not self._history_length:
            print(f'[Playback] No history being recorded')
            return

        oldest_tick = self._current_tick - self._history_length
        start_tick = oldest_tick + round(start_percentage * self._history_length)
        end_tick = oldest_tick + round(end_percentage * self._history_length)

        # Filter events within the playback window
        events = [(tick, msg) for tick, msg in self._history
                  if start_tick <= tick <= end_tick and type(msg) in RECORDED_MESSAGE_TYPES]

        # Safety check - this shouldn't ever happen
        if not events:
            print(f'[Playback] No matching events found')
            return

        # Get the ticks and timestamps
        first_tick = events[0][0]
        last_tick = events[-1][0]
        first_timestamp = self._current_timestamp - (self._current_tick - first_tick) // UPDATES_PER_SECOND
        last_timestamp = first_timestamp + (last_tick - first_tick) // UPDATES_PER_SECOND

        # Write to file
        print(f'[Playback] Writing to {path}')
        with open_recording(path) as f:
            write_event(f, first_tick, ipc.Tick(first_tick, first_timestamp))
            for tick, msg in events:
                write_event(f, tick, msg)
            write_event(f, last_tick, ipc.Tick(last_tick, last_timestamp))

        # Notify the GUI it's saved
        print(f'[Playback] History saved to {path}')
        self.send_data(ipc.HistoryExported(path=path, duration_ticks=last_tick - first_tick))

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

        paused = stopped = False
        tick_offset = 0

        self.send_data(ipc.PlaybackStarted())

        # Use the tracking tick handler for a constant 60 ups
        for _tick in ticks(UPDATES_PER_SECOND):

            # Process any messages sent during the replay
            for message in self.receive_data():
                if message.source == ipc.Target.Playback:
                    continue
                match message:
                    case ipc.PausePlayback():
                        paused = True
                    case ipc.ResumePlayback():
                        paused = False
                    case ipc.StopTracking() | ipc.Exit():
                        raise ExitRequest
                    case ipc.AllComponentsLoaded():
                        self._components_loaded = True
                    case ipc.StopPlayback():
                        stopped = True

            # Handle exit / pause
            if stopped:
                break
            if paused or not self._components_loaded:
                tick_offset -= 1
                continue

            # Calculate the correct tick
            tick = _tick + tick_offset
            recorded_tick = start_tick + tick
            timestamp = start_timestamp + tick // UPDATES_PER_SECOND
            self.send_data(ipc.Tick(recorded_tick, timestamp))

            # Skip over empty ticks
            ticks_until_action = next_event[0] - recorded_tick - 1
            tick_offset += max(0, ticks_until_action)

            # Process events for the current tick
            while next_event is not None and next_event[0] <= recorded_tick:
                message = next_event[1]
                if isinstance(message, ipc.Tick):
                    start_timestamp = message.timestamp - tick // UPDATES_PER_SECOND
                self.send_data(message)
                next_event = next(stream, None)

            if next_event is None:
                break

        self.send_data(ipc.PlaybackFinishing())
        self.send_data(ipc.PlaybackFinished())
