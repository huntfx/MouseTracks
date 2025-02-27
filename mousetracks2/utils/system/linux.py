"""Linux specific functions.

I have next to no Linux experience, so making notes here.

Arch Linux:
    So far unsuccessful at launching the window.
    It gets stuck on creating a QMenuBar.

    https://www.osboxes.org/arch-linux/
    sudo pacman -Sy
    sudo pacman -S python-pip python-setuptools python-wheel python-build base-devel
    sudo pacman -S git
    sudo pacman -S qt5-base qt5-x11extras xcb-util xcb-util-keysyms xcb-util-wm xcb-util-image xcb-util-renderutil
        (may not be required)
    sudo pacman -S xcb-util-cursor
    cd /home/osboxes
    git clone https://github.com/huntfx/mousetracks
    cd mousetracks
    python -m venv .venv
    source ./.venv/bin/activate
    python launch.py
    deactivate
"""

from Xlib import display


def monitor_locations() -> list[tuple[int, int, int, int]]:
    """Get the location of each monitor.

    Returns:
        List of (x1, y1, x2, y2) tuples representing monitor bounds.
    """
    monitors = []
    d = display.Display()
    root = d.screen().root

    # This is a suggestion from AI and not tested
    try:
        resources = root.xinerama_query_screens()

    # This was available on Arch Linux
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
