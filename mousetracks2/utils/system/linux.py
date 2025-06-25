"""Linux specific functions.

I have no Linux experience, so making notes here of what's required to
get it running.

Arch Linux:
    https://www.osboxes.org/arch-linux/
    > rm /var/lib/pacman/db.lck
    > sudo pacman -Sy
    > sudo pacman -S git
    > cd /home/osboxes
    > git clone https://github.com/huntfx/mousetracks
    > cd mousetracks
    > sudo pacman -S python-pip python-setuptools python-wheel python-build base-devel
    > python -m venv .venv
    > source ./.venv/bin/activate
    > pip install --upgrade pip
    > sudo pacman -S xcb-util-cursor
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

Issues:
    Non alphanumeric keys have a totally different mapping.
    Modifier keys are way out of range (close to 65535).
"""

from __future__ import annotations

import os
import traceback
from typing import Any, Self

import Xlib.display
import Xlib.xobject

from .placeholders import Window as _Window


def monitor_locations() -> list[tuple[int, int, int, int]]:
    """Get the location of each monitor.

    Returns:
        List of (x1, y1, x2, y2) tuples representing monitor bounds.
    """
    monitors = []
    display = Xlib.display.Display()
    root = display.screen().root

    # This is a suggestion from AI and not tested
    try:
        resources = root.xinerama_query_screens()

    # This was available on Ubuntu and Arch Linux
    except AttributeError:
        res = root.xrandr_get_monitors()
        for mon in res._data['monitors']:
            x1, y1 = mon['x'], mon['y']
            x2, y2 = x1 + mon['width_in_pixels'], y1 + mon['height_in_pixels']
            monitors.append((x1, y1, x2, y2))

    else:
        for screen in resources:
            x1, y1 = screen.x_org, screen.y_org
            x2, y2 = x1 + screen.width, y1 + screen.height
            monitors.append((x1, y1, x2, y2))

    return monitors


def _get_top_level_window(root: Xlib.xobject.drawable.Window, window: Xlib.xobject.drawable.Window) -> Xlib.xobject.drawable.Window:
    """Traverse up to the top level window."""
    while True:
        parent: Xlib.xobject.drawable.Window = window.query_tree().parent
        if parent.id == root.id:
            return parent
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
    def rects(self) -> list[tuple[int, int, int, int]]:
        geometry = self._geometry
        return [(geometry.x, geometry.y, geometry.x + geometry.width, geometry.y + geometry.height)]

    @property
    def position(self) -> tuple[int, int]:
        geometry = self._geometry
        return (geometry.x, geometry.y)

    @property
    def size(self) -> tuple[int, int]:
        geometry = self._geometry
        return (geometry.width, geometry.height)
