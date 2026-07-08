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
from .abstract import MonitorComponent
from .recording import open_recording, read_recording, get_recording_length, write_event, RECORDED_MESSAGE_TYPES
from ..constants import UPDATES_PER_SECOND
from ..context import CTX
from ..exceptions import ExitRequest
from ..utils.system import hide_child_process
from ..utils.timing import ticks


class Playback(MonitorComponent):
    """Cache live events for history playback, or replay a .jsonl.gz recording."""

    target = ipc.Target.Playback

    def __post_init__(self) -> None:
        hide_child_process()
        self._history: deque[tuple[int, ipc.Message]] = deque()
        self._current_tick = 0
        self._current_timestamp = 0
        self._history_length = 0
        self._components_loaded = False
        self._last_monitors_changed: ipc.MonitorsChanged | None = None
        self._last_profile_changed: ipc.CurrentProfileChanged | None = None
        self._options = ipc.PlaybackOptions(ups=UPDATES_PER_SECOND, skip_empty_ticks=True,
                                            start_percentage=0.0, end_percentage=1.0)

    def run(self) -> None:
        if CTX.playback_file is not None:
            self._run_file_playback()
        self._cache_live_events()

    @property
    def history_length(self) -> int:
        """Get the actual history length in ticks."""
        if not self._history:
            return 0
        return self._current_tick - self._history[0][0]

    def _cache_live_events(self) -> None:
        """Cache messages from live tracking."""
        for message in self.receive_data(polling_rate=1 / UPDATES_PER_SECOND):
            if message.source == ipc.Target.Playback:
                continue
            match message:
                case ipc.Tick():
                    self._current_tick = message.tick
                    self._current_timestamp = message.timestamp

                    # Trim the history length if required
                    if self._history_length:
                        cutoff = message.tick - self._history_length
                        while self._history and self._history[0][0] < cutoff:
                            _, pruned = self._history.popleft()
                            match pruned:
                                case ipc.MonitorsChanged():
                                    self._last_monitors_changed = pruned
                                case ipc.CurrentProfileChanged():
                                    self._last_profile_changed = pruned

                case ipc.SetHistoryLength():
                    self._history_length = message.ticks
                    if not message.ticks:
                        self._history.clear()

                case ipc.AllComponentsLoaded():
                    self._components_loaded = True

                case ipc.ExportHistory():
                    self._export_history(message.path, message.start_percentage, message.end_percentage)

                case ipc.PlaybackOptions():
                    self._options = message

                case ipc.StartPlayback():
                    self._options = message.options
                    oldest_tick = self._current_tick - self._history_length
                    start_tick = oldest_tick + round(self._options.start_percentage * self._history_length)
                    end_tick = oldest_tick + round(self._options.end_percentage * self._history_length)
                    events = [
                        (tick, msg) for tick, msg in self._history
                        if start_tick <= tick <= end_tick and type(msg) in RECORDED_MESSAGE_TYPES
                    ]
                    tick_count = (events[-1][0] - events[0][0]) if events else 0
                    self._replay(iter(events), tick_count)

                # Don't record these events to history
                case ipc.StopPlayback() | ipc.PausePlayback() | ipc.ResumePlayback(): ...

                # Prevent this being recorded too, but also update the GUI
                case ipc.RequestPlaybackProgress():
                    self.send_data(ipc.PlaybackProgress(1.0))

                case ipc.StopTracking() | ipc.Exit():
                    raise ExitRequest

                case ipc.MonitorsChanged():
                    self.set_monitor_data(message.data)
                    if self._last_monitors_changed is None:
                        self._last_monitors_changed = message
                    if self._history_length:
                        self._history.append((self._current_tick, message))

                case ipc.CurrentProfileChanged():
                    if self._last_profile_changed is None:
                        self._last_profile_changed = message
                    if self._history_length:
                        self._history.append((self._current_tick, message))

                case ipc.RequestHistoryLength():
                    self.send_data(ipc.HistoryLength(self.history_length))

                # Record all other events in the history queue
                case _ if self._history_length:
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
        first_timestamp = self._current_timestamp - round((self._current_tick - first_tick) // UPDATES_PER_SECOND)
        last_timestamp = first_timestamp + round((last_tick - first_tick) // UPDATES_PER_SECOND)

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
        path = str(CTX.playback_file)
        self._replay(read_recording(path), get_recording_length(path))

    def _iter_ticks(self) -> Iterator[int]:
        """Yield a continuously incrementing tick count, restarting ticks() when speed changes."""
        offset = 1
        yield 0
        while True:
            ups = self._options.ups or 5
            break_required = False

            for tick in ticks(ups):
                if break_required:
                    break

                yield tick + offset

                # Catch if the user has changed playback speed
                # To account for the final pause, break on next loop
                if self._options.ups != ups:
                    offset += tick + 1
                    break_required = True

    def _replay(self, stream: Iterator[tuple[int, ipc.Message]], total_ticks: int) -> None:
        """Replay events from an iterator of (tick, message) pairs at the live tick rate."""
        next_event = next(stream, None)
        if next_event is None:
            return
        start_tick = recorded_tick = next_event[0]
        start_timestamp = int(time.time())

        pause_manual = stopped = False
        pause_render: bool | None = False
        tick_offset = 0

        self.send_data(ipc.PlaybackStarted())

        # Start with the correct monitor and profile setup
        self.send_data(self._last_monitors_changed or ipc.MonitorsChanged(data=self._monitor_data))
        if self._last_profile_changed is not None:
            self.send_data(self._last_profile_changed)

        # Use the tracking tick handler for a constant 60 ups
        for _tick in self._iter_ticks():

            # Process any messages sent during the replay
            for message in self.receive_data():
                if message.source == ipc.Target.Playback:
                    continue
                match message:
                    case ipc.PausePlayback():
                        pause_manual = True
                    case ipc.ResumePlayback():
                        pause_manual = False
                    case ipc.StopTracking() | ipc.Exit():
                        raise ExitRequest
                    case ipc.AllComponentsLoaded():
                        self._components_loaded = True
                    case ipc.PlaybackOptions():
                        self._options = message
                    case ipc.StopPlayback():
                        stopped = True
                    case ipc.PlaybackResumeRender():
                        pause_render = False
                    case ipc.RequestPlaybackProgress():
                        if total_ticks:
                            self.send_data(ipc.PlaybackProgress((recorded_tick - start_tick) / total_ticks))
                        else:
                            self.send_data(ipc.PlaybackProgress(1.0))

            # Handle exit / pause
            if stopped:
                break
            if pause_manual or pause_render or not self._components_loaded or not self._options.ups:
                tick_offset -= 1
                continue

            # Calculate the correct tick
            tick = _tick + tick_offset
            recorded_tick = start_tick + tick
            timestamp = start_timestamp + round(tick // UPDATES_PER_SECOND)
            self.send_data(ipc.Tick(recorded_tick, timestamp))

            # Skip over empty ticks
            ticks_until_action = next_event[0] - recorded_tick - 1
            tick_offset += max(0, ticks_until_action)

            # Process events for the current tick
            while next_event is not None and next_event[0] <= recorded_tick:
                message = next_event[1]

                # Set the correct timestamp if a tick is sent
                if isinstance(message, ipc.Tick):
                    start_timestamp = message.timestamp - round(tick // UPDATES_PER_SECOND)

                # Don't continue with profile switch until render is complete
                elif isinstance(message, ipc.CurrentProfileChanged):
                    pause_render = True

                self.send_data(message)
                next_event = next(stream, None)

            if next_event is None:
                break

        self.send_data(ipc.PlaybackFinished())
