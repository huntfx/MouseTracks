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


def format_ticks(ticks: float, ups: int = UPDATES_PER_SECOND, accuracy: int = 1, length: int = 5) -> str:
    """Convert ticks to a formatted time string."""
    seconds = ticks / ups
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    years, days = divmod(days, 365)

    # If a length is set, calculate which items to show
    diff = (5 if years else 4 if days else 3 if hours else 2 if minutes else 1) - length

    # Merge the smaller data into the minimum value
    if diff > 0:
        minutes += seconds / 60
    if diff > 1:
        hours += minutes / 60
    if diff > 2:
        days += hours / 24
    if diff > 3:
        years += days / 365

    # Build up the string
    parts = []
    if diff < 1:
        parts.append(f'{seconds:.{accuracy * (diff <= 0)}f}s')
    if diff < 2 and (diff == 1 or minutes or hours or days or years):
        parts.append(f'{minutes:.{accuracy * (diff == 1)}f}m')
    if diff < 3 and (diff == 2 or hours or days or years):
        parts.append(f'{hours:.{accuracy * (diff == 2)}f}h')
    if diff < 4 and (diff == 3 or days or years):
        parts.append(f'{days:.{accuracy * (diff == 3)}f}d')
    if diff < 5 and (diff == 4 or years):
        parts.append(f'{years:.{accuracy * (diff == 4)}f}y')
    return ' '.join(reversed(parts))


def format_bytes(b: int) -> str:
    """Convert bytes to a formatted string."""
    if b < 1024:
        return f'{round(b)} B'
    power = min(7, int(math.log(b) / math.log(1024)))
    adjusted = round(b / 1024 ** power, 2)
    sign = 'KMGTPEZY'[power - 1]
    return f'{adjusted} {sign}B'


def format_network_speed(b: int) -> str:
    """Convert bytes to network speed."""
    return f'{format_bytes(b * 8)[:-1]}bps'
