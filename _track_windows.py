import win32api
from _track_constants import MOUSE_BUTTONS
import os

def get_device_data():
    """Get the resolution and refresh rate of the main monitor."""
    device = win32api.EnumDisplayDevices()
    settings = win32api.EnumDisplaySettings(device.DeviceName, 0)
    refresh_rate = getattr(settings, 'DisplayFrequency')
    resolution = (win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1))
    return {'Resolution': resolution, 0: resolution,
            'Refresh': refresh_rate, 1: refresh_rate}

def get_cursor_pos():
    """Return the cursor position as a tuple."""
    try:
        return win32api.GetCursorPos()
    except win32api.error:
        return None

def get_mouse_click():
    """Check if one of the three main mouse buttons is being clicked."""
    return any(win32api.GetKeyState(button) < 0 for button in MOUSE_BUTTONS)

def get_key_press(key):
    """Check if a key is being pressed.
    Needs changing for something that detects keypresses in applications.
    """
    #return win32api.GetAsyncKeyState(key)
    return win32api.GetKeyState(key) < 0

def remove_file(file_name):
    """Delete a file."""
    try:
        os.remove(file_name)
    except WindowsError:
        return False
    return True

def rename_file(old_name, new_name):
    """Rename a file."""
    try:
        os.rename(old_name, new_name)
    except WindowsError:
        return False
    return True

def create_folder(folder_path):
    """Create a folder."""
    try:
        os.makedirs(folder_path)
    except WindowsError:
        return False
    return True
