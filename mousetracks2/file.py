import os
import pickle
import re
import time
import zipfile
from collections import defaultdict
from collections.abc import MutableMapping
from dataclasses import dataclass, field
from typing import Any, Generic, Iterator, Self, Sequence, Type, TypeVar
from uuid import uuid4

import numpy as np
import numpy.typing as npt

from .config import CLI, ProfileConfig
from .constants import COMPRESSION_FACTOR, COMPRESSION_THRESHOLD, DEBUG, TRACKING_DISABLE
from .utils.keycodes import CLICK_CODES


CURRENT_FILE_VERSION = 1

EXTENSION = 'mtk'
"""Extension to use for the profile data."""

PROFILE_DIR = CLI.data_dir / 'Profiles'

_DType_co = TypeVar('_DType_co', bound=np.generic, covariant=True)

_ScalarType_co = TypeVar('_ScalarType_co', covariant=True)


class TrackingArray(Generic[_DType_co, _ScalarType_co]):
    """Create a savable array with support for auto padding.

    Ideally this would inherit `np.ndarray`, but changing the dtype of
    an array in-place isn't supported.
    """

    array: npt.NDArray[_DType_co]
    auto_pad: list[bool]

    def __init__(self, shape: int | Sequence[int] | npt.NDArray[Any],
                 dtype: Type[_DType_co] | np.dtype[_DType_co],
                 auto_pad: bool | list[bool] = False) -> None:
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
            self.auto_pad = [auto_pad] * self.ndim
        elif len(auto_pad) != self.ndim:
            raise ValueError('length of auto_pad must match number of array dimensions')
        else:
            self.auto_pad = auto_pad

    def as_zero(self) -> Self:
        """Return a copy of the same array with all values as 0."""
        return type(self)(self.shape, self.dtype, self.auto_pad)

    def __array__(self) -> npt.NDArray[_DType_co]:
        """For internal numpy usage."""
        return self.array

    def __str__(self) -> str:
        return str(self.array)

    def __repr__(self) -> str:
        return repr(self.array)

    @property
    def dtype(self) -> np.dtype[_DType_co]:
        """Get the array dtype."""
        return self.array.dtype

    @property
    def shape(self) -> tuple[int, ...]:
        """Get the array shape."""
        return self.array.shape

    @property
    def ndim(self) -> int:
        """Get the array dimensions."""
        return self.array.ndim

    def _check_padding(self, index: int | list[int]) -> bool:
        """Check if padding needs to be added.
        The index must be of the same dimensions of the array.
        """
        if isinstance(index, int):
            if self.ndim == 1 and self.auto_pad[0]:
                self.array = np.pad(self.array, (0, max(0, 1 + index - self.shape[0])))
                return True
            return False

        if len(index) != self.ndim:
            return False

        diff = []
        padding_required = False
        for idx, size, pad in zip(index, self.shape, self.auto_pad):
            if pad and idx >= size:
                diff.append((0, idx - size + 1))
                padding_required = True
            else:
                diff.append((0, 0))

        if not padding_required:
            return False

        self.array = np.pad(self.array, diff)
        return True

    def __getitem__(self, item: Any) -> _ScalarType_co | npt.NDArray[_DType_co]:
        try:
            return self.array[item]
        except IndexError:
            if not self._check_padding(item):
                raise
            return self.array[item]

    def __setitem__(self, item: Any, value: Any) -> None:
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


class TrackingIntArray(TrackingArray[np.unsignedinteger, int]):
    """Create an integer array and update the dtype when required.
    This is for memory optimisation as the arrays are large.
    """

    DTYPES: list[type[np.unsignedinteger]] = [np.uint8, np.uint16, np.uint32, np.uint64]

    MAX_VALUES: list[int] = [np.iinfo(dtype).max for dtype in DTYPES]

    def __init__(self, shape: int | Sequence[int] | npt.NDArray[Any],
                 auto_pad: bool | list[bool] = False) -> None:
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
        return type(self)(self.shape, self.auto_pad)

    def __getitem__(self, item: Any) -> int:
        """Get an array item."""
        return int(super().__getitem__(item))

    def __setitem__(self, item: int | tuple[int, ...], value: int) -> None:
        """Set an array item, changing dtype if required."""
        self._check_dtype(value)
        super().__setitem__(item, value)

    def _load_from_zip(self, zf: zipfile.ZipFile, path: str) -> None:
        """Load data and update the internal max value."""
        super()._load_from_zip(zf, path)
        self.max_value = np.iinfo(self.dtype).max

    def _check_dtype(self, value: int) -> None:
        """Check that the dtype is valid for the given value."""
        if value >= self.max_value:
            for dtype, max_value in zip(self.DTYPES, self.MAX_VALUES):
                if value < max_value:
                    self.max_value = max_value
                    self.array = self.array.astype(dtype)
                    break


class ArrayResolutionMap(dict[tuple[int, int], TrackingIntArray]):
    """Store multiple arrays for different resolutions.
    New arrays will be created on demand.
    """

    def __missing__(self, key: tuple[int, int]) -> TrackingIntArray:
        self[key] = TrackingIntArray((key[1], key[0]))
        return self[key]

    def __setitem__(self, key: tuple[int, int], array: npt.NDArray[np.unsignedinteger] | TrackingIntArray) -> None:
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
            for res, tracking_array in tuple(maps.items()):
                array = np.asarray(tracking_array)
                maps[res] = (array.astype(np.float64) / factor).astype(array.dtype)

                # Remove array if it no longer contains data
                if not np.any(maps[res]):
                    del maps[res]

            # Compress the counter by the same amount
            self.counter = round(self.counter / factor)

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

    _last_accessed: float = field(default_factory=lambda: time.time(), init=False)

    def _write_to_zip(self, zf: zipfile.ZipFile) -> None:
        if DEBUG:
            assert (self.active + self.inactive) == self.elapsed

        with zf.open('config.yaml', 'w') as f:
            self.config.save(f)

        zf.writestr('version', str(CURRENT_FILE_VERSION))
        zf.writestr('metadata/name', self.name)
        zf.writestr('metadata/time/created', str(self.created))
        zf.writestr('metadata/time/modified', str(self.modified))
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

        self._last_accessed = time.time()

    def _load_from_zip(self, zf: zipfile.ZipFile, metadata_only: bool = False) -> None:
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

        if metadata_only:
            return

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

        self._last_accessed = time.time()

    def _save_main(self, path: str | None = None) -> bool:
        """Save the profile."""
        if path is None:
            path = get_filename(self.name)

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
                    return False

            # Copy modified date
            os.utime(temp_file, (self.modified, self.modified))

            # Replace file
            os.rename(temp_file, path)

        finally:
            # Clean up files
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if os.path.exists(del_file):
                os.remove(del_file)

        return True

    def save(self) -> bool:
        """Save the profile and handle the modified state."""
        if self.is_modified:
            previous, self.modified = self.modified, int(time.time())
        if self._save_main():
            self.is_modified = False
            return True
        self.modified = previous
        return False

    @classmethod
    def load(cls, path: str, metadata_only: bool = False) -> Self:
        """Load a profile."""
        profile = cls()
        with zipfile.ZipFile(path, mode='r') as zf:
            profile._load_from_zip(zf, metadata_only)
        return profile

    @classmethod
    def get_name(self, path: str) -> str | None:
        """Get the profile name if possible.
        If not possible, it's likely a legacy profile.
        """
        try:
            with zipfile.ZipFile(path, mode='r') as zf:
                return zf.read('metadata/name').decode('utf-8')
        except (KeyError, zipfile.BadZipFile):
            return None

    def import_legacy(self, path: str) -> bool:
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
        # Load the data using the legacy libraries
        from mousetracks.files import CustomOpen, decode_file, upgrade_version

        with CustomOpen(path, 'rb') as f:
            try:
                data = upgrade_version(decode_file(f, legacy=f.zip is None))
            except Exception as e:
                print(f'Error importing {path}: {e}')
                return False

        # Process main tracking data
        # Use the array shape as it does not always match the correct resolution
        for values in data['Resolution'].values():
            tracks = values['Tracks']
            if np.any(tracks > 0):
                self.cursor_map.sequential_arrays[tracks.shape[::-1]] = TrackingIntArray(tracks)

            speed = values['Speed']
            if np.any(speed > 0):
                self.cursor_map.speed_arrays[speed.shape[::-1]] = TrackingIntArray(speed)

            single_clicks = values['Clicks']['Single']
            for i, mb in enumerate(('Left', 'Middle', 'Right')):
                array = single_clicks[mb]
                if np.any(array > 0):
                    self.mouse_single_clicks[int(CLICK_CODES[i])][array.shape[::-1]] = TrackingIntArray(array)

            double_clicks = values['Clicks']['Double']
            for i, mb in enumerate(('Left', 'Middle', 'Right')):
                array = double_clicks[mb]
                if np.any(array > 0):
                    self.mouse_double_clicks[int(CLICK_CODES[i])][array.shape[::-1]] = TrackingIntArray(array)

        # Load in the metadata
        self.created = int(data['Time']['Created'])
        self.cursor_map.distance = int(data['Distance']['Tracks'])
        self.cursor_map.counter = int(data['Ticks']['Tracks'])

        # Calculate the active / inactive time
        # This was not recorded properly in the legacy code, so a very
        # rough formula is used to estimate based on the data available
        self.elapsed = data['Ticks']['Total']
        self.active = round(data['Ticks']['Recorded'] * (data['Ticks']['Total'] / data['Ticks']['Recorded']) ** 0.9)
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

        # Simple way to get the density array populated
        for array in map(np.asarray, self.cursor_map.sequential_arrays.values()):
            self.cursor_map.density_arrays[array.shape[::-1]].array[np.where(array > 1)] = 1

        return True


class TrackingProfileLoader(MutableMapping):
    """Act like a defaultdict to load data if available."""

    def __init__(self, max_profiles: int = 5):
        self.max_profiles = max_profiles
        self._profiles: dict[str, TrackingProfile] = {}

    def __setitem__(self, profile_name: str, profile: TrackingProfile) -> None:
        sanitised = sanitise_profile_name(profile_name)
        self._profiles[sanitised] = profile

    def __getitem__(self, profile_name: str) -> TrackingProfile:
        """Load or get a profile."""
        sanitised = sanitise_profile_name(profile_name)
        try:
            return self._profiles[sanitised]
        except KeyError:
            self._profiles[sanitised] = self._load_or_create_profile(profile_name)
        return self._profiles[sanitised]

    def __delitem__(self, profile_name: str) -> None:
        sanitised = sanitise_profile_name(profile_name)
        del self._profiles[sanitised]

    def __iter__(self) -> Iterator[str]:
        return iter(self._profiles)

    def __len__(self) -> int:
        return len(self._profiles)

    def __contains__(self, key: Any) -> bool:
        if not isinstance(key, str):
            return False
        sanitised = sanitise_profile_name(key)
        return sanitised in self._profiles

    def _load_or_create_profile(self, profile_name: str) -> TrackingProfile:
        """Load in any missing data or create a new profile.
        This is in the place of `__missing__`, as the profile name gets
        sanitised before it reaches that point.
        """
        filename = get_filename(profile_name)
        sanitised = sanitise_profile_name(profile_name)
        if os.path.exists(filename):
            profile = TrackingProfile.load(filename)
            if profile is None:
                raise KeyError(profile_name)
        else:
            profile = TrackingProfile()
        self._profiles[sanitised] = profile
        self._evict(keep_loaded=sanitised)

        # Update the data
        if not profile.name or profile_name != sanitised:
            profile.name = profile_name
        profile._last_accessed = time.time()

        # Force disabled profile config
        if profile_name == TRACKING_DISABLE:
            profile.config.track_mouse = False
            profile.config.track_keyboard = False
            profile.config.track_gamepad = False
            profile.config.track_network = False

        return profile

    def _evict(self, keep_loaded: str) -> None:
        """Unload if too many profiles are loaded into memory at once.
        The argument to `keep_loaded` must be sanitised already.
        """
        sanitised = sanitise_profile_name(keep_loaded)
        data = ((profile.is_modified,  # Sort modified profiles first
                 profile._last_accessed,  # Sort by recently accessed
                 name, profile)
                for name, profile in self._profiles.items())

        for i, (is_modified, load_time, name, profile) in enumerate(sorted(data, reverse=True)):
            if i < self.max_profiles or is_modified or name == sanitised:
                continue
            del self._profiles[name]


def sanitise_profile_name(profile_name: str) -> str:
    """Get the sanitised version of a profile name."""
    return re.sub(r'[^a-zA-Z0-9]', '', profile_name.lower())


def get_filename(profile_name: str) -> str:
    """Get the filename for a profile."""
    return os.path.join(PROFILE_DIR, f'{sanitise_profile_name(profile_name)}.{EXTENSION}')


def get_profile_names() -> dict[str, str]:
    """Get all the profile_names, ordered by modified time."""
    if not os.path.exists(PROFILE_DIR):
        return {}
    files = []
    for file in os.scandir(PROFILE_DIR):
        if os.path.splitext(file.name)[1] != f'.{EXTENSION}':
            continue
        profile_name = TrackingProfile.get_name(file.path)
        if profile_name is not None:
            files.append((file.stat().st_mtime, profile_name, os.path.splitext(file.name)[0]))
    return {filename: profile_name for modified, profile_name, filename in sorted(files, reverse=True)}
