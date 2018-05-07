"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Windows functions that require pywin32

from __future__ import absolute_import

import os
import sys
import time
import win32api
import win32con
import win32console
import win32gui
import win32process
import pywintypes
from win32com.shell import shell, shellcon


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
    return win32api.GetKeyState(key) < 0


def get_monitor_locations():
    """Return a list of (x[0], y[0], x[1], y[1]) coordinates for each monitor."""
    return tuple(m[2] for m in win32api.EnumDisplayMonitors())
    
    
def get_documents_path():
    """Return the path to documents."""
    return shell.SHGetFolderPath(0, shellcon.CSIDL_PERSONAL, None, 0)

    
def get_window_handle(parent=True, console=False):
    command = win32console.GetConsoleWindow if console else win32gui.GetForegroundWindow
    if not parent:
        return command()
    
    #Find the parent windows until there are none left
    while True:
        try:
            parent = win32gui.GetParent(hwnd)
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
        self.pid = win32process.GetWindowThreadProcessId(self.hwnd)[1]
    
    @property
    def rect(self):
        """Get the coordinates of a window."""
        try:
            return win32gui.GetWindowRect(self.hwnd)
        except win32api.error:
            return (0, 0, 0, 0)
    
    @property
    def name(self):
        return win32gui.GetWindowText(self.hwnd)
    
    #Tray icon commands
    @property
    def minimised(self):
        """Find if window is minimised."""
        return win32gui.IsIconic(self.hwnd)
        
    def restore(self):
        """Restore a window from being minimised."""
        win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
    
    def bring_to_front(self, new=True):
        """Bring a window into focus.
        Kept the old way just to be on the safe side.
        """
        if new:
            win32gui.ShowWindow(self.hwnd, True)
        else:
            self.restore()
            
        #Sometimes it seems to fail but then work a second time
        try:
            win32gui.SetForegroundWindow(self.hwnd)
        except pywintypes.error:
            time.sleep(0.5)
            win32gui.ShowWindow(self.hwnd, True)
            try:
                win32gui.SetForegroundWindow(self.hwnd)
            except pywintypes.error:
                pass
        
    def minimise(self):
        """Minimise a window."""
        win32gui.ShowWindow(self.hwnd, win32con.SW_MINIMIZE)
        
    def hide(self, new=True):
        """Hide a window from the task bar.
        Kept the old way just to be on the safe side.
        """
        if new:
            win32gui.ShowWindow(self.hwnd, False)
        else:
            self.minimise()
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)
            win32gui.SetWindowLong(self.hwnd, win32con.GWL_EXSTYLE,
                                   win32gui.GetWindowLong(self.hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_TOOLWINDOW)
            win32gui.ShowWindow(self.hwnd, win32con.SW_SHOW)


def launch_console(params, visible=True, process=sys.executable, visiblity_override=None):
    if visiblity_override is not None:
        if visiblity_override:
            process.replace('pythonw', 'python')
        else:
            process = process.replace('python', 'pythonw').replace('pythonww', 'pythonw')
    try:
        shell.ShellExecuteEx(lpVerb='runas', lpFile=process, lpParameters=params, nShow=5 if visible else 0)
    except pywintypes.error:
        return False
    return True

    
def is_elevated():
    return shell.IsUserAnAdmin()