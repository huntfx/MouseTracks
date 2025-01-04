import os
import pickle
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import numpy as np


COMPRESSION_FACTOR = 1.1

COMPRESSION_THRESHOLD = 425000  # Max: 2 ** 64 - 1

EXPECTED_LEGACY_VERSION = 34
"""Only mtk files of this version are allowed to be loaded.
Any other versions must be upgraded with the mousetracks v1 script.
"""


class InvalidVersionError(Exception):
    def __init__(self, filename: str, version: int, expected: int) -> None:
        super().__init__(f'The {os.path.basename(filename)} version is invalid '
                         f'(got: v{version}, expected: v{expected})')


class IntArrayHandler:
    """Create an integer array and update the dtype when required."""

    DTYPES = [np.uint16, np.uint32, np.uint64]
    MAX_VALUES = [np.iinfo(dtype).max for dtype in DTYPES]

    def __init__(self, shape: int | list[int] | np.ndarray) -> None:
        if isinstance(shape, np.ndarray):
            self.array = shape
        else:
            self.array = np.zeros(shape, dtype=np.uint8)
        self.max_value = np.iinfo(np.uint8).max

    def __str__(self) -> str:
        return str(self.array)

    def __repr__(self) -> str:
        return repr(self.array)

    def __getitem__(self, item: any) -> int:
        """Get an array item."""
        return self.array[item]

    def __setitem__(self, item: any, value: int) -> None:
        """Set an array item, changing dtype if required."""
        if value >= self.max_value:
            for dtype, max_value in zip(self.DTYPES, self.MAX_VALUES):
                if value < max_value:
                    self.max_value = max_value
                    self.array = self.array.astype(dtype)
                    break

        self.array[item] = value


class ResolutionArray(dict):
    """Store multiple arrays for different resolutions."""

    def __missing__(self, key: tuple[int, int]) -> IntArrayHandler:
        self[key] = IntArrayHandler([key[1], key[0]])
        return self[key]



@dataclass
class MapData:
    """Hold the data for tracking the movement of something."""

    _MAX_VALUE = 2 ** 64 - 1

    position: Optional[tuple[int, int]] = field(default=None)
    time_arrays: ResolutionArray = field(default_factory=ResolutionArray)
    speed_arrays: ResolutionArray = field(default_factory=ResolutionArray)
    count_arrays: ResolutionArray = field(default_factory=ResolutionArray)
    distance: float = field(default=0.0)
    move_count: int = field(default=0)
    move_tick: int = field(default=0)

    def requires_compression(self, threshold: int = COMPRESSION_THRESHOLD) -> bool:
        """Check if compression is required."""
        return self.move_count > min(threshold, self._MAX_VALUE)

    def run_compression(self, factor: float = COMPRESSION_FACTOR) -> None:
        """Compress down the values.
        This is important for the time arrays, but helps flatten out
        speed values that are too large.
        """
        for maps in (self.time_arrays, self.speed_arrays):
            for res, array in maps.items():
                maps[res] = (array / factor).astype(array.dtype)
            self.move_count = int(self.move_count // factor)


@dataclass
class ApplicationData:
    """The data stored per application."""

    cursor_map: MapData = field(default_factory=MapData)
    thumbstick_l_map: dict[int, MapData] = field(default_factory=lambda: defaultdict(MapData))
    thumbstick_r_map: dict[int, MapData] = field(default_factory=lambda: defaultdict(MapData))
    trigger_map: dict[int, MapData] = field(default_factory=lambda: defaultdict(MapData))

    mouse_single_clicks: dict[int, ResolutionArray] = field(default_factory=lambda: defaultdict(ResolutionArray))
    mouse_double_clicks: dict[int, ResolutionArray] = field(default_factory=lambda: defaultdict(ResolutionArray))
    mouse_held_clicks: dict[int, ResolutionArray] = field(default_factory=lambda: defaultdict(ResolutionArray))

    key_presses: IntArrayHandler = field(default_factory=lambda: IntArrayHandler(0xFF))
    key_held: IntArrayHandler = field(default_factory=lambda: IntArrayHandler(0xFF))

    button_presses: dict[int, IntArrayHandler] = field(default_factory=lambda: defaultdict(lambda: IntArrayHandler(20)))
    button_held: dict[int, IntArrayHandler] = field(default_factory=lambda: defaultdict(lambda: IntArrayHandler(20)))


def load_legacy_data(path: str) -> ApplicationData:
    """Load in data from the legacy tracking.

    Mouse:
        Time, speed and click arrays are imported.
        There is no density data.

    Keyboard:
        Everything is imported.

    Gamepad:
        Mostly imported.
        Trigger presses may be lost.
        Thumbstick data is discarded as X and Y were recorded separately
        and cannot be recombined.
    """

    result = ApplicationData()

    with zipfile.ZipFile(path, 'r') as zf:
        # Check the version
        version = int(zf.read('metadata/file.txt'))
        if version != EXPECTED_LEGACY_VERSION:
            raise InvalidVersionError(path, version, EXPECTED_LEGACY_VERSION)

        # Load in the data
        with zf.open('data.pkl') as f:
            data: dict[str, any] = pickle.load(f)

        # Load in the metadata
        # created: int = int(data['Time']['Created'])
        # modified: int = int(data['Time']['Modified'])
        # session_count: int = data['TimesLoaded']
        # ticks_total: int = data['Ticks']['Total']
        # ticks_recorded: int = data['Ticks']['Recorded']

        result.cursor_map.distance = int(data['Distance']['Tracks'])
        result.cursor_map.move_count = int(data['Ticks']['Tracks'])

        # Process main tracking data
        for resolution, values in data['Resolution'].items():
            # Load tracking heatmap
            for array_type, container in (('Tracks', result.cursor_map.time_arrays), ('Speed', result.cursor_map.speed_arrays)):
                with zf.open(f'maps/{values[array_type]}.npy') as f:
                    array = np.load(f)
                    if np.any(array > 0):
                        container[resolution].array = array

            # Load click heatmap
            for array_type, container in (('Single', result.mouse_single_clicks), ('Double', result.mouse_double_clicks)):
                for i, mb in enumerate(('Left', 'Middle', 'Right')):
                    with zf.open(f'maps/{values["Clicks"][array_type][mb]}.npy') as f:
                        array = np.load(f)
                        if np.any(array > 0):
                            container[MOUSE_BUTTONS[i]][resolution].array = array

        # Process key/button data
        for opcode, count in data['Keys']['All']['Pressed'].items():
            result.key_presses[opcode] = count
        for opcode, count in data['Keys']['All']['Held'].items():
            result.key_held[opcode] = count

        for opcode, count in data['Gamepad']['All']['Buttons']['Pressed'].items():
            result.button_presses[opcode] = count
        for opcode, count in data['Gamepad']['All']['Buttons']['Held'].items():
            result.button_held[opcode] = count

        return result
