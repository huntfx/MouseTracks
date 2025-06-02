import json
from urllib.request import urlopen
from urllib.error import URLError

from .config.cli import CLI
from .version import VERSION


RELEASES_URL = 'https://api.github.com/repos/huntfx/MouseTracks/releases'


def get_latest_version() -> str:
    """Get the latest version available.
    This assumes the latest release is the latest version.
    """
    if CLI.offline:
        return VERSION
    try:
        with urlopen(RELEASES_URL, timeout=5) as response:
            data = json.load(response)
    except (URLError, json.decoder.JSONDecodeError):
        return VERSION
    if not data:
        return VERSION

    tag = data[0]['tag_name']
    if tag is None:
        return VERSION
    return tag.lstrip('v')


def is_latest_version() -> bool:
    """Determine if the current version is the latest."""
    return get_latest_version() == VERSION
