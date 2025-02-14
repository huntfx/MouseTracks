"""Windows specific functions."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
from typing import Any

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


class PID:
    """Class to manage a process ID."""

    def __init__(self, pid: int) -> None:
        self.pid = pid

    def __int__(self) -> int:
        return self.pid

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, int):
            return self.pid == other
        if isinstance(other, PID):
            return self.pid == other.pid
        return False

    @property
    def hwnds(self) -> list[int]:
        """Find all window handles for the given process ID.

        This shouldn't be required often, but certain applications such as
        "HP Anyware Client" have multiple windows with different hwnds.
        """
        hwnds: list[int] = []
        if not self.pid:
            return hwnds

        def enum_windows_callback(hwnd, lparam):
            process_id = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if process_id.value == self.pid:
                hwnds.append(hwnd)
            return True  # Continue enumeration

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)

        return [hwnd for hwnd in sorted(hwnds) if user32.IsWindowVisible(hwnd)]

    @property
    def executable(self) -> str:
        """Get the executable file path of the process."""
        h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, self.pid)
        if not h_process:
            return ''
        buffer = ctypes.create_unicode_buffer(512)
        psapi.GetModuleFileNameExW(h_process, None, buffer, len(buffer))
        kernel32.CloseHandle(h_process)
        return buffer.value.strip()

    @property
    def rect(self) -> tuple[int, int, int, int]:
        """Get the bounding rectangle of all windows belonging to this process."""
        left = top = 2 << 31
        right = bottom = -2 << 31

        valid = False
        for hwnd in self.hwnds:
            rect = ctypes.wintypes.RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                valid = True
                left = min(left, rect.left)
                top = min(top, rect.top)
                right = max(right, rect.right)
                bottom = max(bottom, rect.bottom)

        if valid:
            return left, top, right, bottom
        return 0, 0, 0, 0

    @property
    def rects(self) -> list[tuple[int, int, int, int]]:
        """Get the rects of each window handle."""
        return [handle.rect for handle in map(WindowHandle, self.hwnds)]

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


class WindowHandle:
    """Class to manage a window handle and retrieve relevant information.
    Note that a PID may have multiple window handles.
    """

    def __init__(self, hwnd: int, pid: int | None = None) -> None:
        self.hwnd = hwnd

        # Get Process ID
        if pid is None:
            process_id = ctypes.wintypes.DWORD()
            self.thread_id = user32.GetWindowThreadProcessId(self.hwnd, ctypes.byref(process_id))
            pid = process_id.value
        self.pid = PID(pid)

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
