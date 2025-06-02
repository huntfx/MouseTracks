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
