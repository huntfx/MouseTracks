import math
import os
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Iterator

from .constants import UPDATES_PER_SECOND
from .file import TrackingProfile
from .utils.keycodes import KEYBOARD_CODES, MOUSE_CODES, SCROLL_CODES, GAMEPAD_CODES


class Export:
    """Handle the export of data for a profile."""

    def __init__(self, profile: TrackingProfile) -> None:
        self.profile = profile

    def _daily_stats(self) -> Iterator[tuple[Any, ...]]:
        """Iterate over the data for the daily stats."""
        creation_day = self.profile.created // 86400
        modified_day = self.profile.modified // 86400

        yield ('Date', 'Time (seconds)', 'Active (seconds)', 'Inactive (seconds)',
               'Cursor Distance (pixels)', 'Mouse Clicks', 'Mouse Scrolls',
               'Keyboard Presses', 'Gamepad Presses', 'Download (bytes)', 'Upload (bytes)')
        for i in reversed(range(1 + modified_day - creation_day)):
            # Skip if no data
            if not self.profile.daily_ticks[i, 0]:
                continue

            # Get the date
            timestamp = self.profile.created + i * 86400
            dt = datetime(1970, 1, 1) + timedelta(seconds=timestamp)

            yield (dt.strftime('%Y-%m-%d'),
                   round(self.profile.daily_ticks[i, 0] / UPDATES_PER_SECOND, 2),
                   round(self.profile.daily_ticks[i, 1] / UPDATES_PER_SECOND, 2),
                   round(self.profile.daily_ticks[i, 2] / UPDATES_PER_SECOND, 2),
                   self.profile.daily_distance[i],
                   self.profile.daily_clicks[i],
                   self.profile.daily_scrolls[i],
                   self.profile.daily_keys[i],
                   self.profile.daily_buttons[i],
                   self.profile.daily_download[i],
                   self.profile.daily_upload[i])

    def daily_stats(self, path: str | os.PathLike) -> None:
        """Save a CSV file of the daily stats."""
        with open(path, 'w', encoding='utf-8') as f:
            for i, data in enumerate(self._daily_stats()):
                if i:
                    f.write('\n')
                f.write(','.join(map(str, data)))

    def _mouse_stats(self) -> Iterator[tuple[Any, ...]]:
        yield 'Code', 'Name', 'Press Count', 'Press Time (seconds)'
        for keycode in MOUSE_CODES:
            presses = self.profile.key_presses[keycode]
            held = round(self.profile.key_held[keycode] / UPDATES_PER_SECOND, 2)
            yield int(keycode), str(keycode), presses, held
        for keycode in SCROLL_CODES:
            yield '', str(keycode), self.profile.key_held[keycode], 0

    def mouse_stats(self, path: str | os.PathLike) -> None:
        """Save a CSV file of the mouse stats."""
        with open(path, 'w', encoding='utf-8') as f:
            for i, data in enumerate(self._mouse_stats()):
                if i:
                    f.write('\n')
                f.write(','.join(map(str, data)))

    def _keyboard_stats(self) -> Iterator[tuple[Any, ...]]:
        yield 'Code', 'Key', 'Press Count', 'Press Time (seconds)'
        for keycode in KEYBOARD_CODES:
            presses = self.profile.key_presses[keycode]
            held = round(self.profile.key_held[keycode] / UPDATES_PER_SECOND, 2)
            if presses or held:
                yield int(keycode), str(keycode), presses, held

    def keyboard_stats(self, path: str | os.PathLike) -> None:
        """Save a CSV file of the keyboard stats."""
        with open(path, 'w', encoding='utf-8') as f:
            for i, data in enumerate(self._keyboard_stats()):
                if i:
                    f.write('\n')
                f.write(','.join(map(str, data)))

    def _network_stats(self) -> Iterator[tuple[Any, ...]]:
        """Iterate over the data for the network stats."""
        yield 'Name', 'MAC Address', 'Download (bytes)', 'Upload (bytes)', 'Total (bytes)'
        totals = {mac_address: self.profile.data_download[mac_address]
                               + self.profile.data_upload[mac_address]
                  for mac_address in self.profile.data_interfaces}
        for mac_address, total in sorted(totals.items(), key=lambda kv: kv[1], reverse=True):
            yield (self.profile.data_interfaces[mac_address], mac_address,
                   self.profile.data_download[mac_address],
                   self.profile.data_upload[mac_address], total)

    def network_stats(self, path: str | os.PathLike) -> None:
        """Save a CSV file of the network stats."""
        with open(path, 'w', encoding='utf-8') as f:
            for i, data in enumerate(self._network_stats()):
                if i:
                    f.write('\n')
                f.write(','.join(map(str, data)))

    def _gamepad_stats(self) -> Iterator[tuple[Any, ...]]:
        yield 'Code', 'Name', 'Press Count', 'Press Time (seconds)'
        presses: dict[int, int] = defaultdict(int)
        held: dict[int, int] = defaultdict(int)
        gamepad_codes = {int(math.log2(int(keycode))): str(keycode)
                         for keycode in GAMEPAD_CODES}

        for keycode in gamepad_codes:
            for data in self.profile.button_presses.values():
                presses[keycode] += data[keycode]
            for data in self.profile.button_held.values():
                held[keycode] += data[keycode]

        for keycode, name in sorted(gamepad_codes.items()):
            if presses[keycode] or held[keycode]:
                yield (keycode, name, presses[keycode],
                       round(held[keycode] / UPDATES_PER_SECOND, 2))

    def gamepad_stats(self, path: str | os.PathLike) -> None:
        """Save a CSV file of the gamepad stats."""
        with open(path, 'w', encoding='utf-8') as f:
            for i, data in enumerate(self._gamepad_stats()):
                if i:
                    f.write('\n')
                f.write(','.join(map(str, data)))
