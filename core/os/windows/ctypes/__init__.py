"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import ctypes
import ctypes.wintypes
import os
import sys

from core.compatibility import unicode


def get_double_click_time():
    """ Gets the Windows double click time in ms """
    return int(ctypes.windll.user32.GetDoubleClickTime())

    
def hide_file(file_name):
    """Set a file as hidden."""
    ctypes.windll.kernel32.SetFileAttributesW(file_name, 2)

   
def show_file(file_name):
    """Unset a file as hidden."""
    ctypes.windll.kernel32.SetFileAttributesW(file_name, 128)


def get_resolution():
    """Get the resolution of the main monitor.
    Returns:
        (x, y) resolution as a tuple.
    """
    user32 = ctypes.windll.user32
    return (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_cursor_pos():
    """Read the cursor position on screen.
    Returns:
        (x, y) coordinates as a tuple.
        None if it can't be detected.
    """
    pt = _POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return (int(pt.x), int(pt.y))


def get_mouse_click():
    """Check if one of the three main mouse buttons is being clicked.
    Returns:
        True/False if any clicks have been detected or not.
    """
    buttons = (1, 4, 2)
    return tuple(ctypes.windll.user32.GetKeyState(button) > 1 for button in buttons)


def get_key_press(key):
    """Check if a key is being pressed.
    Needs changing for something that detects keypresses in applications.
    Returns:
        True/False if the selected key has been pressed or not.
    """
    return ctypes.windll.user32.GetKeyState(key) > 1
    

class _RECT(ctypes.Structure):
    _fields_ = [
        ('left', ctypes.c_long),
        ('top', ctypes.c_long),
        ('right', ctypes.c_long),
        ('bottom', ctypes.c_long)
    ]
  
    def dump(self):
        return tuple(map(int, (self.left, self.top, self.right, self.bottom)))


class _MONITORINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', ctypes.c_long),
        ('rcMonitor', _RECT),
        ('rcWork', _RECT),
        ('dwFlags', ctypes.c_long)
    ]


def _get_monitors():
    """Get a list of all monitors to further processing.
    Copied from code.activestate.com/recipes/460509-get-the-actual-and-usable-sizes-of-all-the-monitor/
    """
    retval = []
    CBFUNC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                                ctypes.POINTER(_RECT), ctypes.c_double)

    def cb(hMonitor, hdcMonitor, lprcMonitor, dwData):
        r = lprcMonitor.contents
        data = [hMonitor]
        data.append(r.dump())
        retval.append(data)
        return 1

    cbfunc = CBFUNC(cb)
    temp = ctypes.windll.user32.EnumDisplayMonitors(0, 0, cbfunc, 0)
  
    return retval


def _monitor_areas():
    """Find the active and working area of each monitor.
    Copied from code.activestate.com/recipes/460509-get-the-actual-and-usable-sizes-of-all-the-monitor/
    """
    retval = []
    monitors = _get_monitors()
    for hMonitor, extents in monitors:
        data = [hMonitor]
        mi = _MONITORINFO()
        mi.cbSize = ctypes.sizeof(_MONITORINFO)
        mi.rcMonitor = _RECT()
        mi.rcWork = _RECT()
        res = ctypes.windll.user32.GetMonitorInfoA(hMonitor, ctypes.byref(mi))
        data.append(mi.rcMonitor.dump())
        data.append(mi.rcWork.dump())
        retval.append(data)
    return retval


def get_monitor_locations():
    """Extract locations from monitor functions."""
    return tuple(m[1] for m in _monitor_areas())

    
def get_documents_path():
    """Return the path to documents."""
    buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
    return buf.value
    
    
def get_window_handle(parent=True, console=False):
    command = ctypes.windll.kernel32.GetConsoleWindow if console else ctypes.windll.user32.GetForegroundWindow
    if not parent:
        return command()
    
    #Find the parent windows until there are none left
    while True:
        try:
            parent = ctypes.windll.user32.GetParent(hwnd)
        except UnboundLocalError:
            hwnd = command()
        except win32api.error:
            break
        else:
            if parent:
                hwnd = parent
            else:
                break
    return hwnd
    

class WindowHandle(object):

    def __init__(self, parent=True, console=False):
        """Get the handle of the currently focused window."""
        self.hwnd = get_window_handle(parent, console)
        
        process_id = ctypes.c_int()
        ctypes.windll.user32.GetWindowThreadProcessId(self.hwnd, ctypes.byref(process_id))
        self.pid = process_id.value
        
    @property
    def rect(self):
        """Get the coordinates of a window."""
        win_rect = _RECT()
        ctypes.windll.user32.GetWindowRect(self.hwnd, ctypes.byref(win_rect))
        return win_rect.dump()
    
    @property
    def name(self):
        length = ctypes.windll.user32.GetWindowTextLengthW(self.hwnd) + 1
        buff = ctypes.create_unicode_buffer(length)
        ctypes.windll.user32.GetWindowTextW(self.hwnd, buff, length)
        return buff.value
    
    #Tray icon commands (not in use)
    @property
    def minimised(self):
        return ctypes.windll.user32.IsIconic(self.hwnd)
        
    def restore(self):
        ctypes.windll.user32.ShowWindow(self.hwnd, 9)

    def bring_to_front(self):
        self.restore()
        ctypes.windll.user32.SetForegroundWindow(self.hwnd)
        
    def minimise(self):
        ctypes.windll.user32.ShowWindow(self.hwnd, 6)
        
    def hide(self):
        self.minimise()
        ctypes.windll.user32.ShowWindow(self.hwnd, 0)
        ctypes.windll.user32.SetWindowLongA(self.hwnd, -20,
                                            ctypes.windll.user32.GetWindowLongA(self.hwnd, -20) | 128)
        ctypes.windll.user32.ShowWindow(self.hwnd, 5)

        
def launch_new_console(show=True, add_arguments=[], remove_arguments=[]):
    if isinstance(add_arguments, str):
        add_arguments = [add_arguments]
    if isinstance(remove_arguments, str):
        remove_arguments = [remove_arguments]
        
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + [i for i in sys.argv[1:] if i not in remove_arguments] + list(add_arguments))
    ret = ctypes.windll.shell32.ShellExecuteW(None, u'runas', unicode(sys.executable), params, None, 5 if show else 0)
    if int(ret) > 32:
        sys.exit(0)


def elevate(console=True, _argument='Elevate'):
    """Elevate the program to admin permissions."""
    if ctypes.windll.shell32.IsUserAnAdmin() or _argument in sys.argv:
        return True
    
    if launch_new_console(show=console, add_arguments=_argument):
        sys.exit(0)
    return False