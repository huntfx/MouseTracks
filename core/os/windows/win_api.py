import win32api
import win32con


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
    return [m[2] for m in win32api.EnumDisplayMonitors()]
    
    
def get_documents_path():
    return win32com.shell.shell.SHGetFolderPath(0, win32com.shell.shellcon.CSIDL_PERSONAL, None, 0)
