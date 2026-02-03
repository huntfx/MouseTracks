"""Linux specific functions.

I have no Linux experience, so making notes here of what's required to
get it running.

Arch Linux:
    https://www.osboxes.org/arch-linux/
    > sudo rm /var/lib/pacman/db.lck
    > sudo pacman -Sy archlinux-keyring
    > sudo pacman-key --init
    > sudo pacman-key --populate archlinux
    > sudo pacman-key --refresh-keys  # Not currently required, but leaving for future reference
    > sudo pacman -Syu --overwrite '*'
    > sudo pacman -S git python-pip python-setuptools python-wheel python-build base-devel xcb-util-cursor
    > cd /home/osboxes
    > git clone https://github.com/huntfx/mousetracks
    > cd mousetracks
    > python -m venv .venv
    > source ./.venv/bin/activate
    > pip install --upgrade pip
    > pip install -r requirements.txt
    > python launch.py
    > deactivate

Ubuntu:
    https://www.osboxes.org/ubuntu/
    Login with "Ubuntu on Xorg" session.
    > cd /home/osboxes
    > sudo apt update
    > sudo apt install git python3-venv gcc python3-dev libxcb-cursor-dev -y
    > git clone https://github.com/huntfx/mousetracks
    > cd mousetracks
    > python3 -m venv .venv
    > source ./.venv/bin/activate
    > pip install --upgrade pip
    > pip install -r requirements.txt
    > python3 launch.py
    > deactivate
"""

from __future__ import annotations

import os
import shlex
from contextlib import suppress
from pathlib import Path
from typing import Any, Self

import Xlib.display
import Xlib.xobject

from .base import Window as _Window
from ...constants import SYS_EXECUTABLE
from ...types import Rect, RectList


AUTOSTART_NAME = 'MouseTracks'

AUTOSTART_DIR = Path.home() / '.config' / 'autostart'

AUTOSTART_FILE_PATH = AUTOSTART_DIR / f'{AUTOSTART_NAME.lower()}.desktop'

DESKTOP_FILE_CONTENT = f"""[Desktop Entry]
Type=Application
Name={AUTOSTART_NAME}
Comment=Track mouse, keyboard, and gamepad activity.
Exec={{cmd}}
Icon=input-mouse
Terminal=false
"""


def _get_top_level_window(root: Xlib.xobject.drawable.Window, window: Xlib.xobject.drawable.Window) -> Xlib.xobject.drawable.Window:
    """Traverse to the first window with a title."""
    while True:
        # If the window has a name, it's likely this
        if window.get_wm_name():
            return window

        parent: Xlib.xobject.drawable.Window = window.query_tree().parent

        # If the root is reached, then return the top level window
        if parent.id == root.id:
            return window

        window = parent


def get_focused_window(display: Xlib.display.Display) -> Xlib.xobject.drawable.Window:
    """Get the currently focused window."""
    display = Xlib.display.Display()
    root = display.screen().root
    focus = display.get_input_focus().focus
    return _get_top_level_window(root, focus)


class Window(_Window):
    def __init__(self, display: Xlib.display.Display, window: Xlib.xobject.drawable.Window, **kwargs: Any) -> None:
        self._display = display
        self._window = window
        self._executable: str | None = None
        self._pid: int | None = None

    @classmethod
    def get_focused(cls) -> Self:
        display = Xlib.display.Display()
        window = get_focused_window(display)
        return cls(display, window)

    @property
    def pid(self) -> int:
        if self._pid is None:
            pid_atom: int = self._display.get_atom('_NET_WM_PID')
            pid_property: Xlib.protocol.request.GetProperty | None = self._window.get_property(pid_atom, Xlib.X.AnyPropertyType, 0, 4)

            if pid_property and pid_property.format == 32 and pid_property.value:
                self._pid = pid_property.value[0]
            else:
                self._pid = 0
        return self._pid

    @pid.setter
    def pid(self, pid: int) -> None:
        self._pid = pid

    @property
    def title(self) -> str:
        return self._window.get_wm_name() or ''

    @property
    def executable(self) -> str:
        if self._executable is None:
            if os.path.lexists(exe_path := f"/proc/{self.pid}/exe"):
                self._executable = os.readlink(exe_path)
            else:
                self._executable = ''
        return self._executable

    @property
    def _geometry(self) -> Xlib.protocol.request.GetGeometry:
        """Get the window geometry.
        Available properties are "x", "y", "width" and "height".

        Note that this may only be relative to its parent. Currently
        that's not an issue as it's only being used on top level
        windows, but in the future it may require use of
        `translate_coords(root, 0, 0)` instead.
        """
        return self._window.get_geometry()

    @property
    def rects(self) -> RectList:
        geo = self._geometry
        return RectList([Rect.from_size(width=geo.width, height=geo.height, x=geo.x, y=geo.y)])

    @property
    def position(self) -> tuple[int, int]:
        geo = self._geometry
        return (geo.x, geo.y)

    @property
    def size(self) -> tuple[int, int]:
        geo = self._geometry
        return (geo.width, geo.height)


def get_autostart() -> str | None:
    """Determine if running on startup."""
    try:
        with AUTOSTART_FILE_PATH.open('r', encoding='utf-8') as f:
            exec_line = next(filter(lambda line: 'Exec=' in line, f))
            cmd = exec_line.split('Exec=', 1)[1].strip()
    except FileNotFoundError:
        return None
    except (StopIteration, IndexError):
        pass
    return cmd


def set_autostart(*args: str) -> None:
    """Set an executable to run on startup."""
    cmd = shlex.join([SYS_EXECUTABLE] + list(args))
    content = DESKTOP_FILE_CONTENT.format(cmd=cmd)
    try:
        AUTOSTART_DIR.mkdir(parents=True, exist_ok=True)
        with AUTOSTART_FILE_PATH.open('w', encoding='utf-8') as f:
            f.write(content)

        # Make the file executable
        AUTOSTART_FILE_PATH.chmod(0o755)

    except OSError as e:
        print(f'Error: Could not set autostart: {e}')


def remove_autostart() -> None:
    """Stop an executable running on startup."""
    with suppress(FileNotFoundError):
        AUTOSTART_FILE_PATH.unlink()
