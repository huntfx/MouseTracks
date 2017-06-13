import os

try:
    from core.os.windows.win_api import *
except ImportError:
    from core.os.windows.win_ctypes import *


def remove_file(file_name):
    """Delete a file.
    Returns:
        True/False if successful or not.
    """
    try:
        os.remove(file_name)
    except WindowsError:
        return False
    return True


def rename_file(old_name, new_name):
    """Rename a file.
    Return:
        True/False if successful or not.
    """
    try:
        os.rename(old_name, new_name)
    except WindowsError:
        return False
    return True


def create_folder(folder_path):
    """Create a folder.
    Return:
        True/False if successful or not.
    """
    try:
        os.makedirs(folder_path)
    except WindowsError:
        return False
    return True


def get_running_processes():
    """Return a dictionary of running processes, with their ID as the value.
    The ID is used to determine which process was most recently loaded.
    """
    task_list = os.popen("tasklist").read().splitlines()
    
    running_processes = {}
    for i, task_raw in enumerate(task_list):
        if task_raw:
            try:
                image, name, pid, session, mem, usage = task_raw.split()
            except ValueError:
                pass
            else:
                if '.' in image:
                    running_processes[image] = i
    return running_processes

KEYS = {
    'BACK': 8,
    'TAB': 9,
    'CLEAR': 12,
    'RETURN': 13,
    'PAUSE': 19,
    'CAPSLOCK': 20,
    'ESC': 27,
    'SPACE': 32,
    'PGUP': 33,
    'PGDOWN': 34,
    'END': 35,
    'HOME': 36,
    'LEFT': 37,
    'UP': 38,
    'RIGHT': 39,
    'DOWN': 40,
    'INSERT': 45,
    'DELETE': 46,
    'LWIN': 91,
    'RWIN': 92,
    'MENU': 93,
    'NUM0': 96,
    'NUM1': 97,
    'NUM2': 98,
    'NUM3': 99,
    'NUM4': 100,
    'NUM5': 101,
    'NUM6': 102,
    'NUM7': 103,
    'NUM8': 104,
    'NUM9': 105,
    'MULTIPLY': 106,
    'ADD': 107,
    'SUBTRACT': 109,
    'DECIMAL': 110,
    'DIVIDE': 111,
    'F1': 112,
    'F2': 113,
    'F3': 114,
    'F4': 115,
    'F5': 116,
    'F6': 117,
    'F7': 118,
    'F8': 119,
    'F9': 120,
    'F10': 121,
    'F11': 122,
    'F12': 123,
    'F13': 124,
    'F14': 125,
    'F15': 126,
    'F16': 127,
    'F17': 128,
    'F18': 129,
    'F19': 130,
    'F20': 131,
    'F21': 132,
    'F22': 133,
    'F23': 134,
    'F24': 135,
    'NUMLOCK': 144,
    'SCROLLLOCK': 145,
    'LSHIFT': 160,
    'RSHIFT': 161,
    'LCTRL': 162,
    'RCTRL': 163,
    'LALT': 164,
    'RALT': 165,
    'COLON': 186,
    'EQUALS': 187,
    'COMMA': 188,
    'UNDERSCORE': 189,
    'PERIOD': 190,
    'FORWARDSLASH': 191,
    'AT': 192,
    'LBRACKET': 219,
    'BACKSLASH': 220,
    'RBRACKET': 221,
    'HASH': 222,
    'TILDE': 223
}
for c in list('ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'):
    KEYS[c] = ord(c)
