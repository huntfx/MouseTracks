"""General functions being used by the GUI."""

import math

from ..constants import UPDATES_PER_SECOND, REPO_DIR


ICON_PATH = str(REPO_DIR / 'resources' / 'images' / 'icon.png')


def format_distance(pixels: float, ppi: float = 96.0) -> str:
    """Convert mouse distance to text"""
    inches = pixels / ppi
    cm = inches * 2.54
    m = cm / 100
    km = m / 1000
    if km > 1:
        return f'{round(km, 3)} km'
    if m > 1:
        return f'{round(m, 3)} m'
    return f'{round(cm, 3)} cm'


def format_ticks(ticks: float, ups: int = UPDATES_PER_SECOND, accuracy: int = 1) -> str:
    """Convert ticks to a formatted time string."""
    seconds = ticks / ups
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    parts = [f'{seconds:03.{accuracy}f}s']
    if minutes or hours or days:
        parts.append(f'{int(minutes)}m')
        if hours or days:
            parts.append(f'{int(hours)}h')
            if days:
                parts.append(f'{int(days)}d')
    return ' '.join(reversed(parts))


def format_bytes(b: int) -> str:
    """Convert bytes to a formatted string."""
    if b < 1024:
        return f'{round(b)} B'
    power = min(7, int(math.log(b) / math.log(1024)))
    adjusted = round(b / 1024 ** power, 2)
    sign = 'KMGTPEZY'[power - 1]
    return f'{adjusted} {sign}B'
