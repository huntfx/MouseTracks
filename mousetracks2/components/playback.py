"""Playback component — replaces the tracking component during playback.

Reads a .jsonl.gz recording file and replays the stored events back through
the hub at the original 60 ticks per second rate.
"""

from __future__ import annotations

import time

from . import ipc
from .abstract import Component
from .recording import read_recording
from ..constants import UPDATES_PER_SECOND
from ..context import CTX
from ..exceptions import ExitRequest
from ..utils.system import hide_child_process

from ..utils.timing import ticks


class Playback(Component):
    """Replace the tracking to replay a .jsonl.gz recording."""

    target = ipc.Target.Playback

    def __post_init__(self) -> None:
        hide_child_process()

    def run(self) -> None:
        """Read the recording and emit events tick by tick."""
        path = CTX.playback_file
        if path is None:
            return

        stream = read_recording(str(path))

        # Grab data from the first recorded event
        next_event = next(stream, None)
        if next_event is None:
            return
        start_tick = next_event[0]
        start_timestamp = int(time.time())

        # Iterate per tick to keep the correct timing
        for tick in ticks(UPDATES_PER_SECOND):
            recorded_tick = start_tick + tick
            timestamp = start_timestamp + tick // UPDATES_PER_SECOND
            self.send_data(ipc.Tick(recorded_tick, timestamp))

            # Process all events for the specific tick
            while next_event is not None and next_event[0] <= recorded_tick:
                message = next_event[1]
                if isinstance(message, ipc.Tick):
                    start_timestamp = message.timestamp - tick // UPDATES_PER_SECOND
                self.send_data(message)
                next_event = next(stream, None)

            # Check for stop/exit signals
            for message in self.receive_data():
                match message:
                    case ipc.StopTracking() | ipc.Exit():
                        raise ExitRequest

            if next_event is None:
                break

        self.send_data(ipc.PauseTracking())
