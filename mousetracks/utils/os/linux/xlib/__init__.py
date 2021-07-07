"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Linux functions that require Xlib
#Thanks to /u/Astrrum for helping, still needs a lot of work

from __future__ import absolute_import

from Xlib import display
from pyxhook import HookManager


def get_resolution():
    d = display.Display().screen()
    return (d.width_in_pixels, d.height_in_pixels)


def get_cursor_pos():
    d = display.Display().screen().root.query_pointer()
    return (d.root_x, d.root_y)


class _MouseClick(HookManager):
    def __init__(self):
        super(self.__class__, self).__init__()
        self.reset()
        new_hook = HookManager()
        new_hook.MouseAllButtonsDown = self.click
        new_hook.start()

    def click(self, event):
        """Mark buttons as clicked."""
        self.clicks[0] = True

    def return_click(self):
        """Get any pressed buttons and reset."""
        clicks = self.clicks
        self.reset()
        return clicks

    def reset(self):
        """Mark buttons as unclicked."""
        self.clicks = [False]


def get_mouse_click():
    return _CLICKS.return_click()


_CLICKS = _MouseClick()