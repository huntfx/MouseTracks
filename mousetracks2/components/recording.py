"""Serialisation and deserialisation for session recording files.

Recording files use the .jsonl.gz format (gzipped JSON Lines).
Each line is a JSON object representing one recorded event.

Reserved fields:
    _t: tick number at the time the event was recorded
    _e: event class name

All other fields are the init arguments of the dataclass, passed
directly to the constructor on deserialisation.
"""

from __future__ import annotations

import dataclasses
import gzip
import json
import traceback
import typing
from collections.abc import Iterator
from enum import Enum
from pathlib import Path
from typing import IO, Any

from . import ipc
from ..types import Rect, RectList
from ..utils.monitor import MonitorData


RECORDED_MESSAGE_TYPES: frozenset[type] = frozenset({
    ipc.MouseMove,
    ipc.MouseClick,
    ipc.MouseHeld,
    ipc.KeyPress,
    ipc.KeyHeld,
    ipc.ButtonPress,
    ipc.ButtonHeld,
    ipc.ThumbstickMove,
    ipc.DataTransfer,
    ipc.MonitorsChanged,
    ipc.CurrentProfileChanged,  # Use this instead of TrackedApplicationDetected
})


# --- Serialisation ---

def _serialise_value(value: Any) -> Any:
    """Recursively convert a field value to a JSON-compatible form."""
    if isinstance(value, RectList):
        return value.rects
    if isinstance(value, MonitorData):
        return {'logical': value.logical.rects, 'physical': value.physical.rects}
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, Enum):
        return value.name
    return value


def _build_serialiser(cls: type) -> Any:
    """Build a serialisation function for a message class."""
    field_names = tuple(f.name for f in dataclasses.fields(cls) if f.init)
    cls_name = cls.__name__

    def serialiser(tick: int, message: ipc.Message) -> str:
        fields = {name: _serialise_value(getattr(message, name)) for name in field_names}
        data = {'_t': tick, '_e': cls_name, **fields}
        return json.dumps(data, separators=(',', ':'))

    return serialiser


_SERIALISERS: dict[type, Any] = {cls: _build_serialiser(cls) for cls in RECORDED_MESSAGE_TYPES | {ipc.Tick}}


def serialise_event(tick: int, message: ipc.Message) -> str:
    """Serialise a message to a compact JSON line."""
    return _SERIALISERS[type(message)](tick, message)


# --- Deserialisation ---

def _deserialise_monitor_data(data: dict[str, Any]) -> MonitorData:
    """Reconstruct MonitorData from serialised form."""
    monitor_data = MonitorData()
    # Since it calls reload() automatically, overwrite the values
    monitor_data.logical = RectList(Rect.from_rect(*r) for r in data['logical'])
    monitor_data.physical = RectList(Rect.from_rect(*r) for r in data['physical'])
    return monitor_data


def _convert_value(value: Any, hint: Any) -> Any:
    """Convert a deserialised JSON value to the correct Python type."""
    # If `hint` is `tuple[int, int]`, then `origin` is `tuple`
    origin = typing.get_origin(hint)

    if hint is RectList:
        return RectList(Rect.from_rect(*r) for r in value)
    if hint is MonitorData:
        return _deserialise_monitor_data(value)
    if origin is tuple:
        return tuple(value)
    if isinstance(hint, type) and issubclass(hint, Enum):
        return hint[value]
    return value


def _build_parser(cls: type) -> Any:
    """Build a deserialisation function for a message class."""
    hints = typing.get_type_hints(cls)
    fields = [f for f in dataclasses.fields(cls) if f.init]

    def parser(d: dict[str, Any]) -> ipc.Message:
        return cls(**{f.name: _convert_value(d[f.name], hints[f.name]) for f in fields})

    return parser


_PARSERS: dict[str, Any] = {
    cls.__name__: _build_parser(cls)
    for cls in RECORDED_MESSAGE_TYPES | {ipc.Tick}
}


def _deserialise_line(line: str) -> tuple[int, ipc.Message] | None:
    """Parse one JSON line. Returns None if unknown or malformed."""
    try:
        data = json.loads(line)
        tick: int = data['_t']
        event_name: str = data['_e']
        parser = _PARSERS.get(event_name)
        if parser is None:
            return None
        return tick, parser(data)

    except Exception as e:
        traceback.print_exc()
        print(f'Error parsing line: {line}: {e}')
        return None


# --- File I/O ---

def open_recording(path: str) -> IO[str]:
    """Open a .jsonl.gz file for streaming writes. Caller must close it."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return gzip.open(path, 'wt', encoding='utf-8')


def write_event(f: IO[str], tick: int, message: ipc.Message) -> None:
    """Write a single event line to an open recording file."""
    f.write(serialise_event(tick, message) + '\n')


def read_recording(path: str) -> Iterator[tuple[int, ipc.Message]]:
    """Read events from a .jsonl.gz file. Skips unknown or malformed lines."""
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        stripped_lines = filter(bool, map(str.strip, f))
        deserialised_lines = filter(bool, map(_deserialise_line, stripped_lines))
        yield from deserialised_lines


def _test() -> None:
    """Write a recording to a temp file, read it back, and verify the roundtrip."""
    import tempfile
    import time
    from ..types import Rect, RectList
    from ..utils.monitor import MonitorData

    monitor = MonitorData()
    monitor.logical = RectList([Rect.from_rect(0, 0, 1920, 1080), Rect.from_rect(1920, 0, 3840, 1080)])
    monitor.physical = RectList([Rect.from_rect(0, 0, 2560, 1440)])

    ts = int(time.time())
    test_cases: list[tuple[int, ipc.Message]] = [
        (0,  ipc.Tick(tick=0, timestamp=ts)),
        (1,  ipc.MouseMove(position=(640, 480))),
        (1,  ipc.MouseClick(button=1, position=(640, 480))),
        (1,  ipc.MouseHeld(button=1, position=(640, 480))),
        (2,  ipc.KeyPress(keycode=65)),
        (2,  ipc.KeyHeld(keycode=65)),
        (3,  ipc.ButtonPress(gamepad=0, keycode=4096)),
        (3,  ipc.ButtonHeld(gamepad=0, keycode=4096)),
        (4,  ipc.ThumbstickMove(gamepad=0, thumbstick=ipc.ThumbstickMove.Thumbstick.Left, position=(0.5, -0.3))),
        (5,  ipc.DataTransfer(mac_address='aa:bb:cc:dd:ee:ff', bytes_sent=1024, bytes_recv=2048)),
        (6,  ipc.MonitorsChanged(data=monitor)),
        (7,  ipc.CurrentProfileChanged(name='Firefox', process_id=1234, rects=RectList([Rect.from_rect(100, 200, 1820, 880)]))),
        (8,  ipc.CurrentProfileChanged(name='Default', process_id=None, rects=RectList())),
        (9,  ipc.Tick(tick=9, timestamp=ts + 1)),
    ]

    with tempfile.TemporaryDirectory() as tmp_dir:
        path = str(Path(tmp_dir) / 'test.jsonl.gz')
        print(f'Writing to {path}...')

        # Write
        with open_recording(path) as f:
            for tick, message in test_cases:
                write_event(f, tick, message)

        # Print file contents
        print('File contents:')
        with gzip.open(path, 'rt', encoding='utf-8') as f:
            for line in f:
                print(f'  {line}', end='')

        # Read back and compare
        print(f'Reading from {path}...')
        recovered = list(read_recording(path))
        print(f'Matched: {recovered == test_cases}')


if __name__ == '__main__':
    _test()
