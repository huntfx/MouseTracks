import os
import pickle
import re
import time
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterator, Self
from uuid import uuid4

import numpy as np

from .config.cli import DATA_DIR
from .config.settings import ProfileConfig
from .constants import COMPRESSION_FACTOR, COMPRESSION_THRESHOLD, DEBUG
from .utils.keycodes import CLICK_CODES


CURRENT_FILE_VERSION = 1

EXTENSION = 'mtk'
"""Extension to use for the profile data."""

PROFILE_DIR = DATA_DIR / 'Profiles'


class UnsupportedVersionError(Exception):
    """When a file can't be loaded due to an unsupported version"""


class TrackingArray:
    def __init__(self, shape: int | tuple[int, ...] | np.ndarray, dtype, auto_pad: bool | list[bool] = False) -> None:
        """Set up the tracking array..

        Parameters:
            shape: Set the shape of the new array.
                An existing array may be passed in here.
            auto_pad: If the array can increase in size.
        """
        # Create the array
        if isinstance(shape, np.ndarray):
            self.array = shape.astype(dtype)
        else:
            self.array = np.zeros(shape, dtype=dtype)

        # Set auto padding settings
        if isinstance(auto_pad, bool):
            self.auto_pad = [auto_pad] * self.array.ndim
        elif len(auto_pad) != self.array.ndim:
            raise ValueError('length of auto_pad must match number of array dimensions')
        else:
            self.auto_pad = auto_pad

    def as_zero(self) -> Self:
        """Return a copy of the same array with all values as 0."""
        return type(self)(self.array.shape, self.array.dtype, self.auto_pad)

    def __array__(self) -> np.ndarray:
        """For internal numpy usage."""
        return self.array

    def __str__(self) -> str:
        return str(self.array)

    def __repr__(self) -> str:
        return repr(self.array)

    def _check_padding(self, index: int | list[int]) -> bool:
        """Check if padding needs to be added.
        The index must be of the same dimensions of the array.
        """
        if isinstance(index, int):
            if self.array.ndim == 1 and self.auto_pad[0]:
                self.array = np.pad(self.array, (0, max(0, 1 + index - self.array.shape[0])))
                return True
            return False

        if len(index) != self.array.ndim:
            return False

        diff = []
        padding_required = False
        for idx, size, pad in zip(index, self.array.shape, self.auto_pad):
            if pad and idx >= size:
                diff.append((0, idx - size + 1))
                padding_required = True
            else:
                diff.append((0, 0))

        if not padding_required:
            return False

        self.array = np.pad(self.array, diff)
        return True

    def __getitem__(self, item):
        try:
            return self.array[item]
        except IndexError:
            if not self._check_padding(item):
                raise
            return self.array[item]

    def __setitem__(self, item, value):
        try:
            self.array[item] = value
        except IndexError:
            if not self._check_padding(item):
                raise
            self.array[item] = value

    def _write_to_zip(self, zf: zipfile.ZipFile, path: str) -> None:
        with zf.open(path, 'w') as f:
            np.save(f, self, allow_pickle=False)

    def _load_from_zip(self, zf: zipfile.ZipFile, path: str) -> None:
        with zf.open(path, 'r') as f:
            self.array = np.load(f, allow_pickle=False)


class TrackingIntArray(TrackingArray):
    """Create an integer array and update the dtype when required.
    This is for memory optimisation as the arrays are large.

    Ideally this would inherit `np.ndarray`, but changing the dtype of
    an array in-place isn't supported.
    """

    DTYPES: list[type[np.unsignedinteger]] = [np.uint8, np.uint16, np.uint32, np.uint64]

    MAX_VALUES: list[int] = [np.iinfo(dtype).max for dtype in DTYPES]

    def __init__(self, shape: int | tuple[int, ...] | np.ndarray, auto_pad: bool | list[bool] = False) -> None:
        """Set up the tracking array..

        Parameters:
            shape: Set the shape of the new array.
                An existing array may be passed in here.
            auto_pad: If the array can increase in size.
        """
        # Choose the best dtype to use
        max_int = 0
        if isinstance(shape, np.ndarray):
            max_int = np.max(shape)
        for dtype, max_value in zip(self.DTYPES, self.MAX_VALUES):
            if max_int < max_value:
                break
        else:
            raise ValueError('int too high')
        self.max_value = np.iinfo(dtype).max

        super().__init__(shape, dtype, auto_pad=auto_pad)

    def as_zero(self) -> Self:
        """Return a copy of the same array with all values as 0."""
        return type(self)(self.array.shape, self.auto_pad)

    def __getitem__(self, item: Any) -> int:
        """Get an array item."""
        return int(super().__getitem__(item))

    def __setitem__(self, item: int | tuple[int, ...], value: int) -> None:
        """Set an array item, changing dtype if required."""
        if value >= self.max_value:
            for dtype, max_value in zip(self.DTYPES, self.MAX_VALUES):
                if value < max_value:
                    self.max_value = max_value
                    self.array = self.array.astype(dtype)
                    break

        super().__setitem__(item, value)

    def _load_from_zip(self, zf: zipfile.ZipFile, path: str) -> None:
        """Load data and update the internal max value."""
        super()._load_from_zip(zf, path)
        self.max_value = np.iinfo(self.array.dtype).max


class ArrayResolutionMap(dict):
    """Store multiple arrays for different resolutions.
    New arrays will be created on demand.
    """

    def __missing__(self, key: tuple[int, int]) -> TrackingIntArray:
        self[key] = TrackingIntArray((key[1], key[0]))
        return self[key]

    def __setitem__(self, key: tuple[int, int], array: np.ndarray | TrackingIntArray) -> None:
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

    position: tuple[int, int] | None = field(default=None)  # TODO: Don't store here
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
class TrackingProfile:
    """The data stored per application.
    Everything that gets saved to disk is contained in here.
    """

    name: str = ''

    config: ProfileConfig = field(default_factory=ProfileConfig, init=False)

    created: int = field(default_factory=lambda: int(time.time()), init=False)
    modified: int = field(default_factory=lambda: int(time.time()), init=False)
    is_modified: bool = field(default=False, init=False)
    elapsed: int = field(default=0, init=False)
    active: int = field(default=0, init=False)
    inactive: int = field(default=0, init=False)

    cursor_map: MovementMaps = field(default_factory=MovementMaps, init=False)
    thumbstick_l_map: dict[int, MovementMaps] = field(default_factory=lambda: defaultdict(MovementMaps), init=False)
    thumbstick_r_map: dict[int, MovementMaps] = field(default_factory=lambda: defaultdict(MovementMaps), init=False)

    mouse_single_clicks: dict[int, ArrayResolutionMap] = field(default_factory=lambda: defaultdict(ArrayResolutionMap), init=False)
    mouse_double_clicks: dict[int, ArrayResolutionMap] = field(default_factory=lambda: defaultdict(ArrayResolutionMap), init=False)
    mouse_held_clicks: dict[int, ArrayResolutionMap] = field(default_factory=lambda: defaultdict(ArrayResolutionMap), init=False)

    key_presses: TrackingIntArray = field(default_factory=lambda: TrackingIntArray(0xFF, auto_pad=[True]), init=False)
    key_held: TrackingIntArray = field(default_factory=lambda: TrackingIntArray(0xFF, auto_pad=[True]), init=False)

    button_presses: dict[int, TrackingIntArray] = field(default_factory=lambda: defaultdict(lambda: TrackingIntArray(20)), init=False)
    button_held: dict[int, TrackingIntArray] = field(default_factory=lambda: defaultdict(lambda: TrackingIntArray(20)), init=False)

    data_interfaces: dict[str, str | None] = field(default_factory=lambda: defaultdict(str), init=False)
    data_upload: dict[str, int] = field(default_factory=lambda: defaultdict(int), init=False)
    data_download: dict[str, int] = field(default_factory=lambda: defaultdict(int), init=False)

    daily_ticks: TrackingIntArray = field(default_factory=lambda: TrackingIntArray((1, 3), auto_pad=[True, False]), init=False)
    daily_distance: TrackingArray = field(default_factory=lambda: TrackingArray(1, np.float32, auto_pad=True), init=False)
    daily_clicks: TrackingIntArray = field(default_factory=lambda: TrackingIntArray(1, auto_pad=True), init=False)
    daily_scrolls: TrackingIntArray = field(default_factory=lambda: TrackingIntArray(1, auto_pad=True), init=False)
    daily_keys: TrackingIntArray = field(default_factory=lambda: TrackingIntArray(1, auto_pad=True), init=False)
    daily_buttons: TrackingIntArray = field(default_factory=lambda: TrackingIntArray(1, auto_pad=True), init=False)
    daily_upload: TrackingIntArray = field(default_factory=lambda: TrackingIntArray(1, auto_pad=True), init=False)
    daily_download: TrackingIntArray = field(default_factory=lambda: TrackingIntArray(1, auto_pad=True), init=False)

    def _write_to_zip(self, zf: zipfile.ZipFile) -> None:
        if DEBUG:
            assert (self.active + self.inactive) == self.elapsed

        with zf.open('config.yaml', 'w') as f:
            self.config.save(f)

        zf.writestr('version', str(CURRENT_FILE_VERSION))
        zf.writestr('metadata/name', self.name)
        zf.writestr('metadata/time/created', str(self.created))
        zf.writestr('metadata/time/modified', str(int(time.time())))
        zf.writestr('metadata/ticks/elapsed', str(self.elapsed))
        zf.writestr('metadata/ticks/active', str(self.active))
        zf.writestr('metadata/ticks/inactive', str(self.inactive))

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

        for mac_address, amount in self.data_upload.items():
            zf.writestr(f'data/network/upload/{mac_address}', str(amount))
        for mac_address, amount in self.data_download.items():
            zf.writestr(f'data/network/download/{mac_address}', str(amount))
        for mac_address, name in self.data_interfaces.items():
            zf.writestr(f'data/network/interfaces/{mac_address}', name or '')

        self.daily_ticks._write_to_zip(zf, 'stats/ticks.npy')
        self.daily_distance._write_to_zip(zf, 'stats/mouse/distance.npy')
        self.daily_clicks._write_to_zip(zf, 'stats/mouse/clicks.npy')
        self.daily_scrolls._write_to_zip(zf, 'stats/mouse/scrolls.npy')
        self.daily_keys._write_to_zip(zf, 'stats/keyboard/keys.npy')
        self.daily_buttons._write_to_zip(zf, 'stats/gamepad/buttons.npy')
        self.daily_upload._write_to_zip(zf, 'stats/network/upload.npy')
        self.daily_download._write_to_zip(zf, 'stats/network/download.npy')

    def _load_from_zip(self, zf: zipfile.ZipFile) -> None:
        all_paths = zf.namelist()

        self.name = zf.read('metadata/name').decode('utf-8')
        if 'config.yaml' in all_paths:
            with zf.open('config.yaml', 'r') as f:
                self.config.load(f)

        self.created = int(zf.read('metadata/time/created'))
        self.modified = int(zf.read('metadata/time/modified'))
        self.elapsed = int(zf.read('metadata/ticks/elapsed'))
        self.active = int(zf.read('metadata/ticks/active'))
        self.inactive = int(zf.read('metadata/ticks/inactive'))

        self.cursor_map._load_from_zip(zf, 'data/mouse/cursor')
        mouse_buttons = {int(path.split('/')[3]) for path in all_paths if path.startswith('data/mouse/clicks/')}
        for i in mouse_buttons:
            self.mouse_single_clicks[i]._load_from_zip(zf, f'data/mouse/clicks/{i}/single')
            self.mouse_double_clicks[i]._load_from_zip(zf, f'data/mouse/clicks/{i}/double')
            self.mouse_held_clicks[i]._load_from_zip(zf, f'data/mouse/clicks/{i}/held')

        self.key_presses._load_from_zip(zf, f'data/keyboard/pressed.npy')
        self.key_held._load_from_zip(zf, f'data/keyboard/held.npy')

        gamepad_indexes = {int(path.split('/')[2]) for path in all_paths if path.startswith('data/gamepad/')}
        for path in all_paths:
            for i in gamepad_indexes:
                if path.startswith(f'data/gamepad/{i}/left_stick'):
                    self.thumbstick_l_map[i]._load_from_zip(zf, f'data/gamepad/{i}/left_stick')
                if path.startswith(f'data/gamepad/{i}/right_stick'):
                    self.thumbstick_r_map[i]._load_from_zip(zf, f'data/gamepad/{i}/right_stick')
                if path == f'data/gamepad/{i}/pressed.npy':
                    self.button_presses[i]._load_from_zip(zf, f'data/gamepad/{i}/pressed.npy')
                if path == f'data/gamepad/{i}/held.npy':
                    self.button_held[i]._load_from_zip(zf, f'data/gamepad/{i}/held.npy')

            if path.startswith('data/network/upload/'):
                mac_address = path.split('/')[3]
                self.data_upload[mac_address] = int(zf.read(path))
            elif path.startswith('data/network/download/'):
                mac_address = path.split('/')[3]
                self.data_download[mac_address] = int(zf.read(path))
            elif path.startswith('data/network/interfaces/'):
                mac_address = path.split('/')[3]
                self.data_interfaces[mac_address] = zf.read(path).decode('utf-8')
                if not self.data_interfaces[mac_address]:
                    self.data_interfaces[mac_address] = None

        self.daily_ticks._load_from_zip(zf, 'stats/ticks.npy')
        self.daily_distance._load_from_zip(zf, 'stats/mouse/distance.npy')
        self.daily_clicks._load_from_zip(zf, 'stats/mouse/clicks.npy')
        self.daily_scrolls._load_from_zip(zf, 'stats/mouse/scrolls.npy')
        self.daily_keys._load_from_zip(zf, 'stats/keyboard/keys.npy')
        self.daily_buttons._load_from_zip(zf, 'stats/gamepad/buttons.npy')
        self.daily_upload._load_from_zip(zf, 'stats/network/upload.npy')
        self.daily_download._load_from_zip(zf, 'stats/network/download.npy')

        if DEBUG:
            assert (self.active + self.inactive) == self.elapsed

    def save(self, path: str) -> bool:
        self.is_modified = False

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

                # Rename the existing file
                # If it has a permission error, then keep retrying
                # If it never unlocks then skip the save
                for _ in range(5):
                    try:
                        os.rename(path, del_file)
                    except PermissionError:
                        print(f'[File] Permission error when renaming {path}, trying again...')
                        time.sleep(2)
                    else:
                        break
                else:
                    print(f'[File] Unable to overwrite {path}, saving failed!')
                    self.is_modified = True
                    return False

            os.rename(temp_file, path)

        finally:
            # Clean up files
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(del_file):
                os.remove(del_file)

        return True

    @classmethod
    def load(cls, path: str) -> Self:
        profile = cls()
        with zipfile.ZipFile(path, mode='r') as zf:
            profile._load_from_zip(zf)
        return profile

    def import_legacy(self, path: str) -> None:
        """Load in data from the legacy tracking.
        This is not perfectly safe as it involves loading pickled data,
        so it is hidden behind the "File > Import" option.

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
        # Attempt to import the legacy libraries
        try:
            from mousetracks.files import CustomOpen, decode_file, upgrade_version

        # Manually load the data
        except ImportError:

            with zipfile.ZipFile(path, mode='r') as zf:
                # Check the version
                # Manual parsing is only supported for version 34
                try:
                    version = int(zf.read('metadata/file.txt'))
                except KeyError:
                    version = None
                if version != 34:
                    raise UnsupportedVersionError(f'legacy profile cannot be imported as it does not have the most recent update')

                # Load in the data
                with zf.open('data.pkl') as f:
                    data: dict[str, Any] = pickle.load(f)

                    # Load in the arrays
                    for resolution, values in data['Resolution'].items():
                        with zf.open(f'maps/{values["Tracks"]}.npy') as f:
                            if np.any(array := np.load(f) > 0):
                                self.cursor_map.sequential_arrays[resolution] = TrackingIntArray(array)
                        with zf.open(f'maps/{values["Speed"]}.npy') as f:
                            if np.any(array := np.load(f) > 0):
                                self.cursor_map.speed_arrays[resolution] = TrackingIntArray(array)
                        with zf.open(f'maps/{values["Clicks"]["Single"]["Left"]}.npy') as f:
                            if np.any(array := np.load(f) > 0):
                                self.mouse_single_clicks[CLICK_CODES[0]][resolution] = TrackingIntArray(array)
                        with zf.open(f'maps/{values["Clicks"]["Single"]["Middle"]}.npy') as f:
                            if np.any(array := np.load(f) > 0):
                                self.mouse_single_clicks[CLICK_CODES[1]][resolution] = TrackingIntArray(array)
                        with zf.open(f'maps/{values["Clicks"]["Single"]["Right"]}.npy') as f:
                            if np.any(array := np.load(f) > 0):
                                self.mouse_single_clicks[CLICK_CODES[2]][resolution] = TrackingIntArray(array)
                        with zf.open(f'maps/{values["Clicks"]["Double"]["Left"]}.npy') as f:
                            if np.any(array := np.load(f) > 0):
                                self.mouse_double_clicks[CLICK_CODES[0]][resolution] = TrackingIntArray(array)
                        with zf.open(f'maps/{values["Clicks"]["Double"]["Middle"]}.npy') as f:
                            if np.any(array := np.load(f) > 0):
                                self.mouse_double_clicks[CLICK_CODES[1]][resolution] = TrackingIntArray(array)
                        with zf.open(f'maps/{values["Clicks"]["Double"]["Right"]}.npy') as f:
                            if np.any(array := np.load(f) > 0):
                                self.mouse_double_clicks[CLICK_CODES[2]][resolution] = TrackingIntArray(array)

        # Load the data using the legacy library
        else:
            with CustomOpen(path, 'rb') as f:
                data = upgrade_version(decode_file(f, legacy=f.zip is None))

            # Process main tracking data
            for resolution, values in data['Resolution'].items():
                tracks = values['Tracks']
                if np.any(tracks > 0):
                    self.cursor_map.sequential_arrays[resolution] = TrackingIntArray(tracks)

                speed = values['Speed']
                if np.any(speed > 0):
                    self.cursor_map.speed_arrays[resolution] = TrackingIntArray(speed)

                single_clicks = values['Clicks']['Single']
                for i, mb in enumerate(('Left', 'Middle', 'Right')):
                    array = single_clicks[mb]
                    if np.any(array > 0):
                        self.mouse_single_clicks[CLICK_CODES[i]][resolution] = TrackingIntArray(array)

                double_clicks = values['Clicks']['Double']
                for i, mb in enumerate(('Left', 'Middle', 'Right')):
                    array = double_clicks[mb]
                    if np.any(array > 0):
                        self.mouse_double_clicks[CLICK_CODES[i]][resolution] = TrackingIntArray(array)

        # Load in the metadata
        self.created = int(data['Time']['Created'])
        self.cursor_map.distance = int(data['Distance']['Tracks'])
        self.cursor_map.counter = int(data['Ticks']['Tracks'])

        # Calculate the active / inactive time
        # This was not recorded properly in the legacy code, so a very
        # rough formula is used to estimate based on the data available
        self.elapsed = data['Ticks']['Total']
        self.active = int(data['Ticks']['Recorded'] * (data['Ticks']['Total'] / data['Ticks']['Recorded']) ** 0.9)
        self.inactive = data['Ticks']['Total'] - self.active

        # Process key/button data
        for keycode, count in data['Keys']['All']['Pressed'].items():
            self.key_presses[keycode] = count
        for keycode, count in data['Keys']['All']['Held'].items():
            self.key_held[keycode] = count

        for keycode, count in data['Gamepad']['All']['Buttons']['Pressed'].items():
            self.button_presses[0][keycode] = count
        for keycode, count in data['Gamepad']['All']['Buttons']['Held'].items():
            self.button_held[0][keycode] = count


class TrackingProfileLoader(dict):
    """Act like a defaultdict to load data if available."""

    def __getitem__(self, profile_name: str) -> TrackingProfile:
        """Load the profile and update the current name.

        This is due to the name being stored internally and will not
        update even if the profile is manually renamed.
        """
        profile: TrackingProfile = super().__getitem__(profile_name)
        profile.name = profile_name
        return profile

    def __missing__(self, profile_name: str) -> TrackingProfile:
        """Load in any missing data or create a new profile."""
        filename = get_filename(profile_name)
        if os.path.exists(filename):
            self[profile_name] = TrackingProfile.load(filename)
        else:
            self[profile_name] = profile = TrackingProfile()
            profile.name = profile_name
        return self[profile_name]


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
            name = zf.read('metadata/name').decode('utf-8')
        files.append((file.stat().st_mtime, name))
    return [name for modified, name in sorted(files, reverse=True)]
