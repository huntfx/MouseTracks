"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Define all the editable settings

from __future__ import absolute_import

from locale import getdefaultlocale

from ..misc import format_file_path, get_config_file
from ..constants import DEFAULT_PATH, DEFAULT_LANGUAGE, MAX_INT, APP_LIST_FILE
from ..utils.ini import Config
from ..utils.os import OS_DEBUG


CONFIG_PATH = format_file_path('{}\\settings.ini'.format(DEFAULT_PATH))

CONFIG_PATH_DEFAULT = get_config_file('settings-default.ini')

try:
    _language = getdefaultlocale()[0]
except ValueError:
    _language = DEFAULT_LANGUAGE

_save_freq = 20 if OS_DEBUG else 180

CONFIG_DEFAULTS = {
    'Main': {
        '__priority__': 1,
        'Language': {
            '__info__': 'Choose a language. If there is any issue or the files don\'t exit yet, {} will be used.'.format(DEFAULT_LANGUAGE),
            '__priority__': 1,
            'value': _language,
            'type': str,
        },
        'StartMinimised': {
            '__info__': 'Launch the program and have it only appear in the tray. Only works in Windows if the elevation is allowed through UAC.',
            'value': False,
            'type': bool
        },
        'HistoryLength': {
            '__info__': 'How many seconds to store of the track history. Each hour increases the file size by roughly 1.5mb.',
            '__priority__': 2,
            'value': 3600,
            'type': int,
            'min': 0
        },
        'RunAsAdministrator': {
            '__info__': 'This fixes tracking not working on elevated programs.',
            'value': False,
            'type': bool
        },
        '_TrackGamepads': {
            'value': True,
            'type': bool
        }
    },
    'Paths': {
        '__info__': 'You may use environment variables such as %APPDATA%. %DOCUMENTS% points to a different location depending on the operating system.',
        '__priority__': 2,
        'Data': {
            '__priority__': 1,
            'value': '{}\\Data\\'.format(DEFAULT_PATH),
            'type': str
        },
        'Images': {
            '__info__': 'Default place to save images. [Name] is replaced by the name of the application.',
            '__priority__': 2,
            'value': '{}\\Images\\[Name]'.format(DEFAULT_PATH),
            'type': str
        },
        'AppList': {
            '__priority__': 3,
            'value': '{}\\{}'.format(DEFAULT_PATH, APP_LIST_FILE),
            'type': str
        }
    },
    'Internet': {
        '__priority__': 3,
        'Enable': {
            '__priority__': 1,
            'value': True,
            'type': bool
        },
        'UpdateApplications': {
            '__info__': 'How often (in minutes) to update the list from the internet. Set to 0 to disable.',
            'value': 86400,
            'type': int,
            'min': 0
        }
    },
    'Save': {
        '__priority__': 4,
        'Frequency': {
            '__info__': 'Choose how often to save the file, don\'t set it too low or the program won\'t be able to keep up. Set to 0 to disable.',
            '__priority__': 1,
            'value': 180,
            'type': int,
            'min': 0
        },
        'MaximumAttempts': {
            '__info__': 'Maximum number of failed save attempts before the tracking continues.',
            'value': 3,
            'type': int,
            'min': 1
        },
        'WaitAfterFail': {
            '__info__': 'How many seconds to wait before trying again.',
            'value': 5,
            'type': int,
            'min': 0
        },
        'SavesBeforeUnload': {
            '__info__': 'How many saves can pass before an application is unloaded from memory.',
            'value': 5,
            'type': int,
            'min': 0
        }
    },
    'GenerateImages': {
        '__priority__': 5,
        '_UpscaleResolutionX': {
            'type': int,
        },
        '_UpscaleResolutionY': {
            'type': int,
        },
        '_OutputResolutionX': {
            'type': int,
        },
        '_OutputResolutionY': {
            'type': int,
        },
        'HighPrecision': {
            '__info__': 'Enable this for higher quality images. Increases render time.',
            '__priority__': 2,
            'value': False,
            'type': bool,
        },
        'AutomaticResolution': {
            '__priority__': 3,
            'value': True,
            'type': bool,
        },
        'OutputResolutionX': {
            '__priority__': 4,
            '__info__': 'Custom image width to use if AutomaticResolution is disabled.',
            'type': int,
            'min': 0
        },
        'OutputResolutionY': {
            '__priority__': 5,
            '__info__': 'Custom image height to use if AutomaticResolution is disabled.',
            'type': int,
            'min': 0
        },
        'FileType': {
            '__priority__': 1,
            '__info__': 'Choose if you want jpg (smaller size) or png (higher quality) image.',
            'value': 'png',
            'type': str,
            'case_sensitive': False,
            'valid': ('jpg', 'jpeg', 'png', 'bmp')
        },
        'OpenOnFinish': {
            '__priority__': 6,
            '__info__': 'Open the folder containing the image(s) once the render is complete.',
            'value': True,
            'type': bool
        }
    },
    'GenerateTracks': {
        '__priority__': 6,
        'FileName': {
            '__priority__': 1,
            'value': '[[RunningTimeSeconds]]Tracks - [ColourProfile] [HighPrecision]',
            'type': str
        },
        'ColourProfile': {
            '__priority__': 2,
            'type': str,
            'allow_empty': True
        }
    },
    'GenerateSpeed': {
        '__priority__': 7,
        'FileName': {
            '__priority__': 1,
            'value': '[[RunningTimeSeconds]]Speed - [ColourProfile] [HighPrecision]',
            'type': str
        },
        'ColourProfile': {
            '__priority__': 2,
            'type': str,
            'allow_empty': True
        }
    },
    'GenerateStrokes': {
        '__priority__': 7,
        'FileName': {
            '__priority__': 1,
            'value': '[[RunningTimeSeconds]]Strokes - [ColourProfile] [HighPrecision]',
            'type': str
        },
        'ColourProfile': {
            '__priority__': 2,
            'type': str,
            'allow_empty': True
        }
    },
    'GenerateHeatmap': {
        '__priority__': 8,
        'FileName': {
            '__priority__': 1,
            'value': '[[RunningTimeSeconds]]Clicks ([MouseButton]) - [ColourProfile]',
            'type': str
        },
        'ColourProfile': {
            '__priority__': 2,
            'value': 'Jet',
            'type': str,
            'allow_empty': True
        },
        'GaussianBlurMultiplier': {
            '__info__': 'Change the size multiplier of the gaussian blur. Smaller values are less smooth but show more detail.',
            '__priority__': 3,
            'value': 1.0,
            'type': float,
            'min': 0
        },
        '_MouseButtonLeft': {
            'value': True,
            'type': bool
        },
        '_MouseButtonMiddle': {
            'value': True,
            'type': bool
        },
        '_MouseButtonRight': {
            'value': True,
            'type': bool
        },
        '_GaussianBlurBase': {
            'value': 0.0125,
            'type': float,
            'min': 0
        }
    },
    'GenerateKeyboard': {
        '__priority__': 9,
        'FileName': {
            '__priority__': 1,
            'value': '[[RunningTimeSeconds]]Keyboard - [ColourProfile] ([DataSet])',
            'type': str
        },
        'ColourProfile': {
            '__priority__': 2,
            'type': str,
            'allow_empty': True
        },
        'ExtendedKeyboard': {
            '__info__': 'If the full keyboard should be shown, or just the main section.',
            '__priority__': 3,
            'value': True,
            'type': bool
        },
        'SizeMultiplier': {
            '__info__': 'Change the size of everything at once.',
            'value': 1,
            'type': float
        },
        'DataSet': {
            '__info__': 'Set if the colours should be determined by the total time the key has been held (time), or the number of presses (press).',
            '__priority__': 4,
            'value': 'time',
            'type': str,
            'case_sensitive': False,
            'valid': ('time', 'press')
            
        },
        'LinearMapping': {
            '__note__': 'Set if a linear mapping for colours should be used.',
            '__priority__': 10,
            'value': False,
            'type': bool
        
        },
        'LinearPower': {
            '__note__': 'Set the exponential to raise the linear values to.',
            '__priority__': 11,
            'value': 1.0,
            'type': float
        }
    },
    'GenerateCSV': {
        '__info__': 'This is for anyone who may want to use the recorded data in their own projects.',
        '__priority__': 10,
        'FileNameTracks': {
            '__priority__': 1,
            'value': '[[RunningTimeSeconds]] Tracks ([Width], [Height])',
            'type': str
        },
        'FileNameClicks': {
            '__priority__': 1,
            'value': '[[RunningTimeSeconds]] Clicks ([Width], [Height]) [MouseButton]',
            'type': str
        },
        'FileNameKeyboard': {
            '__priority__': 1,
            'value': '[[RunningTimeSeconds]] Keyboard',
            'type': str
        },
        'MinimumPoints': {
            '__info__': 'Files will not be generated for any resolutions that have fewer points than this recorded.',
            'value': 50,
            'type': int
        },
        '_GenerateTracks': {
            'value': True,
            'type': bool
        },
        '_GenerateClicks': {
            'value': True,
            'type': bool
        },
        '_GenerateKeyboard': {
            'value': True,
            'type': bool
        }
    },
    'API': {
        '__priority__': 4,
        'SocketServer': {
            '__info__': 'Run an encrypted socket server so that a client can connect and receive messages.',
            '__priority__': 1,
            'value': False,
            'type': bool
        },
        'WebServer': {
            '__info__': 'Run a web service to communicate with the main script. Required for more advanced features.',
            '__priority__': 1,
            'value': True,
            'type': bool
        },
        '_ServerEncryption': {
            'value': True,
            'type': bool,
            'lock': True
        }
    },
    'Advanced': {
        'MessageLevel': {
            '__info__': 'Choose the level of messages to show. 0 will show everything, and 3 will show nothing.',
            'value': int(not OS_DEBUG),  #If debug, show more messages
            'type': int,
            'min': 0,
            'max': 3
        },
        'HeatmapRangeClipping': {
            '__info__': 'Lower the highest value when generating a heatmap.',
            'value': 0.005,
            'type': float,
            'min': 0,
            'max': 1
        },
        'CompressTrackMax': {
            '__info__': 'Maximum number of of ticks before compression happens. Set to 0 to disable.',
            'value': 425000,
            'type': int,
            'min': 0,
            'max': MAX_INT
        },
        'CompressTrackAmount': {
            '__info__': 'How much to divide each pixel by when compression happens.',
            'value': 1.1,
            'type': float,
            'min': 1.001
        },
        'CheckResolution': {
            '__info__': 'How many ticks to wait between checking the resolution.',
            'value': 60,
            'type': int,
            'min': 0
        },
        'CheckRunningApplications': {
            '__info__': 'How many ticks to wait between checking if something is running.',
            'value': 60,
            'type': int,
            'min': 0
        },
        'ReloadApplicationList': {
            '__info__': 'How many ticks to wait before reloading {}.'.format(APP_LIST_FILE),
            'value': 18000,
            'type': int,
            'min': 0
        },
        'ShowQueuedCommands': {
            '__info__': 'How many ticks to wait before showing the number of commands waiting to be processed.',
            'value': 1200,
            'type': int,
            'min': 0
        },
        'RepeatKeyPress': {
            '__info__': 'How many ticks to wait before recording a new key press if a key is being held down (set to 0 to disable).',
            'value': 0,
            'type': int,
            'min': 0
        },
        'RepeatClicks': {
            '__info__': 'How many ticks to wait before recording a click if a mouse button is being held down (set to 0 to disable).',
            'value': 14,
            'type': int,
            'min': 0
        },
        'RepeatButtonPress': {
            '__info__': 'How many ticks to wait before recording a new gamepad button press if a button is being held down (set to 0 to disable).',
            'value': 0,
            'type': int,
            'min': 0
        },
        'KeyboardKeySize': {
            'value': 65.0,
            'type': float,
            'min': 0
        },
        'KeyboardKeyCornerRadius': {
            'value': 3.0,
            'type': float,
            'min': 0
        },
        'KeyboardKeyPadding': {
            'value': 8.0,
            'type': float,
            'min': 0
        },
        'KeyboardKeyBorder': {
            'value': 0.6,
            'type': float,
            'min': 0
        },
        'KeyboardDropShadowX': {
            'value': 1.25,
            'type': float,
            'min': 0
        },
        'KeyboardDropShadowY': {
            'value': 1.5,
            'type': float,
            'min': 0
        },
        'KeyboardImagePadding': {
            'value': 16.0,
            'type': float,
            'min': 0
        },
        'KeyboardFontSizeMain': {
            'value': 17.0,
            'type': float,
            'min': 0
        },
        'KeyboardFontSizeStats': {
            'value': 13.0,
            'type': float,
            'min': 0
        },
        'KeyboardFontHeightOffset': {
            'value': 5.0,
            'type': float,
            'min': 0
        },
        'KeyboardFontWidthOffset': {
            'value': 5.0,
            'type': float,
            'min': 0
        },
        'KeyboardFontSpacing': {
            'value': 5.0,
            'type': float,
            'min': 0
        },
        'HistoryCheck': {
            '__info__': 'How many ticks to wait before checking the history length and trimming if needed.',
            'value': 1200,
            'type': int,
            'min': 0
        },
        'RefreshGamepads': {
            '__info__': 'How many ticks to wait before refreshing the list of connected gamepads.',
            'value': 600,
            'type': int,
            'min': 1
        },
        'KeypressIntervalMax': {
            '__info__': 'Maximum number of ticks between recorded keypresses. Set to a negative number for infinite.',
            'value': 600,
            'type': int
        },
        'IdleTime': {
            '__info__': 'How many ticks of inactivity allowed before recording as idle.',
            'value': 6000,
            'type': int
        },
        'MinSessionTime': {
            '__info__': 'Sessions with fewer ticks than this will be merged.',
            'value': 1800,
            'type': int
        },
        'APIPollingRate': {
            '__info__': 'How many ticks between each API check.',
            'value': 10,
            'type': int,
            'min': 1
        }
    }
}


CONFIG = Config(CONFIG_DEFAULTS).load(CONFIG_PATH, CONFIG_PATH_DEFAULT).save(CONFIG_PATH, comment_spacing=40)