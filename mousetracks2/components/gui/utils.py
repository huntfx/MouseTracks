"""General functions being used by the GUI."""

import math
import sys

from ...constants import UPDATES_PER_SECOND


ICON_PATH = 'resources/images/icon.png'
if hasattr(sys, '_MEIPASS'):
    ICON_PATH = f'{sys._MEIPASS}/{ICON_PATH}'


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


def format_ticks(ticks: int) -> str:
    """Convert ticks to a formatted time string."""
    seconds = ticks / UPDATES_PER_SECOND
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)

    return f'{int(days):02}:{int(hours):02}:{int(minutes):02}:{seconds:04.1f}'


def format_bytes(b: int) -> str:
    """Convert bytes to a formatted string."""
    if b < 1024:
        return f'{round(b)} B'
    power = min(7, int(math.log(b) / math.log(1024)))
    adjusted = round(b / 1024 ** power, 2)
    sign = 'KMGTPEZY'[power - 1]
    return f'{adjusted} {sign}B'
