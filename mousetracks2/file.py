import os
import pickle
import re
import sys
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional, Self
from uuid import uuid4

import numpy as np

from .constants import COMPRESSION_FACTOR, COMPRESSION_THRESHOLD, UPDATES_PER_SECOND, INACTIVITY_MS
from .utils.win import MOUSE_BUTTONS


ALLOW_LEGACY_IMPORT = True
"""Legacy imports require unpickling data, so is unsafe.
TODO: Default to False, and only enable when using File > Import.
"""

EXPECTED_LEGACY_VERSION = 34
"""Only legacy files of this version are allowed to be loaded.
Any other versions must be upgraded with the mousetracks v1 script.
"""

CURRENT_FILE_VERSION = 1

EXTENSION = 'mtk'
"""Extension to use for the profile data."""


# Get the appdata folder
# Source: https://github.com/ActiveState/appdirs/blob/master/appdirs.py
match sys.platform:
    case "win32":
        APPDATA = Path(os.path.expandvars('%APPDATA%'))
    case 'darwin':
        APPDATA = Path(os.path.expanduser('~/Library/Application Support/'))
    case _:
        APPDATA = Path(os.getenv('XDG_DATA_HOME', os.path.expanduser("~/.local/share")))

BASE_DIR = APPDATA / 'MouseTracks'

PROFILE_DIR = BASE_DIR / 'Profiles'


class UnsupportedVersionError(Exception):
    """When a file can't be loaded due to an unsupported version"""


class TrackingArray:
    """Create an integer array and update the dtype when required.
    This is for memory optimisation as the arrays are large.

    Ideally this would inherit `np.ndarray`, but changing the dtype of
    an array in-place isn't supported.
    """

    DTYPES = [np.uint8, np.uint16, np.uint32, np.uint64]
    MAX_VALUES = [np.iinfo(dtype).max for dtype in DTYPES]

    def __init__(self, shape: int | list[int] | np.ndarray) -> None:
        # Choose the best dtype to use
        max_int = 0
        if isinstance(shape, np.ndarray):
            max_int = np.max(shape)
        for dtype, max_value in zip(self.DTYPES, self.MAX_VALUES):
            if max_int < max_value:
                break
        else:
            raise ValueError('int too high')

        # Create the array
        if isinstance(shape, np.ndarray):
            self.array = shape.astype(dtype)
        else:
            self.array = np.zeros(shape, dtype=dtype)
        self.max_value = np.iinfo(dtype).max

    def __array__(self) -> np.ndarray:
        """For internal numpy usage."""
        return self.array

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

    def _write_to_zip(self, zf: zipfile.ZipFile, path: str) -> None:
        with zf.open(path, 'w') as f:
            np.save(f, self, allow_pickle=False)

    def _load_from_zip(self, zf: zipfile.ZipFile, path: str) -> None:
        with zf.open(path, 'r') as f:
            self.array = np.load(f, allow_pickle=False)


class ArrayResolutionMap(dict):
    """Store multiple arrays for different resolutions.
    New arrays will be created on demand.
    """

    def __missing__(self, key: tuple[int, int]) -> TrackingArray:
        self[key] = TrackingArray([key[1], key[0]])
        return self[key]

    def __setitem__(self, key: tuple[int, int], array: np.ndarray | TrackingArray) -> None:
        if isinstance(array, np.ndarray):
            self[key].array = array
        else:
            super().__setitem__(key, array)

    def _write_to_zip(self, zf: zipfile.ZipFile, subfolder: str) -> None:
        for (width, height), array in self.items():
            array._write_to_zip(zf, f'{subfolder}/{width}x{height}.npy')

    def _load_from_zip(self, zf: zipfile.ZipFile, subfolder: str) -> None:
        relative_paths = [path[len(subfolder):].lstrip('/') for path in zf.namelist() if path.startswith(subfolder)]

        for relative_path in relative_paths:
            match = re.match(r'(\d+)x(\d+)\.npy', relative_path)
            if match is None:
                raise RuntimeError(f'unexpected data in filename: {subfolder}/{relative_path}')
            width, height = map(int, match.groups())
            self[(width, height)]._load_from_zip(zf, f'{subfolder}/{relative_path}')


@dataclass
class MovementMaps:
    """Hold the data for the line based maps."""

    _MAX_VALUE = 2 ** 64 - 1

    position: Optional[tuple[int, int]] = field(default=None)  # TODO: Don't store here
    sequential_arrays: ArrayResolutionMap = field(default_factory=ArrayResolutionMap)
    density_arrays: ArrayResolutionMap = field(default_factory=ArrayResolutionMap)
    speed_arrays: ArrayResolutionMap = field(default_factory=ArrayResolutionMap)
    distance: float = field(default=0.0)
    counter: int = field(default=0)
    ticks: int = field(default=0)
    tick: int = field(default=0)  # TODO: Don't store here

    def requires_compression(self, threshold: int = COMPRESSION_THRESHOLD) -> bool:
        """Check if compression is required."""
        return self.counter > min(threshold, self._MAX_VALUE)

    def run_compression(self, factor: float = COMPRESSION_FACTOR) -> None:
        """Compress down the values.
        This is important for the time arrays, but helps flatten out
        speed values that are too large.
        """
        for maps in (self.sequential_arrays, self.speed_arrays):
            # Compress all arrays
            for res, array in tuple(maps.items()):
                array = np.asarray(array)
                maps[res] = (array.astype(np.float64) / factor).astype(array.dtype)

                # Remove array if it no longer contains data
                if not np.any(maps[res]):
                    del maps[res]

            # Compress the counter by the same amount
            self.counter = int(self.counter // factor)

    def _iter_array_types(self) -> Iterator[tuple[str, ArrayResolutionMap]]:
        yield 'sequential', self.sequential_arrays
        yield 'density', self.density_arrays
        yield 'speed', self.speed_arrays

    def _write_to_zip(self, zf: zipfile.ZipFile, subfolder: str) -> None:
        for array_type, array_resolution_map in self._iter_array_types():
            array_resolution_map._write_to_zip(zf, f'{subfolder}/{array_type}')
        zf.writestr(f'{subfolder}/distance', str(self.distance))
        zf.writestr(f'{subfolder}/counter', str(self.counter))
        zf.writestr(f'{subfolder}/ticks', str(self.counter))

    def _load_from_zip(self, zf: zipfile.ZipFile, subfolder: str) -> None:
        folders = {path[len(subfolder):].lstrip('/').split('/', 1)[0]
                   for path in zf.namelist() if path.startswith(subfolder)}

        for folder in folders:
            path = f'{subfolder}/{folder}'
            if folder == 'distance':
                self.distance = float(zf.read(path))
            elif folder == 'counter':
                self.counter = int(zf.read(path))
            elif folder == 'ticks':
                self.ticks = int(zf.read(path))
            elif folder == 'sequential':
                self.sequential_arrays._load_from_zip(zf, path)
            elif folder == 'density':
                self.density_arrays._load_from_zip(zf, path)
            elif folder == 'speed':
                self.speed_arrays._load_from_zip(zf, path)


@dataclass
class Tick:
    """Store data related to ticks."""

    current: int = field(default=0)
    previous: int = field(default=0)
    active: int = field(default=0)
    inactive: int = field(default=0)
    saved: int = field(default=0)

    @property
    def activity(self) -> int:
        """Get the number of active ticks."""
        amount = self.active
        if self.is_active:
            amount += self.since_active
        return amount

    @property
    def inactivity(self) -> int:
        """Get the number of inactive ticks."""
        amount = self.inactive
        if not self.is_active:
            amount += self.since_active
        return amount

    @property
    def is_active(self) -> bool:
        """Determine if currently active."""
        threshold = UPDATES_PER_SECOND * INACTIVITY_MS / 1000
        return self.since_active <= threshold

    @property
    def since_active(self) -> int:
        """Get the number of ticks since the last activity."""
        return self.current - self.previous

    def set_active(self) -> None:
        """Update the last tick activity."""
        if self.is_active:
            self.active += self.since_active
        else:
            self.inactive += self.since_active
        self.previous = self.current


@dataclass
class TrackingProfile:
    """The data stored per application.
    Everything that gets saved to disk is contained in here.
    """

    name: str

    created: int = field(default_factory=lambda: int(time.time()))
    tick: Tick = field(default_factory=Tick)

    cursor_map: MovementMaps = field(default_factory=MovementMaps)
    thumbstick_l_map: dict[int, MovementMaps] = field(default_factory=lambda: defaultdict(MovementMaps))
    thumbstick_r_map: dict[int, MovementMaps] = field(default_factory=lambda: defaultdict(MovementMaps))

    mouse_single_clicks: dict[int, ArrayResolutionMap] = field(default_factory=lambda: defaultdict(ArrayResolutionMap))
    mouse_double_clicks: dict[int, ArrayResolutionMap] = field(default_factory=lambda: defaultdict(ArrayResolutionMap))
    mouse_held_clicks: dict[int, ArrayResolutionMap] = field(default_factory=lambda: defaultdict(ArrayResolutionMap))

    key_presses: TrackingArray = field(default_factory=lambda: TrackingArray(0xFF))
    key_held: TrackingArray = field(default_factory=lambda: TrackingArray(0xFF))

    button_presses: dict[int, TrackingArray] = field(default_factory=lambda: defaultdict(lambda: TrackingArray(20)))
    button_held: dict[int, TrackingArray] = field(default_factory=lambda: defaultdict(lambda: TrackingArray(20)))

    @property
    def modified(self):
        """Determine if the data is modified."""
        return self.tick.current != self.tick.saved

    def _write_to_zip(self, zf: zipfile.ZipFile) -> None:
        zf.writestr('version', str(CURRENT_FILE_VERSION))
        zf.writestr('metadata/name', self.name)
        zf.writestr('metadata/created', str(self.created))
        zf.writestr('metadata/modified', str(int(time.time())))
        zf.writestr('metadata/active', str(self.tick.activity))
        zf.writestr('metadata/inactive', str(self.tick.inactivity))

        self.cursor_map._write_to_zip(zf, 'data/mouse/cursor')
        for i, array_resolution_map in self.mouse_single_clicks.items():
            array_resolution_map._write_to_zip(zf, f'data/mouse/clicks/{i}/single')
        for i, array_resolution_map in self.mouse_double_clicks.items():
            array_resolution_map._write_to_zip(zf, f'data/mouse/clicks/{i}/double')
        for i, array_resolution_map in self.mouse_held_clicks.items():
            array_resolution_map._write_to_zip(zf, f'data/mouse/clicks/{i}/held')

        self.key_presses._write_to_zip(zf, 'data/keyboard/pressed.npy')
        self.key_held._write_to_zip(zf, 'data/keyboard/held.npy')

        for i, array in self.button_presses.items():
            array._write_to_zip(zf, f'data/gamepad/{i}/pressed.npy')
        for i, array in self.button_held.items():
            array._write_to_zip(zf, f'data/gamepad/{i}/held.npy')
        for i, array_map in self.thumbstick_l_map.items():
            array_map._write_to_zip(zf, f'data/gamepad/{i}/left_stick')
        for i, array_map in self.thumbstick_r_map.items():
            array_map._write_to_zip(zf, f'data/gamepad/{i}/right_stick')

    def _load_from_zip(self, zf: zipfile.ZipFile) -> None:
        all_paths = zf.namelist()

        self.name = zf.read('metadata/name').decode('utf-8')
        self.created = int(zf.read('metadata/created'))
        self.tick.active = int(zf.read('metadata/active'))
        self.tick.inactive = int(zf.read('metadata/inactive'))

        self.cursor_map._load_from_zip(zf, 'data/mouse/cursor')
        mouse_buttons = {int(path.split('/')[3]) for path in all_paths if path.startswith('data/mouse/clicks')}
        for i in mouse_buttons:
            self.mouse_single_clicks[i]._load_from_zip(zf, f'data/mouse/clicks/{i}/single')
            self.mouse_double_clicks[i]._load_from_zip(zf, f'data/mouse/clicks/{i}/double')
            self.mouse_held_clicks[i]._load_from_zip(zf, f'data/mouse/clicks/{i}/held')

        self.key_presses._load_from_zip(zf, f'data/keyboard/pressed.npy')
        self.key_held._load_from_zip(zf, f'data/keyboard/held.npy')

        gamepad_indexes = {int(path.split('/')[2]) for path in all_paths if path.startswith('data/gamepad')}
        for i in gamepad_indexes:
            if f'data/gamepad/{i}/left_stick' in all_paths:
                self.thumbstick_l_map[i]._load_from_zip(zf, f'data/gamepad/{i}/left_stick')
            if f'data/gamepad/{i}/right_stick' in all_paths:
                self.thumbstick_r_map[i]._load_from_zip(zf, f'data/gamepad/{i}/right_stick')
            if f'data/gamepad/{i}/pressed.npy' in all_paths:
                self.button_presses[i]._load_from_zip(zf, f'data/gamepad/{i}/pressed.npy')
            if f'data/gamepad/{i}/held.npy' in all_paths:
                self.button_held[i]._load_from_zip(zf, f'data/gamepad/{i}/held.npy')

    def save(self, path: str):
        self.tick.saved = self.tick.current

        # Ensure the folder exists
        base_dir = os.path.dirname(path)
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        # Setup filenames
        temp_file_base = os.path.join(base_dir, uuid4().hex)
        temp_file = f'{temp_file_base}.tmp'
        del_file = f'{temp_file_base}.del'

        try:
            with zipfile.ZipFile(temp_file, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
                self._write_to_zip(zf)

            # Quickly swap over the files to reduce chances of a race condition
            if os.path.exists(path):
                os.rename(path, del_file)
            os.rename(temp_file, path)

        finally:
            # Clean up files
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(del_file):
                os.remove(del_file)

    @classmethod
    def load(cls, path: str, allow_legacy: bool = ALLOW_LEGACY_IMPORT) -> Self:
        profile = cls('')
        with zipfile.ZipFile(path, mode='r') as zf:
            version = _get_profile_version(zf)

            # Special case to load legacy profiles
            if version is None:
                if allow_legacy and _get_profile_legacy_version(zf) is not None:
                    _load_legacy_data(zf, profile)
                else:
                    raise UnsupportedVersionError('invalid file')

            # Load the data
            else:
                if not 1 <= version <= CURRENT_FILE_VERSION:
                    raise UnsupportedVersionError(str(version))
                profile._load_from_zip(zf)

        return profile


def _load_legacy_data(zf: zipfile.ZipFile, profile: TrackingProfile) -> None:
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
    # Check the version
    version = _get_profile_legacy_version(zf)
    if version != EXPECTED_LEGACY_VERSION:
        raise UnsupportedVersionError(f'legacy profile cannot be imported as it does not have the most recent update')

    # Load in the data
    with zf.open('data.pkl') as f:
        data: dict[str, any] = pickle.load(f)

    # Load in the metadata
    profile.created = int(data['Time']['Created'])
    profile.tick.active = data['Ticks']['Recorded']
    profile.tick.inactive = data['Ticks']['Total'] - data['Ticks']['Recorded']
    profile.cursor_map.distance = int(data['Distance']['Tracks'])
    profile.cursor_map.counter = int(data['Ticks']['Tracks'])

    # Process main tracking data
    for resolution, values in data['Resolution'].items():
        # Load tracking heatmap
        for array_type, container in (('Tracks', profile.cursor_map.sequential_arrays), ('Speed', profile.cursor_map.speed_arrays)):
            with zf.open(f'maps/{values[array_type]}.npy') as f:
                array = np.load(f)
                if np.any(array > 0):
                    container[resolution] = TrackingArray(array)

        # Load click heatmap
        for array_type, container in (('Single', profile.mouse_single_clicks), ('Double', profile.mouse_double_clicks)):
            for i, mb in enumerate(('Left', 'Middle', 'Right')):
                with zf.open(f'maps/{values["Clicks"][array_type][mb]}.npy') as f:
                    array = np.load(f)
                    if np.any(array > 0):
                        container[MOUSE_BUTTONS[i]][resolution] = TrackingArray(array)

    # Process key/button data
    for opcode, count in data['Keys']['All']['Pressed'].items():
        profile.key_presses[opcode] = count
    for opcode, count in data['Keys']['All']['Held'].items():
        profile.key_held[opcode] = count

    for opcode, count in data['Gamepad']['All']['Buttons']['Pressed'].items():
        profile.button_presses[0][opcode] = count
    for opcode, count in data['Gamepad']['All']['Buttons']['Held'].items():
        profile.button_held[0][opcode] = count


def _get_profile_version(zf: zipfile.ZipFile) -> Optional[bool]:
    try:
        return int(zf.read('version'))
    except KeyError:
        return None


def _get_profile_legacy_version(zf: zipfile.ZipFile) -> Optional[bool]:
    try:
        return int(zf.read('metadata/file.txt'))
    except KeyError:
        return None


class TrackingProfileLoader(dict):
    """Act like a defaultdict to load data if available."""
    def __missing__(self, application) -> TrackingProfile:
        filename = get_filename(application)
        if os.path.exists(filename):
            self[application] = TrackingProfile.load(filename)
        else:
            self[application] = TrackingProfile(application)
        return self[application]


def get_filename(application: str) -> str:
    """Get the filename for an application."""
    sanitised = re.sub(r'[^a-zA-Z0-9]', '', application.lower())
    return os.path.join(PROFILE_DIR, f'{sanitised}.{EXTENSION}')


def get_profile_names() -> list[str]:
    """Get all the profile_names, ordered by modified time."""
    if not os.path.exists(PROFILE_DIR):
        return []
    files = []
    for file in os.scandir(PROFILE_DIR):
        if os.path.splitext(file.name)[1] != f'.{EXTENSION}':
            continue
        with zipfile.ZipFile(file, 'r') as zf:
            if _get_profile_version(zf) is None:
                if _get_profile_legacy_version(zf) != EXPECTED_LEGACY_VERSION:
                    continue
                name = os.path.splitext(file.name)[0]
            else:
                name = zf.read('metadata/name').decode('utf-8')
        files.append((file.stat().st_mtime, name))
    return [name for modified, name in sorted(files, reverse=True)]
