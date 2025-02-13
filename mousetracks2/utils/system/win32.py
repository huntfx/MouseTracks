"""Windows specific functions."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys

import winreg

from ...constants import IS_EXE


user32 = ctypes.windll.user32

kernel32 = ctypes.windll.kernel32

psapi = ctypes.windll.psapi

SM_CXSCREEN = 0

SM_CYSCREEN = 1

SW_HIDE = 0

SW_RESTORE = 9

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

MONITORINFOEX = ctypes.wintypes.RECT

HMONITOR = ctypes.wintypes.HANDLE

HDC = ctypes.wintypes.HDC

LPARAM = ctypes.wintypes.LPARAM

MonitorEnumProc = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, HMONITOR, HDC, ctypes.POINTER(MONITORINFOEX), LPARAM)

REG_STARTUP = r'Software\Microsoft\Windows\CurrentVersion\Run'


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


def get_window_handle(console: bool = False) -> int:
    """Get a window handle."""
    if console:
        return kernel32.GetConsoleWindow()

    # Walk through the parent windows
    hwnd = user32.GetForegroundWindow()
    while parent := user32.GetParent(hwnd):
        hwnd = parent
    return hwnd


class WindowHandle:
    """Class to manage a window handle and retrieve relevant information."""

    def __init__(self, hwnd: int) -> None:
        self.hwnd = hwnd

        # Get Process ID
        process_id = ctypes.wintypes.DWORD()
        self.thread_id = user32.GetWindowThreadProcessId(self.hwnd, ctypes.byref(process_id))
        self.pid = process_id.value

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """Get the window's rect coordinates."""
        rect = ctypes.wintypes.RECT()
        if user32.GetWindowRect(self.hwnd, ctypes.byref(rect)):
            return rect.left, rect.top, rect.right, rect.bottom
        return 0, 0, 0, 0

    @property
    def position(self) -> tuple[int, int]:
        """Get the position of the window."""
        x1, y1, x2, y2 = self.rect
        return x1, y1

    @property
    def size(self) -> tuple[int, int]:
        """Get the size of the window."""
        x1, y1, x2, y2 = self.rect
        return x2 - x1, y2 - y1

    @property
    def title(self) -> str:
        """Get the window's title."""
        length = user32.GetWindowTextLengthW(self.hwnd)
        if not length:
            return ''
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(self.hwnd, buff, length + 1)
        return buff.value

    @title.setter
    def title(self, title: str) -> None:
        """Set the window title."""
        user32.SetWindowTextW(self.hwnd, title)

    @property
    def exe(self) -> str:
        """Get the executable file path of the process owning this window."""
        h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, self.pid)
        if not h_process:
            return ''
        buffer = ctypes.create_unicode_buffer(512)
        psapi.GetModuleFileNameExW(h_process, None, buffer, len(buffer))
        kernel32.CloseHandle(h_process)
        return buffer.value.strip()

    @property
    def visible(self) -> bool:
        """Check if the window is visible."""
        return bool(user32.IsWindowVisible(self.hwnd))

    @property
    def enabled(self) -> bool:
        """Check if the window is enabled."""
        return bool(user32.IsWindowEnabled(self.hwnd))

    def show(self, foreground: bool = False) -> None:
        """Restore a window from being minimised."""
        user32.ShowWindow(self.hwnd, SW_RESTORE)
        if foreground:
            user32.SetForegroundWindow(self.hwnd)

    def hide(self) -> None:
        """Hide a window from the task bar."""
        user32.ShowWindow(self.hwnd, SW_HIDE)


def get_autostart(name: str) -> str | None:
    """Determine if running on startup."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_STARTUP, 0, winreg.KEY_READ) as key:
            exe: str = winreg.QueryValueEx(key, name)[0]
            flag_idx = exe.index(' -')
            if flag_idx > 0:
                exe = exe[:flag_idx].rstrip(' ')
            if os.path.exists(exe):
                return os.path.abspath(exe)
            return None
    except OSError:
        return None


def set_autostart(name: str, executable: str, *args: str) -> None:
    """Set an executable to run on startup."""
    if os.path.splitext(executable)[1] != '.exe':
        raise RuntimeError('Running on startup is only supported by the executable build of MouseTracks.')
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_STARTUP, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, ' '.join([executable] + list(args)))


def remove_autostart(name: str) -> None:
    """Stop an executable running on startup."""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_STARTUP, 0, winreg.KEY_WRITE) as key:
        winreg.DeleteValue(key, name)
