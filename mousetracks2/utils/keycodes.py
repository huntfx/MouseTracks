"""Register all keycodes in use.

https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes

Some keys trigger multiple codes at once.
This will need to be handled in stats/renders.
    - Left control: VK_CONTROL + VK_LCONTROL
    - Right control: VK_CONTROL + VK_RCONTROL
    - Left alt: VK_MENU + VK_LMENU
    - Right alt: VK_MENU + VK_RMENU + VK_CONTROL + VK_LCONTROL
"""

from __future__ import annotations

import sys

from pynput.keyboard import Key as _Key, KeyCode as _KeyCode


def from_pynput(key: _KeyCode | _Key) -> int:
    """Get the integer keycode from a pynput object."""
    # Handle special keys (eg. enter, shift, f1)
    if isinstance(key, _Key):
        if key in KeyCode._PYNPUT_MAP:
            return KeyCode._PYNPUT_MAP[key]
        key = key.value

    # Handle printable character keys (eg. 'a', '1', ';')
    if key.vk is None:
        raise ValueError('vk not set')

    # On Linux/macOS, use the character itself.
    if sys.platform != 'win32' and key.char is not None:
        # Check the new auto-populated character map first
        char = KeyCode._SYMBOL_REMAP.get(key.char, key.char)
        if char in KeyCode._CHAR_MAP:
            return KeyCode._CHAR_MAP[char]

        # For A-Z and 0-9, the ASCII/Unicode value often matches the VK code.
        char_upper = char.upper()
        if 'A' <= char_upper <= 'Z' or '0' <= char_upper <= '9':
            return ord(char_upper)

    # On Windows, key.vk is the most reliable source.
    return key.vk


def key(name: str) -> _Key | None:
    """Get a key from pynput if it exists.

    This is required as different operating systems have different
    supported keys.
    """
    return getattr(_Key, name, None)


class KeyCode(int):
    """Register a keycode with its associated data."""

    _REGISTRY: dict[int, str] = {}
    _PYNPUT_MAP: dict[_Key, int] = {}
    _CHAR_MAP: dict[str, int] = {}
    _SYMBOL_REMAP: dict[str, str] = {}

    def __new__(cls, code: int | _Key | _KeyCode) -> KeyCode:
        if not isinstance(code, int):
            code = from_pynput(code)
        return int.__new__(cls, code)

    @classmethod
    def register(cls, code: int, name: str | None = None, *alternative: _Key | str | None, vk: str | None = None) -> KeyCode:
        """Register a new keycode option."""
        if name is not None:
            cls._REGISTRY[code] = name

        for key in set(alternative):
            if isinstance(key, _Key):
                if key in cls._PYNPUT_MAP:
                    raise RuntimeError(f'key "{key}" already remapped')
                cls._PYNPUT_MAP[key] = code
            elif key is not None:
                if key in cls._SYMBOL_REMAP:
                    raise RuntimeError(f'key "{key}" already remapped')
                if name is None:
                    raise ValueError('name must be set when remapping')
                cls._SYMBOL_REMAP[key] = name

        if vk is None:
            vk = name
        if vk in cls._CHAR_MAP:
            raise RuntimeError(f'key "{vk}" already remapped')
        if vk is not None and len(vk) == 1:
            cls._CHAR_MAP[vk] = code

        return cls(code)

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self:#04X}, {self.name!r})'

    def __str__(self) -> str:
        return self.name

    @property
    def name(self) -> str:
        """Get the keycode name."""
        return self._REGISTRY.get(int(self), f'{self:#04X}')

    @name.setter
    def name(self, name: str) -> None:
        """Set a new keycode name."""
        self._REGISTRY[int(self)] = name


class GamepadCode(KeyCode):
    _REGISTRY: dict[int, str] = {}
    _PYNPUT_MAP: dict[_Key, int] = {}
    _CHAR_MAP: dict[str, int] = {}
    _SYMBOL_REMAP: dict[str, str] = {}


# Mouse buttons
VK_LBUTTON = KeyCode.register(0x01, 'Left mouse button')
VK_RBUTTON = KeyCode.register(0x02, 'Right mouse button')
VK_MBUTTON = KeyCode.register(0x04, 'Middle mouse button')
VK_XBUTTON1 = KeyCode.register(0x05, 'Mouse button 4')
VK_XBUTTON2 = KeyCode.register(0x06, 'Mouse button 5')

# Control keys
VK_BACK = KeyCode.register(0x08, 'Backspace', key('backspace'))
VK_TAB = KeyCode.register(0x09, 'Tab', key('tab'))
VK_CLEAR = KeyCode.register(0x0C, 'Clear')
VK_RETURN = KeyCode.register(0x0D, 'Enter', key('enter'))
VK_SHIFT = KeyCode.register(0x10, 'Shift', key('shift') if key('shift') not in (key('shift_l'), key('shift_r')) else None)
VK_CONTROL = KeyCode.register(0x11, 'Control', key('ctrl') if key('ctrl') not in (key('ctrl_l'), key('ctrl_r')) else None)
VK_MENU = KeyCode.register(0x12, 'Alt', key('alt') if key('alt') not in (key('alt_l'), key('alt_r')) else None)
VK_PAUSE = KeyCode.register(0x13, 'Pause', key('pause'))
VK_CAPITAL = KeyCode.register(0x14, 'Caps Lock', key('caps_lock'))

VK_LSHIFT = KeyCode.register(0xA0, 'Left Shift', key('shift_l'))
VK_RSHIFT = KeyCode.register(0xA1, 'Right Shift', key('shift_r'))
VK_LCONTROL = KeyCode.register(0xA2, 'Left Control', key('ctrl_l'))
VK_RCONTROL = KeyCode.register(0xA3, 'Right Control', key('ctrl_r'))
VK_LMENU = KeyCode.register(0xA4, 'Left Alt', key('alt_l'))
VK_RMENU = KeyCode.register(0xA5, 'Right Alt', key('alt_r'))

# IME keys (user-triggerable)
VK_KANA = KeyCode.register(0x15, 'Kana mode')
VK_HANGUL = KeyCode.register(0x15, 'Hangul mode')
VK_ESCAPE = KeyCode.register(0x1B, 'Escape', key('esc'))
VK_CONVERT = KeyCode.register(0x1C, 'IME convert')
VK_NONCONVERT = KeyCode.register(0x1D, 'IME nonconvert')
VK_MODECHANGE = KeyCode.register(0x1F, 'IME mode change')

# Navigation keys
VK_SPACE = KeyCode.register(0x20, 'Space', key('space'))
VK_PRIOR = KeyCode.register(0x21, 'Page Up', key('page_up'))
VK_NEXT = KeyCode.register(0x22, 'Page Down', key('page_down'))
VK_END = KeyCode.register(0x23, 'End', key('end'))
VK_HOME = KeyCode.register(0x24, 'Home', key('home'))
VK_LEFT = KeyCode.register(0x25, 'Left Arrow', key('left'))
VK_UP = KeyCode.register(0x26, 'Up Arrow', key('up'))
VK_RIGHT = KeyCode.register(0x27, 'Right Arrow', key('right'))
VK_DOWN = KeyCode.register(0x28, 'Down Arrow', key('down'))

# System keys
VK_SELECT = KeyCode.register(0x29, 'Select')
VK_PRINT = KeyCode.register(0x2A, 'Print')
VK_EXECUTE = KeyCode.register(0x2B, 'Execute')
VK_SNAPSHOT = KeyCode.register(0x2C, 'Print Screen', key('print_screen'))
VK_INSERT = KeyCode.register(0x2D, 'Insert', key('insert'))
VK_DELETE = KeyCode.register(0x2E, 'Delete', key('delete'))
VK_HELP = KeyCode.register(0x2F, 'Help')

# Number keys
VK_0 = KeyCode.register(0x30, '0', ')')
VK_1 = KeyCode.register(0x31, '1', '!')
VK_2 = KeyCode.register(0x32, '2', '@')
VK_3 = KeyCode.register(0x33, '3', '#')
VK_4 = KeyCode.register(0x34, '4', '$')
VK_5 = KeyCode.register(0x35, '5', '%')
VK_6 = KeyCode.register(0x36, '6', '^')
VK_7 = KeyCode.register(0x37, '7', '&')
VK_8 = KeyCode.register(0x38, '8', '*')
VK_9 = KeyCode.register(0x39, '9', '(')

# Letter keys
VK_A = KeyCode.register(0x41, 'A', 'a')
VK_B = KeyCode.register(0x42, 'B', 'b')
VK_C = KeyCode.register(0x43, 'C', 'c')
VK_D = KeyCode.register(0x44, 'D', 'd')
VK_E = KeyCode.register(0x45, 'E', 'e')
VK_F = KeyCode.register(0x46, 'F', 'f')
VK_G = KeyCode.register(0x47, 'G', 'g')
VK_H = KeyCode.register(0x48, 'H', 'h')
VK_I = KeyCode.register(0x49, 'I', 'i')
VK_J = KeyCode.register(0x4A, 'J', 'j')
VK_K = KeyCode.register(0x4B, 'K', 'k')
VK_L = KeyCode.register(0x4C, 'L', 'l')
VK_M = KeyCode.register(0x4D, 'M', 'm')
VK_N = KeyCode.register(0x4E, 'N', 'n')
VK_O = KeyCode.register(0x4F, 'O', 'o')
VK_P = KeyCode.register(0x50, 'P', 'p')
VK_Q = KeyCode.register(0x51, 'Q', 'q')
VK_R = KeyCode.register(0x52, 'R', 'r')
VK_S = KeyCode.register(0x53, 'S', 's')
VK_T = KeyCode.register(0x54, 'T', 't')
VK_U = KeyCode.register(0x55, 'U', 'u')
VK_V = KeyCode.register(0x56, 'V', 'v')
VK_W = KeyCode.register(0x57, 'W', 'w')
VK_X = KeyCode.register(0x58, 'X', 'x')
VK_Y = KeyCode.register(0x59, 'Y', 'y')
VK_Z = KeyCode.register(0x5A, 'Z', 'z')

# Windows keys
VK_LWIN = KeyCode.register(0x5B, 'Left Super', key('cmd'), key('cmd_l'))
VK_RWIN = KeyCode.register(0x5C, 'Right Super', key('cmd_r'))
VK_APPS = KeyCode.register(0x5D, 'Applications', key('menu'))

# Numpad keys
VK_NUMPAD0 = KeyCode.register(0x60, 'Numpad 0')
VK_NUMPAD1 = KeyCode.register(0x61, 'Numpad 1')
VK_NUMPAD2 = KeyCode.register(0x62, 'Numpad 2')
VK_NUMPAD3 = KeyCode.register(0x63, 'Numpad 3')
VK_NUMPAD4 = KeyCode.register(0x64, 'Numpad 4')
VK_NUMPAD5 = KeyCode.register(0x65, 'Numpad 5')
VK_NUMPAD6 = KeyCode.register(0x66, 'Numpad 6')
VK_NUMPAD7 = KeyCode.register(0x67, 'Numpad 7')
VK_NUMPAD8 = KeyCode.register(0x68, 'Numpad 8')
VK_NUMPAD9 = KeyCode.register(0x69, 'Numpad 9')

VK_MULTIPLY = KeyCode.register(0x6A, 'Numpad Multiply')
VK_ADD = KeyCode.register(0x6B, 'Numpad Add')
VK_SUBTRACT = KeyCode.register(0x6D, 'Numpad Subtract')
VK_DECIMAL = KeyCode.register(0x6E, 'Numpad Decimal')
VK_DIVIDE = KeyCode.register(0x6F, 'Numpad Divide')

# Function keys
VK_F1 = KeyCode.register(0x70, 'F1', key('f1'))
VK_F2 = KeyCode.register(0x71, 'F2', key('f2'))
VK_F3 = KeyCode.register(0x72, 'F3', key('f3'))
VK_F4 = KeyCode.register(0x73, 'F4', key('f4'))
VK_F5 = KeyCode.register(0x74, 'F5', key('f5'))
VK_F6 = KeyCode.register(0x75, 'F6', key('f6'))
VK_F7 = KeyCode.register(0x76, 'F7', key('f7'))
VK_F8 = KeyCode.register(0x77, 'F8', key('f8'))
VK_F9 = KeyCode.register(0x78, 'F9', key('f9'))
VK_F10 = KeyCode.register(0x79, 'F10', key('f10'))
VK_F11 = KeyCode.register(0x7A, 'F11', key('f11'))
VK_F12 = KeyCode.register(0x7B, 'F12', key('f12'))
VK_F13 = KeyCode.register(0x7C, 'F13', key('f13'))
VK_F14 = KeyCode.register(0x7D, 'F14', key('f14'))
VK_F15 = KeyCode.register(0x7E, 'F15', key('f15'))
VK_F16 = KeyCode.register(0x7F, 'F16', key('f16'))
VK_F17 = KeyCode.register(0x80, 'F17', key('f17'))
VK_F18 = KeyCode.register(0x81, 'F18', key('f18'))
VK_F19 = KeyCode.register(0x82, 'F19', key('f19'))
VK_F20 = KeyCode.register(0x83, 'F20', key('f20'))

# Lock keys
VK_NUMLOCK = KeyCode.register(0x90, 'Num Lock', key('num_lock'))
VK_SCROLL = KeyCode.register(0x91, 'Scroll Lock', key('scroll_lock'))

# Volume keys (not standardised, but common)
VK_VOLUME_MUTE = KeyCode.register(0xAD, 'Volume Mute', key('media_volume_mute'))
VK_VOLUME_DOWN = KeyCode.register(0xAE, 'Volume Down', key('media_volume_down'))
VK_VOLUME_UP = KeyCode.register(0xAF, 'Volume Up', key('media_volume_up'))
VK_MEDIA_NEXT_TRACK = KeyCode.register(0xB0, 'Next Track', key('media_next'))
VK_MEDIA_PREV_TRACK = KeyCode.register(0xB1, 'Previous Track', key('media_previous'))
VK_MEDIA_PLAY_PAUSE = KeyCode.register(0xB3, 'Play/Pause', key('media_play_pause'))

# OEM keys (these may vary by region)
VK_OEM_1 = KeyCode.register(0xBA, ';', ':')
VK_OEM_PLUS = KeyCode.register(0xBB, '+', '=')
VK_OEM_COMMA = KeyCode.register(0xBC, ',', '<')
VK_OEM_MINUS = KeyCode.register(0xBD, '-', '_')
VK_OEM_PERIOD = KeyCode.register(0xBE, '.', '>')
VK_OEM_2 = KeyCode.register(0xBF, '/', '?')
VK_OEM_3 = KeyCode.register(0xC0, "'", '"')
VK_OEM_4 = KeyCode.register(0xDB, '[', '{')
VK_OEM_5 = KeyCode.register(0xDC, '\\', '|')
VK_OEM_6 = KeyCode.register(0xDD, ']', '}')
VK_OEM_7 = KeyCode.register(0xDE, '#')
VK_OEM_8 = KeyCode.register(0xDF, '`', '~')

# Custom events
VK_SCROLL_UP = KeyCode.register(0xFF + 1, 'Scroll up')
VK_SCROLL_DOWN = KeyCode.register(0xFF + 2, 'Scroll down')
VK_SCROLL_LEFT = KeyCode.register(0xFF + 3, 'Scroll left')
VK_SCROLL_RIGHT = KeyCode.register(0xFF + 4, 'Scroll right')

# Gamepad buttons
BUTTON_DPAD_UP = GamepadCode.register(0x000001, '↑')
BUTTON_DPAD_DOWN = GamepadCode.register(0x000002, '↓')
BUTTON_DPAD_LEFT = GamepadCode.register(0x000004, '←')
BUTTON_DPAD_RIGHT = GamepadCode.register(0x000008, '→')
BUTTON_START = GamepadCode.register(0x000010, 'Start')
BUTTON_BACK = GamepadCode.register(0x000020, 'Select')
BUTTON_LEFT_THUMB = GamepadCode.register(0x000040, 'LS')
BUTTON_RIGHT_THUMB = GamepadCode.register(0x000080, 'RS')
BUTTON_LEFT_SHOULDER = GamepadCode.register(0x000100, 'LB')
BUTTON_RIGHT_SHOULDER = GamepadCode.register(0x000200, 'RB')
BUTTON_A = GamepadCode.register(0x001000, 'A')
BUTTON_B = GamepadCode.register(0x002000, 'B')
BUTTON_X = GamepadCode.register(0x004000, 'X')
BUTTON_Y = GamepadCode.register(0x008000, 'Y')
TRIGGER_LEFT = GamepadCode.register(0x040000, 'LT')
TRIGGER_RIGHT = GamepadCode.register(0x080000, 'RT')

# Group codes
CLICK_CODES = (VK_LBUTTON, VK_MBUTTON, VK_RBUTTON)
MOUSE_CODES = CLICK_CODES + (VK_XBUTTON1, VK_XBUTTON2)
SCROLL_CODES = (VK_SCROLL_UP, VK_SCROLL_DOWN, VK_SCROLL_LEFT, VK_SCROLL_RIGHT)
VOLUME_CODES = (VK_VOLUME_DOWN, VK_VOLUME_UP)
KEYBOARD_CODES = tuple(KeyCode(i) for i in range(256) if i not in MOUSE_CODES)
GAMEPAD_CODES = (BUTTON_DPAD_UP, BUTTON_DPAD_DOWN, BUTTON_DPAD_LEFT, BUTTON_DPAD_RIGHT,
                 BUTTON_START, BUTTON_BACK,
                 BUTTON_LEFT_THUMB, BUTTON_RIGHT_THUMB,
                 BUTTON_LEFT_SHOULDER, BUTTON_RIGHT_SHOULDER,
                 BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y,
                 TRIGGER_LEFT, TRIGGER_RIGHT)
