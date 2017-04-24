import win32api
import win32con
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
    return win32api.GetAsyncKeyState(key)


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


MOUSE_BUTTONS = (win32con.VK_LBUTTON, win32con.VK_MBUTTON, win32con.VK_RBUTTON)
KEYS = {
    'F1': win32con.VK_F1,
    'F2': win32con.VK_F2,
    'F3': win32con.VK_F3,
    'F4': win32con.VK_F4,
    'F5': win32con.VK_F5,
    'F6': win32con.VK_F6,
    'F7': win32con.VK_F7,
    'F8': win32con.VK_F8,
    'F9': win32con.VK_F9,
    'F10': win32con.VK_F10,
    'F11': win32con.VK_F11,
    'F12': win32con.VK_F12,
    'F13': win32con.VK_F13,
    'F14': win32con.VK_F14,
    'F15': win32con.VK_F15,
    'F16': win32con.VK_F16,
    'F17': win32con.VK_F17,
    'F18': win32con.VK_F18,
    'F19': win32con.VK_F19,
    'F20': win32con.VK_F20,
    'F21': win32con.VK_F21,
    'F22': win32con.VK_F22,
    'F23': win32con.VK_F23,
    'F24': win32con.VK_F24,
    'LCTRL': win32con.VK_LCONTROL,
    'RCTRL': win32con.VK_RCONTROL,
    'LSHIFT': win32con.VK_LSHIFT,
    'RSHIFT': win32con.VK_RSHIFT,
    'LALT': win32con.VK_LMENU,
    'RALT': win32con.VK_RMENU,
    'LWIN': win32con.VK_LWIN,
    'RWIN': win32con.VK_RWIN,
    'ESC': win32con.VK_ESCAPE,
    'HOME': win32con.VK_HOME,
    'DELETE': win32con.VK_DELETE,
    'RETURN': win32con.VK_RETURN,
    'BACK': win32con.VK_BACK,
    'TAB': win32con.VK_TAB,
    'DIVIDE': win32con.VK_DIVIDE,
    'DECIMAL': win32con.VK_DECIMAL,
    'MULTIPLY': win32con.VK_MULTIPLY,
    'SUBTRACT': win32con.VK_SUBTRACT,
    'ADD': win32con.VK_ADD,
    'INSERT': win32con.VK_INSERT,
    'CLEAR': win32con.VK_CLEAR,
    'CAPSLOCK': win32con.VK_CAPITAL,
    'SCROLLLOCK': win32con.VK_SCROLL,
    'NUMLOCK': win32con.VK_NUMLOCK,
    'NUM0': win32con.VK_NUMPAD0,
    'NUM1': win32con.VK_NUMPAD1,
    'NUM2': win32con.VK_NUMPAD2,
    'NUM3': win32con.VK_NUMPAD3,
    'NUM4': win32con.VK_NUMPAD4,
    'NUM5': win32con.VK_NUMPAD5,
    'NUM6': win32con.VK_NUMPAD6,
    'NUM7': win32con.VK_NUMPAD7,
    'NUM8': win32con.VK_NUMPAD8,
    'NUM9': win32con.VK_NUMPAD9,
    'HOME': win32con.VK_HOME,
    'END': win32con.VK_END,
    'PGUP': win32con.VK_PRIOR,
    'PGDOWN': win32con.VK_NEXT,
    'PAUSE': win32con.VK_PAUSE,
    'UP': win32con.VK_UP,
    'DOWN': win32con.VK_DOWN,
    'LEFT': win32con.VK_LEFT,
    'RIGHT': win32con.VK_RIGHT,
    'SPACE': win32con.VK_SPACE,
    'UNDERSCORE': 189,
    'EQUALS': 187,
    'MENU': 93,
    'BACKSLASH': 220,
    'FORWARDSLASH': 191,
    'COLON': 186,
    'AT': 192,
    'HASH': 222,
    'LBRACKET': 219,
    'RBRACKET': 221,
    'TILDE': 223,
    'PERIOD': 190,
    'COMMA': 188,
}
for c in list('ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'):
    KEYS[c] = ord(c)
