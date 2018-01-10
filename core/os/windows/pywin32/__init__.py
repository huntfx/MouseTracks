"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import os
import pywintypes
import sys
import win32api
import win32con
import win32gui
import win32process
from win32com.shell import shell, shellcon

from core.os.windows.pywin32 import tray


def hide_file(file_name):
    """Set a file as hidden."""
    try:
        win32api.SetFileAttributes(file_name, win32con.FILE_ATTRIBUTE_HIDDEN)
    except win32api.error:
        return False
    return True

   
def show_file(file_name):
    """Unset a file as hidden."""
    try:
        win32api.SetFileAttributes(file_name, win32con.FILE_ATTRIBUTE_NORMAL)
    except win32api.error:
        return False
    return True


def get_resolution():
    """Get the resolution of the main monitor.
    Returns:
        (x, y) resolution as a tuple.
    """
    return (win32api.GetSystemMetrics(win32con.SM_CXSCREEN), 
            win32api.GetSystemMetrics(win32con.SM_CYSCREEN))


def get_refresh_rate():
    """Get the refresh rate of the main monitor.
    Returns:
        Refresh rate/display frequency as an int.
    """
    device = win32api.EnumDisplayDevices()
    settings = win32api.EnumDisplaySettings(device.DeviceName, 0)
    return getattr(settings, 'DisplayFrequency')


def get_cursor_pos():
    """Read the cursor position on screen.
    Returns:
        (x, y) coordinates as a tuple.
        None if it can't be detected.
    """
    try:
        return win32api.GetCursorPos()
    except win32api.error:
        return None


def get_mouse_click():
    """Check if one of the three main mouse buttons is being clicked.
    Returns:
        True/False if any clicks have been detected or not.
    """
    buttons = (win32con.VK_LBUTTON, win32con.VK_MBUTTON, win32con.VK_RBUTTON)
    return tuple(win32api.GetKeyState(button) < 0 for button in buttons)


def get_key_press(key):
    """Check if a key is being pressed.
    Needs changing for something that detects keypresses in applications.
    Returns:
        True/False if the selected key has been pressed or not.
    """
    return win32api.GetAsyncKeyState(key)


def get_monitor_locations():
    """Return a list of (x[0], y[0], x[1], y[1]) coordinates for each monitor."""
    return tuple(m[2] for m in win32api.EnumDisplayMonitors())
    
    
def get_documents_path():
    """Return the path to documents."""
    return shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, None, 0)

    
class WindowFocusData(object):

    def __init__(self):
        """Get the handle of the currently focused window."""
        self.hwnd = self._get_parent()
    
    def _get_parent(self):
        while True:
            try:
                parent = win32gui.GetParent(hwnd)
            except UnboundLocalError:
                hwnd = win32gui.GetForegroundWindow()
            except win32api.error:
                break
            else:
                if parent:
                    hwnd = parent
                else:
                    break
        return hwnd
        
    def get_pid(self):
        """Get the process ID of a window."""
        return win32process.GetWindowThreadProcessId(self.hwnd)[1]
        
    def get_rect(self):
        """Get the coordinates of a window."""
        try:
            return win32gui.GetWindowRect(self.hwnd)
        except win32api.error:
            return (0, 0, 0, 0)
    
    def get_name(self):
        return win32gui.GetWindowText(self.hwnd)
        
        
def elevate(console=True, _argument='forced_elevate'):
    """Elevate the program to admin permissions."""
    if shell.IsUserAnAdmin() or sys.argv[-1] == _argument:
        return True
        
    script = os.path.abspath(sys.argv[0])
    params = ' '.join([script] + sys.argv[1:] + [_argument])
    try:
        shell.ShellExecuteEx(lpVerb='runas', lpFile=sys.executable, lpParameters=params, nShow=5 if console else 0)
    except pywintypes.error:
        pass
    else:
        sys.exit(0)
    return False