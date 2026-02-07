"""Code required for updates with minimal imports."""

import json
import platform
import struct
import sys
import time
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

from .network import safe_download_file
from ..constants import UNTRUSTED_EXT
from ..version import VERSION

if sys.platform == 'win32':
    from ..sign import verify_signature, failed_signature_verification
else:
    def verify_signature(file_path: Path | str, write_untrusted: bool = True) -> bool: return True
    def failed_signature_verification(file_path: Path | str) -> bool: return False


RELEASES_URL = 'https://api.github.com/repos/huntfx/MouseTracks/releases'

_CACHE: dict[str, tuple[float, dict]] = {}

_CACHE_REFRESH_SECONDS = 3600


def _get_release_data(version: str = 'latest') -> dict | None:
    """Download the data for a specific release."""
    if version == 'latest':
        url = f'{RELEASES_URL}/{version}'
    else:
        url = f'{RELEASES_URL}/tags/v{version}'

    # Check if cached
    if url in _CACHE:
        updated, data = _CACHE[url]
        if updated + _CACHE_REFRESH_SECONDS > time.time():
            return data

    # Fetch the data
    try:
        with urlopen(url, timeout=5) as response:
            release = json.load(response)

    except (URLError, json.decoder.JSONDecodeError) as e:
        print(f'Error reading version {version}: {e}')
        return None

    # Cache the data
    _CACHE[url] = (time.time(), release)
    return release


def get_latest_version() -> str:
    """Get the latest version available."""
    release = _get_release_data()
    if not release:
        return VERSION

    tag = release.get('tag_name')
    if tag is None:
        return VERSION
    return tag.lstrip('v')


def is_latest_version() -> bool:
    """Determine if the current version is the latest.
    If the current version is even newer, then it will be treated as latest.
    """
    latest = get_latest_version()
    if latest == VERSION:
        return True
    try:
        return tuple(map(int, latest.split('.'))) <= tuple(map(int, VERSION.split('.')))
    except ValueError:
        return True


def get_download_link(version: str = 'latest') -> str | None:
    """Get the link to download the correct executable for the current OS."""
    release = _get_release_data(version)
    if not release:
        return None

    suffix = _get_platform_suffix()
    for asset in release.get('assets', []):
        if asset['name'].endswith(f'-{suffix}'):
            return asset['browser_download_url']
    return None


def generate_exe_name(version: str = VERSION, with_extension: bool = True) -> str:
    """Generate the executable path."""
    return f'MouseTracks-{version}-{_get_platform_suffix(with_extension)}'


def _get_platform_suffix(with_extension: bool = True) -> str:
    """Generate the file suffix from the platform data."""
    if sys.platform == 'win32':
        os_name = 'windows'
        ext = '.exe'
    elif sys.platform.startswith('linux'):
        os_name = 'linux'
        ext = ''
    elif sys.platform == 'darwin':
        os_name = 'macos'
        ext = ''
    else:
        raise NotImplementedError(sys.platform)

    if platform.machine().lower() in ('arm64', 'aarch64'):
        arch = 'arm64'
    else:
        is_64bit = (struct.calcsize('P') * 8) == 64
        arch = 'x64' if is_64bit else 'x86'

    if not with_extension:
        ext = ''

    return f'{os_name}-{arch}{ext}'


def _split_exe_name(path: str | Path, include_untrusted: bool = False,
                    ) -> tuple[tuple[int, ...], str, str] | None:
    """Get the components of the executable path.
    Returns the version, os name and architecture.
    """
    path = Path(path)
    if not path.is_file():
        return None

    # Get any "unstrusted" files
    if path.suffix == UNTRUSTED_EXT:
        if not include_untrusted:
            return None
        path = path.with_suffix('')

    name = path.stem
    if not name.startswith('MouseTracks-'):
        return None

    parts = name.split('-')
    try:
        version = tuple(map(int, parts[1].split('.')))
        os_name = parts[2]
        arch = parts[3]
    except (IndexError, ValueError):
        return None
    return version, os_name, arch


def download_version(folder: Path | str, version: str = 'latest') -> Path | None:
    """Download a version of MouseTracks for the current OS.
    If the download fails the signature check, it will not be kept.
    """
    executable_link = get_download_link(version)
    if executable_link is None:
        return None

    executable_path = Path(folder) / Path(executable_link).name

    # If it exists, then return without any extra checks
    if executable_path.exists():
        return executable_path

    # Check if signature verification previously failed to avoid redownloading
    if failed_signature_verification(executable_path):
        return None

    if not safe_download_file(executable_link, executable_path):
        return None

    # Check the public key is a match
    if verify_signature(executable_path):
        return executable_path

    # If verification fails, just remove the download
    executable_path.unlink()
    return None


def cleanup_old_executables(folder: Path | str, version: str = VERSION, keep: int = 2) -> None:
    """Delete any executables older than the given version.
    Optionally define a number to keep.
    """
    lower, current, higher = get_local_executables(folder, version, include_untrusted=True)

    # Keep the highest few versions rather than removing everything
    if keep:
        lower = lower[:-keep]

    # Delete the files
    for executable in lower:
        print(f'Removing old executable: {executable}')
        if executable.exists():
            try:
                executable.unlink()
            except OSError as e:
                print(f'Error removing file: {e}')

        untrusted = executable.with_suffix(UNTRUSTED_EXT)
        if untrusted.exists():
            try:
                untrusted.unlink()
            except OSError as e:
                print(f'Error removing file: {e}')


def get_local_executables(folder: Path | str, version: str = VERSION, include_untrusted: bool = False,
                          ) -> tuple[list[Path], Path | None, list[Path]]:
    """Get all the available executables from a path.
    Splits into lower and higher than the current version.
    """
    # Get the split data for the current version
    result = _split_exe_name(generate_exe_name(version))
    if result is None:
        raise RuntimeError(f'unknown error generating version data for {version!r}')

    executable: Path | None = None
    executables_lower: list[tuple[tuple[tuple[int, ...], str, str], Path]] = []
    executables_higher: list[tuple[tuple[tuple[int, ...], str, str], Path]] = []
    for child in Path(folder).iterdir():
        parts = _split_exe_name(child, include_untrusted)
        if parts is not None and parts[1] == result[1] and parts[2] == result[2]:
            if parts[0] < result[0]:
                executables_lower.append((parts, child))
            elif parts[0] > result[0]:
                executables_higher.append((parts, child))
            else:
                executable = child

    return ([path for _, path in sorted(executables_lower)],
            executable,
            [path for _, path in sorted(executables_higher)])
