"""Playback component - caches live events for history playback, or replays a recording file.

In normal operation (no playback file) the component runs continuously, caching
incoming events into a history deque so they can be replayed later.

When launched with a recording file (a .mtr file dropped onto the executable),
it replays the stored events back through the hub at the original tick rate instead.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Callable, Iterable, Iterator

from . import ipc
from .abstract import MonitorComponent
from .recording import (open_recording, read_recording, get_recording_range, write_event,
                        LiveState, RECORDED_MESSAGE_TYPES)
from ..constants import UPDATES_PER_SECOND
from ..context import CTX
from ..exceptions import ExitRequest
from ..utils.system import hide_child_process
from ..utils.timing import ticks


# Message types to exclude from the "skip if idle" option
IMPORTANT_MESSAGE_TYPES: frozenset[type] = frozenset({
    ipc.MouseMove,
    ipc.MouseClick,
    ipc.MouseHeld,
    ipc.KeyPress,
    ipc.KeyHeld,
    ipc.ButtonPress,
    ipc.ButtonHeld,
    ipc.ThumbstickMove,
})


class _SkippableEventStream:
    """Wrap an event stream to allow looking ahead."""

    def __init__(self, source: Iterator[tuple[int, ipc.Message]]) -> None:
        self._source = source
        self._buffer: deque[tuple[int, ipc.Message]] = deque()

    def __iter__(self) -> Iterator[tuple[int, ipc.Message]]:
        return self

    def __next__(self) -> tuple[int, ipc.Message]:
        if self._buffer:
            return self._buffer.popleft()
        return next(self._source)

    def next_active_tick(self, current: tuple[int, ipc.Message]) -> int:
        """Find the tick of the next event worth waiting for."""
        tick, message = current
        while type(message) not in IMPORTANT_MESSAGE_TYPES:
            event = next(self._source, None)
            if event is None:
                return tick
            self._buffer.append(event)
            tick, message = event
        return tick


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
        self._last_state = LiveState()
        self._seek_tick: int | None = None
        self._seek_tick_percentage: float | None = None
        self._seek_pos = 0
        self._stream_range: tuple[float, float] = (0.0, 1.0)
        self._playback_end_tick: int | None = None
        self._active_file: str | None = None
        self._active_file_first_tick = 0
        self._active_file_total_ticks = 0
        self._options = ipc.PlaybackOptions(ups=UPDATES_PER_SECOND, skip_empty_ticks=True,
                                            start_percentage=0.0, end_percentage=1.0)

    def run(self) -> None:
        if CTX.playback_file is not None:
            self._play_recording_file(str(CTX.playback_file))
        self._cache_live_events()

    @property
    def history_length(self) -> int:
        """Get the actual history length in ticks."""
        if self._active_file is not None:
            return self._active_file_total_ticks
        if self._history:
            return self._current_tick - self._history[0][0]
        return 0

    def _iter_events_with_state(self, source: Iterable[tuple[int, ipc.Message]],
                                start_tick: int, end_tick: int,
                                ) -> Iterator[tuple[int, ipc.Message]]:
        """Iterate events within the start and end tick.

        The initial states (monitor/profile/cursor/thumbstick) are set
        before any other messages are sent.
        """
        state_copy = LiveState(monitors=self._last_state.monitors, profile=self._last_state.profile,
                               mouse=self._last_state.mouse, thumbsticks=dict(self._last_state.thumbsticks))

        injected = False
        for tick, message in source:
            if tick > end_tick:
                break

            if tick < start_tick:
                state_copy.update(message)
                continue

            if not injected:
                for state_message in state_copy:
                    yield start_tick, state_message
                injected = True

            yield tick, message

        # The range had no events of its own, so send the state
        if not injected:
            for state_message in state_copy:
                yield start_tick, state_message

    def _filter_history(self, start_tick: int, end_tick: int) -> list[tuple[int, ipc.Message]]:
        """Get history messages from within a range."""
        source = read_recording(self._active_file) if self._active_file is not None else self._history
        return [(tick, msg) for tick, msg in self._iter_events_with_state(source, start_tick, end_tick)
                if type(msg) in RECORDED_MESSAGE_TYPES]

    def _get_stream_and_ticks(self) -> tuple[Callable[[], _SkippableEventStream], int]:
        """Build a fresh stream and tick count from the current history options."""
        self._stream_range = (self._options.start_percentage, self._options.end_percentage)

        if self._active_file is not None:
            path = self._active_file
            first_tick = self._active_file_first_tick
            start_tick = first_tick + round(self._options.start_percentage * self._active_file_total_ticks)
            end_tick = first_tick + round(self._options.end_percentage * self._active_file_total_ticks)

            def get_stream() -> _SkippableEventStream:
                return _SkippableEventStream(self._iter_events_with_state(read_recording(path), start_tick, end_tick))

            return get_stream, end_tick - start_tick

        if self._history:
            first_tick = self._history[0][0]
            last_tick = self._playback_end_tick if self._playback_end_tick is not None else self._current_tick
            history_length = last_tick - first_tick
            start_tick = first_tick + round(self._options.start_percentage * history_length)
            end_tick = first_tick + round(self._options.end_percentage * history_length)

            if events := self._filter_history(start_tick, end_tick):
                return lambda: _SkippableEventStream(iter(events)), events[-1][0] - events[0][0]

        return lambda: _SkippableEventStream(iter(())), 0

    def _load_history_stream(self) -> tuple[Callable[[], _SkippableEventStream], int] | None:
        """Build a replayable stream from the current history.

        Returns (get_stream, total_ticks) if events were found, else None.
        """
        get_stream, total_ticks = self._get_stream_and_ticks()
        if total_ticks:
            return get_stream, total_ticks
        return None

    def _cache_live_events(self) -> None:
        """Cache messages from live tracking.

        Certain state events are cached so that playback can read them
        back first. This is handled in two parts. The first is during
        live caching, in that when history is pruned, the states will
        update. However, if history is disabled or not yet loaded, then
        any events received will immediately update the state.
        """
        for message in self.receive_data(polling_rate=1 / UPDATES_PER_SECOND):
            if message.source == ipc.Target.Playback:
                continue
            match message:
                case ipc.Tick():
                    self._current_tick = message.tick
                    self._current_timestamp = message.timestamp

                    # Trim the history length
                    cutoff = message.tick - self._history_length
                    while self._history and self._history[0][0] < cutoff:
                        _, pruned = self._history.popleft()
                        self._last_state.update(pruned)

                case ipc.SetHistoryLength():
                    self._history_length = message.ticks

                case ipc.AllComponentsLoaded():
                    self._components_loaded = True

                case ipc.ExportHistory():
                    self._export_history(message.path, message.start_percentage, message.end_percentage)

                case ipc.PlaybackOptions():
                    self._options = message

                case ipc.StartPlayback():
                    self._active_file = None
                    self._options = message.options
                    self._playback_end_tick = self._current_tick
                    if stream_data := self._load_history_stream():
                        get_stream, total_ticks = stream_data
                        self._replay(get_stream, total_ticks)

                case ipc.PlayRecordingFile():
                    self._play_recording_file(message.path)

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

                case ipc.StopPlayback():
                    self._active_file = None

                # Don't record these events to history
                case ipc.PausePlayback() | ipc.ResumePlayback(): ...

                # If just caching, then progress is always at 100%
                case ipc.RequestPlaybackProgress():
                    self.send_data(ipc.PlaybackProgress(1.0))

                case ipc.StopTracking() | ipc.Exit():
                    raise ExitRequest

                case ipc.MonitorsChanged():
                    self.set_monitor_data(message.data)
                    if self._history_length and self._components_loaded:
                        self._history.append((self._current_tick, message))
                    else:
                        self._last_state.update(message)

                case ipc.CurrentProfileChanged():
                    if self._history_length and self._components_loaded:
                        self._history.append((self._current_tick, message))
                    else:
                        self._last_state.update(message)

                case ipc.RequestHistoryLength():
                    self.send_data(ipc.HistoryLength(self.history_length))

                # Record all other events in the history queue
                case _:
                    if self._history_length and self._components_loaded:
                        self._history.append((self._current_tick, message))
                    else:
                        self._last_state.update(message)

    def _export_history(self, path: str, start_percentage: float, end_percentage: float) -> None:
        """Export a slice of the history to disk."""
        if self._active_file is None:
            first_tick = self._history[0][0] if self._history else self._current_tick
            total_ticks = self._current_tick - first_tick
        else:
            first_tick = self._active_file_first_tick
            total_ticks = self._active_file_total_ticks

        start_tick = first_tick + round(start_percentage * total_ticks)
        end_tick = first_tick + round(end_percentage * total_ticks)

        # Filter events within the playback window
        events = self._filter_history(start_tick, end_tick)
        if not events:
            print(f'[Playback] No matching events found')
            return

        # Get the ticks and timestamps
        first_tick = events[0][0]
        last_tick = events[-1][0]
        if self._active_file is None:
            first_timestamp = self._current_timestamp - round((self._current_tick - first_tick) / UPDATES_PER_SECOND)
            last_timestamp = first_timestamp + round((last_tick - first_tick) / UPDATES_PER_SECOND)
        else:
            first_timestamp = round(first_tick / UPDATES_PER_SECOND)
            last_timestamp = round(last_tick / UPDATES_PER_SECOND)

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

    def _play_recording_file(self, path: str) -> None:
        """Replay a recording file, whether triggered on startup or elsewhere."""
        first_tick, last_tick = get_recording_range(path)
        self._active_file = path
        self._active_file_first_tick = first_tick
        self._active_file_total_ticks = last_tick - first_tick

        self.send_data(ipc.HistoryLength(self.history_length))
        get_stream, total_ticks = self._get_stream_and_ticks()
        self._replay(get_stream, total_ticks)

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

    def _replay(self, get_stream: Callable[[], _SkippableEventStream],
                total_ticks: int, paused: bool = False) -> None:
        """Replay events from a stream factory at the live tick rate."""
        stream = _SkippableEventStream(iter(()))
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

                if i:
                    self.send_data(ipc.PlaybackRestarted())
                else:
                    self.send_data(ipc.PlaybackStarted(paused=paused))

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
                        self._active_file = None
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

                    case ipc.ExportHistory():
                        self._export_history(message.path, message.start_percentage, message.end_percentage)

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
            if self._seek_tick is None and self._options.skip_empty_ticks:
                assert next_event is not None  # Keep mypy happy
                ticks_until_action = stream.next_active_tick(next_event) - recorded_tick - 1
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
