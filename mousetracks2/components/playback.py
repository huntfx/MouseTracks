"""Playback component - caches live events for history playback, or replays a recording file.

In normal operation (no playback file) the component runs continuously, caching
incoming events into a history deque so they can be replayed later.

When launched with a recording file (--playback), it replays the stored events
back through the hub at the original tick rate instead.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable, Iterator

from . import ipc
from .abstract import MonitorComponent
from .recording import open_recording, read_recording, get_recording_length, write_event, RECORDED_MESSAGE_TYPES
from ..constants import UPDATES_PER_SECOND
from ..context import CTX
from ..exceptions import ExitRequest
from ..utils.system import hide_child_process
from ..utils.timing import ticks


class Playback(MonitorComponent):
    """Cache live events for history playback, or replay a .mtr recording."""

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
        self._seek_tick: int | None = None
        self._seek_tick_percentage: float | None = None
        self._seek_pos = 0
        self._stream_range: tuple[float, float] = (0.0, 1.0)
        self._playback_end_tick: int | None = None
        self._options = ipc.PlaybackOptions(ups=UPDATES_PER_SECOND, skip_empty_ticks=True,
                                            start_percentage=0.0, end_percentage=1.0)

    def run(self) -> None:
        if CTX.playback_file is not None:
            self._run_file_playback()
        self._cache_live_events()

    @property
    def history_length(self) -> int:
        """Get the actual history length in ticks."""
        if self._history:
            return self._current_tick - self._history[0][0]
        return 0

    def _filter_history(self, start_tick: int, end_tick: int) -> list[tuple[int, ipc.Message]]:
        """Get history messages from within a range."""
        return [(tick, msg) for tick, msg in self._history
                if start_tick <= tick <= end_tick and type(msg) in RECORDED_MESSAGE_TYPES]

    def _get_stream_and_ticks(self) -> tuple[Callable[[], Iterator[tuple[int, ipc.Message]]], int]:
        """Build a fresh stream and tick count from the current history options."""
        self._stream_range = (self._options.start_percentage, self._options.end_percentage)

        if self._history:
            first_tick = self._history[0][0]
            last_tick = self._playback_end_tick if self._playback_end_tick is not None else self._current_tick
            history_length = last_tick - first_tick
            start_tick = first_tick + round(self._options.start_percentage * history_length)
            end_tick = first_tick + round(self._options.end_percentage * history_length)

            if events := self._filter_history(start_tick, end_tick):
                return lambda: iter(events), events[-1][0] - events[0][0]

        return lambda: iter(()), 0

    def _load_history_stream(self) -> tuple[Callable[[], Iterator[tuple[int, ipc.Message]]], int] | None:
        """Build a replayable stream from the current history.

        Returns (get_stream, total_ticks) if events were found, else None.
        """
        get_stream, total_ticks = self._get_stream_and_ticks()
        if total_ticks:
            return get_stream, total_ticks
        return None

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
                    self._playback_end_tick = self._current_tick
                    if stream_data := self._load_history_stream():
                        get_stream, total_ticks = stream_data
                        self._replay(get_stream, total_ticks)

                case ipc.SeekPlayback():
                    if self._playback_end_tick is None:
                        self._playback_end_tick = self._current_tick
                    if stream_data := self._load_history_stream():
                        get_stream, total_ticks = stream_data
                        self._seek_tick = round(message.percentage * total_ticks)
                        self._seek_pos = 0
                        self._replay(get_stream, total_ticks, paused=True)
                    else:
                        self.send_data(ipc.SeekComplete())

                # Don't record these events to history
                case ipc.StopPlayback() | ipc.PausePlayback() | ipc.ResumePlayback(): ...

                # If just caching, then progress is always at 100%
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
        events = self._filter_history(start_tick, end_tick)

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
        total_ticks = get_recording_length(path)
        self._replay(lambda: read_recording(path), total_ticks)

    def _iter_ticks(self) -> Iterator[int]:
        """Yield a continuously incrementing tick count.

        Seeking forwards will remove the sleep between ticks.
        Seeking backwards will jump back to 0 and fast forward.
        """
        offset = 1
        yield 0
        while True:
            ups = self._options.ups or 5  # Keep iterating even when UPS set to 0
            break_required = False

            for tick in ticks(ups):
                if break_required:
                    break

                yield tick + offset

                # Break on the next loop if the user has changed playback speed
                if self._options.ups != ups:
                    offset += tick + 1
                    break_required = True

                # Seek to a certain percentage of the total ticks
                elif self._seek_tick is not None:
                    try:
                        while self._seek_pos <= self._seek_tick:
                            yield self._seek_pos
                            self._seek_pos += 1
                        offset = self._seek_tick - tick

                    finally:
                        self._seek_tick = None
                        self.send_data(ipc.SeekComplete())

    def _replay(self, get_stream: Callable[[], Iterator[tuple[int, ipc.Message]]],
                total_ticks: int, paused: bool = False) -> None:
        """Replay events from a stream factory at the live tick rate."""
        stream: Iterator[tuple[int, ipc.Message]] = iter(())
        next_event = None
        start_tick = recorded_tick = 0
        start_timestamp = int(time.time())
        is_rendering = False

        for i, _tick in enumerate(self._iter_ticks()):

            # Initialise the stream on the first tick, or restart it on a backward seek
            if not _tick:
                # Rebuild the stream if the range is changed
                if self._seek_tick_percentage is not None:
                    get_stream, total_ticks = self._get_stream_and_ticks()
                    self._seek_tick = round(self._seek_tick_percentage * total_ticks)
                    self._seek_tick_percentage = None

                # Setup the stream to use in the loop
                stream = get_stream()
                next_event = next(stream, None)
                if next_event is None:
                    break
                start_tick = recorded_tick = next_event[0]
                start_timestamp = int(time.time())
                tick_offset = 0

                # Reset render data then set up monitor and profile state
                if i:
                    self.send_data(ipc.PlaybackRestarted())
                else:
                    self.send_data(ipc.PlaybackStarted(paused=paused))

                self.send_data(self._last_monitors_changed or ipc.MonitorsChanged(data=self._monitor_data))
                if self._last_profile_changed is not None:
                    self.send_data(self._last_profile_changed)

            # Process any messages sent during the replay
            continue_required = break_required = False
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

                    case ipc.PlaybackOptions():
                        self._options = message

                    case ipc.StopPlayback():
                        break_required = True

                    case ipc.SeekPlayback():
                        actual_tick, tick_offset = _tick + tick_offset, 0
                        continue_required = True  # Skip the current tick

                        current_range = (self._options.start_percentage, self._options.end_percentage)
                        if current_range != self._stream_range:
                            self._seek_tick_percentage = message.percentage
                            self._seek_tick = self._seek_pos = 0

                        else:
                            self._seek_tick = round(message.percentage * total_ticks)
                            # Backward seek
                            if self._seek_tick < actual_tick:
                                self._seek_pos = 0
                            # Forward seek
                            else:
                                self._seek_pos = actual_tick + 1

                    case ipc.PlaybackResumeRender():
                        is_rendering = False

                    case ipc.RequestPlaybackProgress():
                        if total_ticks:
                            self.send_data(ipc.PlaybackProgress(min(1.0, (recorded_tick - start_tick) / total_ticks)))
                        else:
                            self.send_data(ipc.PlaybackProgress(1.0))

            if break_required:
                break
            if continue_required:
                continue

            # Undo tick increments when not actively playing back
            _paused = paused or is_rendering or not self._components_loaded or not self._options.ups
            if _paused and self._seek_tick is None:
                tick_offset -= 1
                continue

            # Calculate the correct tick
            tick = _tick + tick_offset
            recorded_tick = start_tick + tick
            timestamp = start_timestamp + round(tick // UPDATES_PER_SECOND)
            self.send_data(ipc.Tick(recorded_tick, timestamp))

            # Skip over empty ticks to avoid waiting on them
            if self._seek_tick is None:
                assert next_event is not None  # Keep mypy happy
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
                    is_rendering = True

                self.send_data(message)
                next_event = next(stream, None)

            if next_event is None:
                break

        self.send_data(ipc.PlaybackFinished())
