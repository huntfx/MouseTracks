"""Windows specific functions."""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import shlex
import sys
from contextlib import suppress
from typing import Any, Self

import subprocess
import winreg

from .base import Window as _Window, MonitorEventsListener as _MonitorEventsListener
from ...constants import APP_EXECUTABLE
from ...types import Rect, RectList


user32 = ctypes.windll.user32

kernel32 = ctypes.windll.kernel32

psapi = ctypes.windll.psapi

shell32 = ctypes.windll.shell32

SM_CXSCREEN = 0

SM_CYSCREEN = 1

SW_HIDE = 0

SW_RESTORE = 9

WM_QUIT = 0x0012

WM_DISPLAYCHANGE = 0x007E

WM_DEVICECHANGE  = 0x0219

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

BOOL = ctypes.wintypes.BOOL

DWORD = ctypes.wintypes.DWORD

HDC = ctypes.wintypes.HDC

HMONITOR = ctypes.wintypes.HMONITOR

HWND = ctypes.wintypes.HWND

UINT = ctypes.wintypes.UINT

LPARAM = ctypes.wintypes.LPARAM

WPARAM = ctypes.wintypes.WPARAM

LPWSTR = ctypes.wintypes.LPWSTR

RECT = ctypes.wintypes.RECT

MSG = ctypes.wintypes.MSG

LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == ctypes.sizeof(ctypes.c_longlong) else ctypes.c_long

MonitorEnumProc = ctypes.WINFUNCTYPE(BOOL, HMONITOR, HDC, ctypes.POINTER(RECT), LPARAM)

EnumWindowsProc = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)

WndEnumPrpc = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)

WNDPROCTYPE = ctypes.WINFUNCTYPE(LRESULT, HWND, UINT, WPARAM, LPARAM)

HCURSOR = ctypes.wintypes.HANDLE

HICON = ctypes.wintypes.HANDLE

HBRUSH = ctypes.wintypes.HANDLE

DPI_AWARENESS_CONTEXT_UNAWARE = ctypes.wintypes.HANDLE(-1)
DPI_AWARENESS_CONTEXT_SYSTEM_AWARE = ctypes.wintypes.HANDLE(-2)
DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.wintypes.HANDLE(-4)

user32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(DWORD)]
user32.GetWindowThreadProcessId.restype = DWORD

user32.EnumWindows.argtypes = [WndEnumPrpc, LPARAM]
user32.EnumWindows.restype = BOOL

user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = BOOL

user32.GetWindowTextLengthW.argtypes = [HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int

user32.GetWindowTextW.argtypes = [HWND, LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int

user32.SetWindowTextW.argtypes = [HWND, LPWSTR]
user32.SetWindowTextW.restype = BOOL

user32.IsWindowVisible.argtypes = [HWND]
user32.IsWindowVisible.restype = BOOL

user32.IsWindowEnabled.argtypes = [HWND]
user32.IsWindowEnabled.restype = BOOL

user32.ShowWindow.argtypes = [HWND, ctypes.c_int]
user32.ShowWindow.restype = BOOL

user32.SetForegroundWindow.argtypes = [HWND]
user32.SetForegroundWindow.restype = BOOL

user32.GetParent.argtypes = [HWND]
user32.GetParent.restype = HWND

user32.GetForegroundWindow.restype = HWND

kernel32.GetConsoleWindow.restype = HWND

user32.EnumDisplayMonitors.argtypes = [HDC, ctypes.POINTER(RECT), MonitorEnumProc, LPARAM]
user32.EnumDisplayMonitors.restype = BOOL

user32.DefWindowProcW.restype = LRESULT
user32.DefWindowProcW.argtypes = [
    HWND,
    UINT,
    WPARAM,
    LPARAM,
]

user32.SetThreadDpiAwarenessContext.argtypes = [ctypes.wintypes.HANDLE]
user32.SetThreadDpiAwarenessContext.restype = ctypes.wintypes.HANDLE

class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ('style', ctypes.wintypes.UINT),
        ('lpfnWndProc', WNDPROCTYPE),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', ctypes.wintypes.HINSTANCE),
        ('hIcon', HICON),
        ('hCursor', HCURSOR),
        ('hbrBackground', HBRUSH),
        ('lpszMenuName', ctypes.wintypes.LPCWSTR),
        ('lpszClassName', ctypes.wintypes.LPCWSTR),
    ]

REG_STARTUP = r'Software\Microsoft\Windows\CurrentVersion\Run'

AUTOSTART_NAME = 'MouseTracks'


def monitor_locations(dpi_aware: bool = False) -> RectList:
    """Get the location of each monitor.

    Parameters:
        dpi_aware: Get the logical coordinates instead of physical.
            Only necessary when using the Windows scaling feature.

    Returns:
        List of (x1, y1, x2, y2) tuples representing monitor bounds.
    """
    monitors = RectList()

    def callback(hMonitor: HMONITOR, hdc: HDC, lprcMonitor: ctypes._Pointer[RECT], lParam: LPARAM) -> bool:
        """Callback function for EnumDisplayMonitors."""
        rect = lprcMonitor.contents
        monitors.append(Rect.from_rect(rect.left, rect.top, rect.right, rect.bottom))
        return True

    awareness = DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 if dpi_aware else DPI_AWARENESS_CONTEXT_UNAWARE
    original_ctx = user32.SetThreadDpiAwarenessContext(awareness)
    try:
        user32.EnumDisplayMonitors(0, None, MonitorEnumProc(callback), 0)
    finally:
        user32.SetThreadDpiAwarenessContext(original_ctx)
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

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self.pid})'

    def __bool__(self) -> bool:
        return bool(self.pid)

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
        hwnds: list[int] = []
        if not self.pid:
            return hwnds

        def enum_windows_callback(hwnd: int, lparam: int) -> bool:
            process_id = DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
            if process_id.value == self.pid:
                hwnds.append(hwnd)
            return True

        user32.EnumWindows(EnumWindowsProc(enum_windows_callback), 0)
        hwnds.sort()
        return hwnds

    @property
    def visible_hwnds(self) -> list[int]:
        """Find all window handles for the given process ID.

        This shouldn't be required often, but certain applications such
        as "HP Anyware Client" have multiple windows with different
        handles.

        In some cases, if reading the PID from the hwnd returns 0, then
        directly querying the window handles from the PID will return an
        empty list. See the `WindowHandle` class for details.
        """
        return [hwnd for hwnd in self.hwnds if user32.IsWindowVisible(hwnd)]

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
    def rect(self) -> Rect:
        """Get the bounding rectangle of all windows belonging to this process."""
        left = top = 2 << 31
        right = bottom = -2 << 31

        valid = False
        for hwnd in self.visible_hwnds:
            rect = RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                valid = True
                left = min(left, rect.left)
                top = min(top, rect.top)
                right = max(right, rect.right)
                bottom = max(bottom, rect.bottom)

        if valid:
            return Rect.from_rect(left, top, right, bottom)
        return Rect()

    @property
    def rects(self) -> RectList:
        """Get the rects of each window handle."""
        return RectList(handle.rect for handle in map(WindowHandle, self.visible_hwnds))

    @property
    def position(self) -> tuple[int, int]:
        """Get the position of the window."""
        return self.rect.position

    @property
    def size(self) -> tuple[int, int]:
        """Get the size of the window."""
        return self.rect.size


class WindowHandle:
    """Class to manage a window handle and retrieve relevant information.
    Note that a PID may have multiple window handles.

    In some cases, the PID will return 0. This is likely an anti cheat
    measure, as I've only seen this happening for Helldivers 2 using
    "nProtect GameGuard". If this happens, then using the PID to get
    all window handles will also return nothing, so I wasn't able to
    find a solution to this.

    Using ctypes instead of pywin32 fixes it when running as a Python
    script, but both methods fail once built as an executable.
    """

    def __init__(self, hwnd: int, pid: int | None = None) -> None:
        self.hwnd = hwnd

        # Get Process ID
        if pid is None:
            process_id = DWORD()
            self.thread_id = user32.GetWindowThreadProcessId(self.hwnd, ctypes.byref(process_id))
            pid = process_id.value
        self.pid = PID(pid)

    @property
    def rect(self) -> Rect:
        """Get the window's rect coordinates."""
        rect = RECT()
        if user32.GetWindowRect(self.hwnd, ctypes.byref(rect)):
            return Rect.from_rect(rect.left, rect.top, rect.right, rect.bottom)
        return Rect()

    @property
    def position(self) -> tuple[int, int]:
        """Get the position of the window."""
        return self.rect.position

    @property
    def size(self) -> tuple[int, int]:
        """Get the size of the window."""
        return self.rect.size

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


def get_autostart() -> str | None:
    """Determine if running on startup."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_STARTUP, 0, winreg.KEY_READ) as key:
            cmd = winreg.QueryValueEx(key, AUTOSTART_NAME)[0]
    except FileNotFoundError:
        return None
    except IndexError:
        pass
    return cmd


def set_autostart(*args: str, ignore_args: tuple[str, ...] = ()) -> None:
    """Set an executable to run on startup."""
    cmd = subprocess.list2cmdline([str(APP_EXECUTABLE)] + [arg for arg in args if arg not in ignore_args])
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_STARTUP, 0, winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, cmd)


def remove_autostart() -> None:
    """Stop an executable running on startup."""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_STARTUP, 0, winreg.KEY_WRITE) as key:
        with suppress(FileNotFoundError):
            winreg.DeleteValue(key, AUTOSTART_NAME)


def is_elevated() -> bool:
    """Check if the script is running with admin privileges."""
    return bool(shell32.IsUserAnAdmin())


def relaunch_as_elevated() -> None:
    """Relaunch the script with admin privileges."""
    shell32.ShellExecuteW(None, 'runas', sys.executable, shlex.join(sys.argv), None, 1)
    sys.exit()


class Window(_Window):
    def __init__(self, hwnd: int) -> None:
        self._hwnd = hwnd
        self._handle = WindowHandle(self._hwnd)
        self._pid = self._handle.pid

    @classmethod
    def get_focused(cls) -> Self:
        return cls(get_window_handle())

    @property
    def pid(self) -> int:
        return int(self._pid)

    @pid.setter
    def pid(self, pid: int) -> None:
        self._pid = PID(pid)

    @property
    def title(self) -> str:
        return self._handle.title

    @property
    def executable(self) -> str:
        return self._pid.executable

    @property
    def rects(self) -> RectList:
        return self._pid.rects

    @property
    def position(self) -> tuple[int, int]:
        return self._pid.position

    @property
    def size(self) -> tuple[int, int]:
        return self._pid.size


class MonitorEventsListener(_MonitorEventsListener):
    """Listen for monitor change events."""

    def __init__(self) -> None:
        super().__init__()
        self._hwnd = None  # type: int | None

    def run(self) -> None:
        """Create and start the message listener."""
        def wndproc(hwnd: int, msg: int, wparam: int, lparam: int) -> int:
            if msg in (WM_DISPLAYCHANGE, WM_DEVICECHANGE):
                self.trigger()
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        hinst = kernel32.GetModuleHandleW(None)
        wndproc_c = WNDPROCTYPE(wndproc)

        class_name = 'MouseTracksHiddenWindowClass'
        wc = WNDCLASS()
        wc.lpfnWndProc = wndproc_c
        wc.lpszClassName = class_name
        wc.hInstance = hinst

        if not user32.RegisterClassW(ctypes.byref(wc)):
            raise ctypes.WinError(ctypes.get_last_error())

        self._hwnd = user32.CreateWindowExW(
            0, class_name, 'hidden', 0,
            0, 0, 0, 0,
            None, None, hinst, None
        )
        if not self._hwnd:
            raise ctypes.WinError(ctypes.get_last_error())

        self.trigger()

        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def stop(self) -> None:
        """Stops the message loop and cleans up the window."""
        if self._hwnd:
            user32.PostMessageW(self._hwnd, WM_QUIT, 0, 0)
