"""Windows specific functions.

This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys

import winreg

from ..constants import IS_EXE


user32 = ctypes.windll.user32

SM_CXSCREEN = 0

SM_CYSCREEN = 1

MONITORINFOEX = ctypes.wintypes.RECT

HMONITOR = ctypes.wintypes.HANDLE

HDC = ctypes.wintypes.HDC

LPARAM = ctypes.wintypes.LPARAM

MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, HMONITOR, HDC, ctypes.POINTER(MONITORINFOEX), LPARAM)


def cursor_position() -> tuple[int, int] | None:
    """Get the current mouse position.

    Returns:
        (x, y) as integers
        None in the case of any error
    """
    point = ctypes.wintypes.POINT()
    if user32.GetCursorPos(ctypes.byref(point)):
        return point.x, point.y
    return None


def main_monitor_resolution() -> tuple[int, int]:
    """Get the main screen resolution.
    Any secondary screens will be ignored.
    """
    return (user32.GetSystemMetrics(SM_CXSCREEN),
            user32.GetSystemMetrics(SM_CYSCREEN))


def monitor_locations() -> list[tuple[int, int, int, int]]:
    """Get the location of each monitor.

    Returns:
        List of (x1, y1, x2, y2) tuples representing monitor bounds.
    """
    monitors: list[tuple[int, int, int, int]] = []

    def callback(hMonitor: HMONITOR, hdc: HDC, lprcMonitor: ctypes._Pointer[MONITORINFOEX], lParam: LPARAM) -> int:
        """Callback function for EnumDisplayMonitors."""
        rect = lprcMonitor.contents
        monitors.append((rect.left, rect.top, rect.right, rect.bottom))
        return 1  # Continue enumeration

    user32.EnumDisplayMonitors(0, None, MonitorEnumProc(callback), 0)
    return monitors


def check_key_press(key: int) -> bool:
    """Check if a key is being pressed.
    This also supports mouse clicks using win32con.VK_[L/M/R]BUTTON.

    Returns:
        True/False if the selected key has been pressed or not.
    """
    return user32.GetKeyState(key) < 0


class AutoRun:
    """Handle running the application on startup."""

    PATH = r'Software\Microsoft\Windows\CurrentVersion\Run'

    def __init__(self, executable: str = os.path.abspath(sys.argv[0]), name: str = 'MouseTracks'):
        self.executable = executable
        if not IS_EXE:
           raise ValueError('running on startup not supported when running as a script')
        self.name = name

    def __bool__(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.PATH, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, self.name)
                return True
        except OSError:
            return False

    def __call__(self, enable: bool) -> None:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.PATH, 0, winreg.KEY_WRITE) as key:
            if enable:
                winreg.SetValueEx(key, self.name, 0, winreg.REG_SZ, self.executable)
            else:
                winreg.DeleteValue(key, self.name)

    @classmethod
    def from_name(cls, name: str) -> str | None:
        """Get the executable for a given name if it exists."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, cls.PATH, 0, winreg.KEY_READ) as key:
                exe = winreg.QueryValueEx(key, name)[0]
                if os.path.exists(exe):
                    return exe
                return None
        except OSError:
            return None
