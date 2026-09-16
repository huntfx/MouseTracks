import os
from dataclasses import dataclass
from typing import Literal

from .constants import PROFILE_EXT, RECORDING_EXT
from .context import CTX
from .file import TrackingProfile, get_filename


IMPORT_TITLE = 'MouseTracks Profile Import'

IMPORT_MESSAGE = 'Do you want to import the profile "{profile_name}"?'

IMPORT_PROFILE_FILETYPE_ERROR = f'Mousetracks can only import valid {PROFILE_EXT} profile files.'

IMPORT_PLAYBACK_MULTIPLE_ERROR = f'Mousetracks can only play a single {RECORDING_EXT} recording file.'

IMPORT_LEGACY_WARNING = 'This is a legacy profile format. Only import legacy profiles from sources you trust, as loading them is not guaranteed to be safe.'


class ProfileImporter:
    """Check and import a profile from disk.

    Note that this allows for legacy profiles, so any guards to prevent
    loading must be done before.
    """

    def __init__(self, path: str | os.PathLike):
        self._name: str | None = None
        self._path = str(path)

    @property
    def profile_name(self) -> str:
        """Get the profile name."""
        if self._name is not None:
            return self._name
        if name := TrackingProfile.get_name(self._path):
            return name
        return os.path.splitext(os.path.basename(self._path))[0]

    @profile_name.setter
    def profile_name(self, name: str) -> None:
        """Set a new profile name."""
        self._name = name

    @property
    def is_legacy(self) -> bool:
        """Determine if the profile is legacy."""
        return TrackingProfile.is_file_legacy(self._path)

    @property
    def path(self) -> str:
        """Get the expected file path of the profile."""
        return get_filename(self.profile_name)

    def exists(self) -> bool:
        """Determine if the profile currently exists."""
        if not CTX.profile_dir.exists():
            return False
        return os.path.basename(self.path).lower() in map(str.lower, os.listdir(CTX.profile_dir))

    def import_profile(self) -> TrackingProfile | None:
        """Import and save a profile to the data directory."""
        return TrackingProfile.import_file(self._path, self.profile_name)


@dataclass
class ImportResultDisplay:
    imported: list[str]
    skipped: list[str]
    exists: list[str]
    failed: list[str]

    @property
    def level(self) -> Literal['info'] | Literal['warning'] | Literal['error']:
        """Get the recommended log level."""
        if self.imported and not self.failed:
            return 'info'
        if self.imported:
            return 'warning'
        if self.failed:
            return 'error'
        return 'warning'

    @property
    def message(self) -> str:
        """Generate a short message."""
        if self.imported and not self.failed:
            return 'Profile import complete.'
        if self.imported:
            return 'Profile import finished with errors.'
        if self.failed:
            return 'Profile import failed.'
        return 'Profile import skipped.'

    @property
    def detail(self) -> str:
        """Generate a detailed message."""
        parts: list[str] = []
        if self.imported:
            if parts:
                parts.append('')
            parts.append('Imported:')
            for mtk in self.imported:
                parts.append(f' - {mtk}')
        if self.exists:
            if parts:
                parts.append('')
            parts.append('Already Exists:')
            for mtk in self.exists:
                parts.append(f' - {mtk}')
        if self.skipped:
            if parts:
                parts.append('')
            parts.append('Skipped:')
            for mtk in self.skipped:
                parts.append(f' - {mtk}')
        if self.failed:
            if parts:
                parts.append('')
            parts.append('Failed:')
            for mtk in self.failed:
                parts.append(f' - {mtk}')
        return '\n'.join(parts) or 'No profiles were imported.'
