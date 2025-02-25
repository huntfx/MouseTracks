"""Register all keycodes in use.

https://learn.microsoft.com/en-us/windows/win32/inputdev/virtual-key-codes

Some keys trigger multiple codes at once.
This will need to be handled in stats/renders.
    - Left control: VK_CONTROL + VK_LCONTROL
    - Right control: VK_CONTROL + VK_RCONTROL
    - Left alt: VK_MENU + VK_LMENU
    - Right alt: VK_MENU + VK_RMENU + VK_CONTROL + VK_LCONTROL
"""

from typing import Self


class KeyCode(int):
    """Add a name to a keycode.
    Each keycode may have one name, and setting a new one will overwrite
    it.
    """

    _REGISTRY: dict[int, str] = {}

    def __new__(cls, code: int, name: str | None = None) -> Self:
        return super().__new__(cls, code)

    def __init__(self, code: int, name: str | None = None) -> None:
        if name is None:
            self._name = self._REGISTRY.get(code, '')
        else:
            self._name = self._REGISTRY[code] = name
        super().__init__()

    def __repr__(self) -> str:
        return f'{type(self).__name__}({self:#04X}, {self._name!r})'

    def __str__(self) -> str:
        if self._name:
            return self._name
        return f'{self:#04X}'

    @property
    def name(self) -> str:
        """Get the keycode name."""
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        """Set a new keycode name."""
        self._name = self._REGISTRY[int(self)] = name


class GamepadCode(KeyCode):
    _REGISTRY: dict[int, str] = {}


# Mouse buttons
VK_LBUTTON = KeyCode(0x01, 'Left mouse button')
VK_RBUTTON = KeyCode(0x02, 'Right mouse button')
VK_MBUTTON = KeyCode(0x04, 'Middle mouse button')
VK_XBUTTON1 = KeyCode(0x05, 'Mouse button 4')
VK_XBUTTON2 = KeyCode(0x06, 'Mouse button 5')

# Control keys
VK_BACK = KeyCode(0x08, 'Backspace')
VK_TAB = KeyCode(0x09, 'Tab')
VK_CLEAR = KeyCode(0x0C, 'Clear')
VK_RETURN = KeyCode(0x0D, 'Enter')
VK_SHIFT = KeyCode(0x10, 'Shift')
VK_CONTROL = KeyCode(0x11, 'Control')
VK_MENU = KeyCode(0x12, 'Alt')
VK_PAUSE = KeyCode(0x13, 'Pause')
VK_CAPITAL = KeyCode(0x14, 'Caps Lock')

VK_LSHIFT = KeyCode(0xA0, 'Left Shift')
VK_RSHIFT = KeyCode(0xA1, 'Right Shift')
VK_LCONTROL = KeyCode(0xA2, 'Left Control')
VK_RCONTROL = KeyCode(0xA3, 'Right Control')
VK_LMENU = KeyCode(0xA4, 'Left Alt')
VK_RMENU = KeyCode(0xA5, 'Right Alt')

# IME keys (user-triggerable)
VK_KANA = KeyCode(0x15, 'Kana mode')
VK_HANGUL = KeyCode(0x15, 'Hangul mode')
VK_ESCAPE = KeyCode(0x1B, 'Escape')
VK_CONVERT = KeyCode(0x1C, 'IME convert')
VK_NONCONVERT = KeyCode(0x1D, 'IME nonconvert')
VK_MODECHANGE = KeyCode(0x1F, 'IME mode change')

# Navigation keys
VK_SPACE = KeyCode(0x20, 'Space')
VK_PRIOR = KeyCode(0x21, 'Page Up')
VK_NEXT = KeyCode(0x22, 'Page Down')
VK_END = KeyCode(0x23, 'End')
VK_HOME = KeyCode(0x24, 'Home')
VK_LEFT = KeyCode(0x25, 'Left Arrow')
VK_UP = KeyCode(0x26, 'Up Arrow')
VK_RIGHT = KeyCode(0x27, 'Right Arrow')
VK_DOWN = KeyCode(0x28, 'Down Arrow')

# System keys
VK_SELECT = KeyCode(0x29, 'Select')
VK_PRINT = KeyCode(0x2A, 'Print')
VK_EXECUTE = KeyCode(0x2B, 'Execute')
VK_SNAPSHOT = KeyCode(0x2C, 'Print Screen')
VK_INSERT = KeyCode(0x2D, 'Insert')
VK_DELETE = KeyCode(0x2E, 'Delete')
VK_HELP = KeyCode(0x2F, 'Help')

# Number keys
VK_0 = KeyCode(0x30, '0')
VK_1 = KeyCode(0x31, '1')
VK_2 = KeyCode(0x32, '2')
VK_3 = KeyCode(0x33, '3')
VK_4 = KeyCode(0x34, '4')
VK_5 = KeyCode(0x35, '5')
VK_6 = KeyCode(0x36, '6')
VK_7 = KeyCode(0x37, '7')
VK_8 = KeyCode(0x38, '8')
VK_9 = KeyCode(0x39, '9')

# Letter keys
VK_A = KeyCode(0x41, 'A')
VK_B = KeyCode(0x42, 'B')
VK_C = KeyCode(0x43, 'C')
VK_D = KeyCode(0x44, 'D')
VK_E = KeyCode(0x45, 'E')
VK_F = KeyCode(0x46, 'F')
VK_G = KeyCode(0x47, 'G')
VK_H = KeyCode(0x48, 'H')
VK_I = KeyCode(0x49, 'I')
VK_J = KeyCode(0x4A, 'J')
VK_K = KeyCode(0x4B, 'K')
VK_L = KeyCode(0x4C, 'L')
VK_M = KeyCode(0x4D, 'M')
VK_N = KeyCode(0x4E, 'N')
VK_O = KeyCode(0x4F, 'O')
VK_P = KeyCode(0x50, 'P')
VK_Q = KeyCode(0x51, 'Q')
VK_R = KeyCode(0x52, 'R')
VK_S = KeyCode(0x53, 'S')
VK_T = KeyCode(0x54, 'T')
VK_U = KeyCode(0x55, 'U')
VK_V = KeyCode(0x56, 'V')
VK_W = KeyCode(0x57, 'W')
VK_X = KeyCode(0x58, 'X')
VK_Y = KeyCode(0x59, 'Y')
VK_Z = KeyCode(0x5A, 'Z')

# Windows keys
VK_LWIN = KeyCode(0x5B, 'Left Windows key')
VK_RWIN = KeyCode(0x5C, 'Right Windows key')
VK_APPS = KeyCode(0x5D, 'Applications key')

# Numpad keys
VK_NUMPAD0 = KeyCode(0x60, 'Numpad 0')
VK_NUMPAD1 = KeyCode(0x61, 'Numpad 1')
VK_NUMPAD2 = KeyCode(0x62, 'Numpad 2')
VK_NUMPAD3 = KeyCode(0x63, 'Numpad 3')
VK_NUMPAD4 = KeyCode(0x64, 'Numpad 4')
VK_NUMPAD5 = KeyCode(0x65, 'Numpad 5')
VK_NUMPAD6 = KeyCode(0x66, 'Numpad 6')
VK_NUMPAD7 = KeyCode(0x67, 'Numpad 7')
VK_NUMPAD8 = KeyCode(0x68, 'Numpad 8')
VK_NUMPAD9 = KeyCode(0x69, 'Numpad 9')

VK_MULTIPLY = KeyCode(0x6A, 'Numpad Multiply')
VK_ADD = KeyCode(0x6B, 'Numpad Add')
VK_SUBTRACT = KeyCode(0x6D, 'Numpad Subtract')
VK_DECIMAL = KeyCode(0x6E, 'Numpad Decimal')
VK_DIVIDE = KeyCode(0x6F, 'Numpad Divide')

# Function keys
VK_F1 = KeyCode(0x70, 'F1')
VK_F2 = KeyCode(0x71, 'F2')
VK_F3 = KeyCode(0x72, 'F3')
VK_F4 = KeyCode(0x73, 'F4')
VK_F5 = KeyCode(0x74, 'F5')
VK_F6 = KeyCode(0x75, 'F6')
VK_F7 = KeyCode(0x76, 'F7')
VK_F8 = KeyCode(0x77, 'F8')
VK_F9 = KeyCode(0x78, 'F9')
VK_F10 = KeyCode(0x79, 'F10')
VK_F11 = KeyCode(0x7A, 'F11')
VK_F12 = KeyCode(0x7B, 'F12')

# Lock keys
VK_NUMLOCK = KeyCode(0x90, 'Num Lock')
VK_SCROLL = KeyCode(0x91, 'Scroll Lock')

# OEM keys (these may vary by region)
VK_OEM_1 = KeyCode(0xBA, ';')
VK_OEM_PLUS = KeyCode(0xBB, '+')
VK_OEM_COMMA = KeyCode(0xBC, ',')
VK_OEM_MINUS = KeyCode(0xBD, '-')
VK_OEM_PERIOD = KeyCode(0xBE, '.')
VK_OEM_2 = KeyCode(0xBF, '/')
VK_OEM_3 = KeyCode(0xC0, '\'')
VK_OEM_4 = KeyCode(0xDB, '[')
VK_OEM_5 = KeyCode(0xDC, '|')
VK_OEM_6 = KeyCode(0xDD, ']')
VK_OEM_7 = KeyCode(0xDE, '#')

# Custom events
VK_SCROLL_UP = KeyCode(0xFF + 1, 'Scroll up')
VK_SCROLL_DOWN = KeyCode(0xFF + 2, 'Scroll down')
VK_SCROLL_LEFT = KeyCode(0xFF + 3, 'Scroll left')
VK_SCROLL_RIGHT = KeyCode(0xFF + 4, 'Scroll right')

# Gamepad buttons
BUTTON_DPAD_UP = GamepadCode(0x000001, '↑')
BUTTON_DPAD_DOWN = GamepadCode(0x000002, '↓')
BUTTON_DPAD_LEFT = GamepadCode(0x000004, '←')
BUTTON_DPAD_RIGHT = GamepadCode(0x000008, '→')
BUTTON_START = GamepadCode(0x000010, 'Start')
BUTTON_BACK = GamepadCode(0x000020, 'Select')
BUTTON_LEFT_THUMB = GamepadCode(0x000040, 'LS')
BUTTON_RIGHT_THUMB = GamepadCode(0x000080, 'RS')
BUTTON_LEFT_SHOULDER = GamepadCode(0x000100, 'LB')
BUTTON_RIGHT_SHOULDER = GamepadCode(0x000200, 'RB')
BUTTON_A = GamepadCode(0x001000, 'A')
BUTTON_B = GamepadCode(0x002000, 'B')
BUTTON_X = GamepadCode(0x004000, 'X')
BUTTON_Y = GamepadCode(0x008000, 'Y')
TRIGGER_LEFT = GamepadCode(0x040000, 'LT')
TRIGGER_RIGHT =  GamepadCode(0x080000, 'RT')

# Group codes
CLICK_CODES = (VK_LBUTTON, VK_MBUTTON, VK_RBUTTON)
MOUSE_CODES = CLICK_CODES + (VK_XBUTTON1, VK_XBUTTON2)
SCROLL_CODES = (VK_SCROLL_UP, VK_SCROLL_DOWN, VK_SCROLL_LEFT, VK_SCROLL_RIGHT)
KEYBOARD_CODES = tuple(KeyCode(i) for i in range(256) if i not in MOUSE_CODES)
GAMEPAD_CODES = (BUTTON_DPAD_UP, BUTTON_DPAD_DOWN, BUTTON_DPAD_LEFT, BUTTON_DPAD_RIGHT,
                 BUTTON_START, BUTTON_BACK,
                 BUTTON_LEFT_THUMB, BUTTON_RIGHT_THUMB,
                 BUTTON_LEFT_SHOULDER, BUTTON_RIGHT_SHOULDER,
                 BUTTON_A, BUTTON_B, BUTTON_X, BUTTON_Y,
                 TRIGGER_LEFT, TRIGGER_RIGHT)
