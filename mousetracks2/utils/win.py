"""Windows specific functions.

This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

import os
import sys
from contextlib import contextmanager

import pywintypes
import win32api
import win32con
import win32console
import win32gui
import win32process
import winreg


def cursor_position() -> tuple[int, int] | None:
    """Get the current mouse position.

    Returns:
        (x, y) as integers
        None in the case of any error
    """
    try:
        return win32api.GetCursorPos()
    except win32api.error:
        return None


def main_monitor_resolution() -> tuple[int, int]:
    """Get the main screen resolution.
    Any secondary screens will be ignored.
    """
    return (win32api.GetSystemMetrics(win32con.SM_CXSCREEN),
            win32api.GetSystemMetrics(win32con.SM_CYSCREEN))


def monitor_locations() -> list[tuple[int, int, int, int]]:
    """Get the location of each monitor.

    Returns:
        (x1, y1, x2, y2) for each monitor
    """
    return [m[2] for m in win32api.EnumDisplayMonitors()]


def check_key_press(key: int) -> bool:
    """Check if a key is being pressed.
    This also supports mouse clicks using win32con.VK_[L/M/R]BUTTON.

    Returns:
        True/False if the selected key has been pressed or not.
    """
    return win32api.GetKeyState(key) < 0


def get_scroll_lines() -> int:
    """Get the number of lines to scroll with one notch of the mouse wheel."""
    return win32gui.SystemParametersInfo(win32con.SPI_GETWHEELSCROLLLINES)


class WindowHandle(object):
    def __init__(self, hwnd):
        self.hwnd = hwnd
        self.pid = win32process.GetWindowThreadProcessId(self.hwnd)[1]
        self.proc = psutil.Process(self.pid)
        # 'as_dict', 'children', 'cmdline', 'connections', 'cpu_affinity', 'cpu_percent',
        # 'cpu_times', 'create_time', 'cwd', 'environ', 'exe', 'io_counters', 'ionice',
        # 'is_running', 'kill', 'memory_full_info', 'memory_info', 'memory_info_ex',
        # 'memory_maps', 'memory_percent', 'name', 'nice', 'num_ctx_switches', 'num_handles',
        # 'num_threads', 'oneshot', 'open_files', 'parent', 'parents', 'pid', 'ppid', 'resume',
        # 'send_signal', 'status', 'suspend', 'terminate', 'threads', 'username', 'wait']

    def __repr__(self):
        return f'{type(self).__name__}({self.hwnd!r})'

    def __eq__(self, hwnd):
        if isinstance(hwnd, type(self)):
            return hwnd.hwnd == self.hwnd
        return hwnd in (self.hwnd, self.pid)

    @classmethod
    def from_title(cls, name):
        """Get a window handle from its title.
        If multiple windows have the title, then it will find the most
        recently loaded.
        """
        hwnd = win32gui.FindWindow(None, name)
        if hwnd is not None:
            return cls(hwnd)
        return cls(0)

    @contextmanager
    def _open_handle(self, permission=win32con.PROCESS_QUERY_INFORMATION):
        handle = win32api.OpenProcess(permission, pywintypes.FALSE, self.pid)
        yield handle
        win32api.CloseHandle(handle)

    @property
    def modules(self):
        """Get all the modules for the process."""
        with self._open_handle(win32con.PROCESS_TERMINATE) as handle:
            for module_id in win32process.EnumProcessModules(handle):
                yield win32process.GetModuleFileNameEx(handle, module_id)

    @property
    def executable(self):
        """Get the path to the executable."""
        return next(self.modules)
        # return psutil.Process(self.pid).exe()

    def kill(self):
        with self._open_handle() as handle:
            win32api.TermindateProcess(handle, 0)

    @property
    def rect(self):
        """Get the coordinates of a window."""
        try:
            return win32gui.GetWindowRect(self.hwnd)
        except win32api.error:
            return (0, 0, 0, 0)

    @property
    def title(self):
        """Get the window title."""
        return win32gui.GetWindowText(self.hwnd)

    @title.setter
    def title(self, title):
        """Set a new window title."""
        return win32gui.SetWindowText(self.hwnd, title)

    @property
    def minimised(self):
        """Find if window is minimised."""
        return win32gui.IsIconic(self.hwnd)

    @property
    def top_most(self):
        """Find if a window is top most."""
        ex_style = win32api.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE)
        return bool(ex_style & win32con.WS_EX_TOPMOST)

    @top_most.setter
    def top_most(self, top_most):
        """Set if a window is top most."""
        x1, y1, x2, y2 = self.rect
        flag = win32con.HWND_TOPMOST if top_most else win32con.HWND_NOTOPMOST
        win32gui.SetWindowPos(self.hwnd, flag, x1, y1, x2-x1, y2-y1, 0)

    def restore(self):
        """Restore a window from being minimised."""
        win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)

    def minimise(self):
        """Minimise a window."""
        win32gui.ShowWindow(self.hwnd, win32con.SW_MINIMIZE)


def get_pid_from_hwnd(hwnd):
    global _top_window_mapping
    try:
        _top_window_mapping
    except NameError:
        _top_window_mapping = {}
        def enumeration_handler(hwnd, top_windows):
            top_windows[win32process.GetWindowThreadProcessId(hwnd)[1]] = hwnd
        win32gui.EnumWindows(enumeration_handler, top_windows)
    return _top_window_mapping.get(str(hwnd), 0)


class AutoRun:
    """Handle running the application on startup."""

    PATH = r'Software\Microsoft\Windows\CurrentVersion\Run'

    def __init__(self, executable: str = os.path.abspath(sys.argv[0]), name: str = 'MouseTracks'):
        self.executable = executable
        if not self.executable.lower().endswith('.exe'):
           raise ValueError('running on startup not supported when running as a script')
        self.name = name

    def __bool__(self) -> bool:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.PATH, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, self.name)
                return True
        except OSError:
            return False

    def __call__(self, startup):
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.PATH, 0, winreg.KEY_WRITE) as key:
            if startup:
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


if __name__ == '__main__':
    '''
    wh = WindowHandle.from_title('Untitled - Notepad')
    print(list(wh.modules))
    print(wh.executable)
    '''

    hwnd = win32gui.FindWindow('Notepad', None)
    win32con.WS_EX_TOPMOST

    #top_most(hwnd)
    print(win32gui.GetWindowText(hwnd))

    top_windows = {}
    def window_enumeration_handler(hwnd, top_windows):
        """Add window title and ID to array."""
        top_windows[win32process.GetWindowThreadProcessId(hwnd)[1]] = hwnd
        #top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))
    win32gui.EnumWindows(window_enumeration_handler, top_windows)
    for i in top_windows:
        print(i)


    '''
    from win32gui import GetWindowText, GetForegroundWindow
    print GetWindowText(GetForegroundWindow())
    '''