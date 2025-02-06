import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterator, TextIO

from .constants import BASE_DIR, REPO_DIR, TRACKING_DISABLE, TRACKING_IGNORE, TRACKING_WILDCARD


RECOGNISED_EXTENSIONS = ['exe', 'bin', 'app', 'scr', 'com']

DEFAULT_TEXT = (
    '// Add any applications you want to be tracked here.\n'
    '// Two separate applications can have the same name, '
    'and will be tracked under the same file.\n'
    '// Put each app on a new line, in the format "MyGame.exe: Game Name". '
    'The executable file is case sensitive.\n'
    '// You may also limit it to a certain window name, '
    'for example if the game uses a generic executable name.\n'
    '// This would work like "Play.exe[MyGame]: Game Name". '
    f'You may use "{TRACKING_WILDCARD}" at the start or end of "MyGame" as a wildcard.\n'
    '// If the executable or window name is the same as the game name,'
    ' providing the game name is not required.\n'
    '// To turn off tracking for a particular application, '
    f'use "{TRACKING_DISABLE}" as its name.\n'
    '// To ignore tracking when a window name is a match '
    f'(such as a splash screen), use "{TRACKING_IGNORE}" as its name.'
)

LOCAL_PATH = BASE_DIR / 'AppList.txt'

REPO_PATH = REPO_DIR / 'config' / 'AppList.txt'

APP_PATTERN = re.compile('^([^:\[\]]+)(?:\[([^\]]*)\])?(?::\s*(.*))?$')


def _parse_data(f: TextIO) -> dict[str, dict[str | None, str]]:
    """Parse data from a file."""
    result = defaultdict(dict)
    for line in filter(bool, map(str.strip, f)):

        # Skip comments
        if line.startswith('//'):
            continue

        exe, title, name = APP_PATTERN.match(line).groups()
        if name is None:
            if title is None:
                name = exe.replace(TRACKING_WILDCARD, '').strip()
            else:
                name = title.replace(TRACKING_WILDCARD, '').strip()

        result[exe.replace('\\', '/').lstrip('/')][title] = name
    return dict(result)


def _prepare_data(data: dict[str, dict[str | None, str]]) -> Iterator[str]:
    """Prepare data to be saved to the file."""
    yield DEFAULT_TEXT
    yield ''

    for exe, data in sorted(data.items(), key=lambda kv: kv[0].lower()):
        for title, name in sorted(data.items(), key=lambda kv: (kv[0] is not None, kv[0])):
            if title is None:
                if name == exe:
                    name = None
            elif name == title:
                name = None

            if title is None:
                if name is None:
                    yield exe
                else:
                    yield f'{exe}: {name}'
            elif name is None:
                yield f'{exe}[{title}]'
            else:
                yield f'{exe}[{title}]: {name}'


def _to_pattern(text: str) -> str:
    """Convert wildcarded text to a compiled regex pattern."""
    return re.escape(text).replace(re.escape(TRACKING_WILDCARD), '.*')


class AppList:
    """Parse a list of applications and provide a way to match them.
    This is a rewrite of the legacy `mousetracks.applications.AppList`.

    Multiple input formats are supported:
        Application.exe
        Application.exe: Name
        Application.exe[Title]
        Application.exe[Title]: Name
        path/Application.exe
        App<*>.exe
        Application.exe[<*> - Title]

    If a name is given, then that's what the profile will be called. If
    not given, then it will use the title if available, otherwise the
    executable name.

    If the title is not given, then any title will match.
    A partial path can be given to the executable.
    The wildcard <*> can be used on the executable name or title.

    Unsupported:
        - Absolute paths
        - Wildcards with partial paths
    """

    def __init__(self) -> None:
        self._path_executables: dict[str, list[str]] = defaultdict(list)
        self._wildcard_executables: dict[str, re.Pattern] = {}
        self._wildcard_titles: dict[str, dict[str, re.Pattern]] = defaultdict(dict)
        self.data: dict[str, dict[str | None, str]] = defaultdict(dict)

        self.load(REPO_PATH)
        if LOCAL_PATH.exists():
            self.load(LOCAL_PATH)

    def load(self, path: Path | str) -> None:
        """Load the contents from disk."""
        with open(path, 'r', encoding='utf-8') as f:
            self.import_(_parse_data(f))

    def import_(self, data: dict[str, dict[str | None, str]]):
        for exe, titles in data.items():
            self.data[exe].update(titles)

            if TRACKING_WILDCARD in exe:
                if '/' in exe:
                    raise NotImplementedError(f'wildcards not supported with paths: {exe}')
                self._wildcard_executables[exe] = re.compile(_to_pattern(exe))

            if '/' in exe:
                self._path_executables[os.path.basename(exe)].append(exe)

            for title in titles:
                if title is not None and TRACKING_WILDCARD in title:
                    self._wildcard_titles[exe][title] = re.compile( _to_pattern(title))


    def save(self) -> None:
        """Save the sorted file contents to disk."""
        with open(LOCAL_PATH, 'w', encoding='utf-8') as f:
            f.write('\n'.join(_prepare_data(self.data)))

    def _match_exe(self, exe: str) -> Iterator[tuple[dict[str | None, str], str] | None]:
        """Find all matches for an executable."""
        # Direct match
        if exe in self.data:
            yield self.data[exe], exe
        exe = exe.replace('\\', '/')

        if '/' in exe:
            basename = os.path.basename(exe)
            # Direct match (without path)
            if basename in self.data:
                yield self.data[basename], exe
        else:
            basename = exe

        # Path match
        for path in self._path_executables.get(basename, []):
            if exe.lower().endswith(path.lower()) or path.lower().endswith(exe.lower()):
                yield self.data[path], exe
                break

        # Wildcard match
        for exe_, pattern in self._wildcard_executables.items():
            if pattern.match(exe):
                yield self.data[exe_], exe_
                break


    def match(self, exe: str, title: str | None = None) -> str | None:
        """Find if there is a match for the given executable / title.
        The name of the application will be returned.
        """
        matches = tuple(self._match_exe(exe))

        if title is not None:
            # Title direct match
            for data, exe in matches:
                if title in data:
                    return data[title]

            # Title wildcard match
            for data, exe in matches:
                if exe in self._wildcard_titles:
                    for title_, pattern in self._wildcard_titles[exe].items():
                        if pattern.match(title):
                            return data[title_]

        # Match exe only
        for data, exe in matches:
            if None in data:
                return data[None]

        # No match
        return None


# Some quick tests for debugging
if __name__ == '__main__':
    applist = AppList()

    applist.save()

    applist.data.clear()
    applist._wildcard_executables.clear()
    applist._wildcard_titles.clear()
    applist._path_executables.clear()

    applist.data['notepad.exe'] = {None: 'Notepad',
                                   'AppList.txt - Notepad': 'AppList',
                                   '<*> - Notepad': 'New'}
    applist._wildcard_titles = {'notepad.exe': {'<*> - Notepad': re.compile(_to_pattern('<*> - Notepad'))}}
    applist.data['test/myapp.exe'] = {None: 'Test App'}
    applist._path_executables['myapp.exe'].append('test/myapp.exe')
    applist.data['<*>paint.exe'] = {None: 'MS Paint'}
    applist._wildcard_executables['<*>paint.exe'] = re.compile(_to_pattern('<*>paint.exe'))

    assert applist.match('notepad.exe') == 'Notepad'
    assert applist.match('notepad.exe', '') == 'Notepad'
    assert applist.match('notepad.exe', 'AppList.txt - Notepad') == 'AppList'
    assert applist.match('notepad.exe', 'new.txt - Notepad') == 'New'
    assert applist.match('win/notepad.exe') == 'Notepad'
    assert applist.match('myapp.exe') == 'Test App'
    assert applist.match('test/myapp.exe') == 'Test App'
    assert applist.match('path/test/myapp.exe') == 'Test App'
    assert applist.match('other/myapp.exe') == None
    assert applist.match('mspaint.exe') == 'MS Paint'

    # # Not supported
    # applist.data['Firefox/Firefox.<*>.exe'] = {None: 'Firefox'}
    # applist._wildcard_executables['Firefox/Firefox.<*>.exe'] = re.compile(_to_pattern('Firefox/Firefox.<*>.exe'))
    # assert applist.match('Firefox.1.exe') == 'Firefox'
    # assert applist.match('Firefox/Firefox.1.exe') == 'Firefox'
    # assert applist.match('Mozilla/Firefox/Firefox.1.exe') == 'Firefox'

    # applist.data['C:/Python311/python.exe'] = {None: 'Python'}
    # assert applist.match('python.exe') == 'Python'
    # assert applist.match('C:/Python311/python.exe') == 'Python'
