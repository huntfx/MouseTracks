import win32api
from _track_constants import MOUSE_BUTTONS
import os

def get_device_data():
    device = win32api.EnumDisplayDevices()
    settings = win32api.EnumDisplaySettings(device.DeviceName, 0)
    refresh_rate = getattr(settings, 'DisplayFrequency')
    resolution = (win32api.GetSystemMetrics(0), win32api.GetSystemMetrics(1))
    return {'Resolution': resolution, 0: resolution,
            'Refresh': refresh_rate, 1: refresh_rate}

def get_cursor_pos():
    try:
        return win32api.GetCursorPos()
    except win32api.error:
        return None

#GetAsyncKeyState won't work in full screen applications
'''
def get_mouse_click():
    return any(win32api.GetAsyncKeyState(button) for button in MOUSE_BUTTONS)

def get_key_press(key):
    return win32api.GetAsyncKeyState(key)
'''

def get_mouse_click():
    return any(win32api.GetKeyState(button) < 0 for button in MOUSE_BUTTONS)

#Unfortunately this won't work either for the keyboard, dunno what will
def get_key_press(key):
    return win32api.GetKeyState(key) < 0

def remove_file(file_name):
    try:
        os.remove(file_name)
    except WindowsError:
        return False
    return True

def rename_file(old_name, new_name):
    try:
        os.rename(old_name, new_name)
    except WindowsError:
        return False
    return True
