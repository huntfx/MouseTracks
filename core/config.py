"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import time
from locale import getdefaultlocale

from core.base import format_file_path, get_script_file
from core.compatibility import iteritems
from core.constants import DEFAULT_PATH, DEFAULT_LANGUAGE, MAX_INT, APP_LIST_FILE
from core.os import get_resolution, create_folder, OS_DEBUG


CONFIG_PATH = format_file_path('{}\\config.ini'.format(DEFAULT_PATH))

CONFIG_DEFAULT = get_script_file('config-default.ini')

try:
    _language = getdefaultlocale()[0]
except ValueError:
    _language = DEFAULT_LANGUAGE

_save_freq = 20 if OS_DEBUG else 180

DEFAULTS = {
    'Main': {
        '__priority__': 1,
        'Language': {
            '__info__': 'Choose a language. If there is any issue or the files don\'t exit yet, {} will be used.'.format(_language, DEFAULT_LANGUAGE),
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
        'MaximumAttemptsNormal': {
            '__info__': 'Maximum number of failed save attempts before the tracking continues.',
            'value': 3,
            'type': int,
            'min': 1
        },
        'MaximumAttemptsSwitch': {
            '__info__': 'Maximum number of failed save attempts when switching profile.',
            'value': 24,
            'type': int,
            'min': 1
        },
        'WaitAfterFail': {
            '__info__': 'How many seconds to wait before trying again.',
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
            'valid': ('jpg', 'jpeg', 'png')
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
            'value': 'Citrus',
            'type': str
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
            'value': 'BlackToWhite',
            'type': str
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
            'type': str
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
            'value': 'Aqua',
            'type': str
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
        'RunServer': {
            '__info__': 'Run a server so that a client can connect and receive messages. Will be overriden by a GUI or tray icon.',
            '__priority__': 1,
            'value': False,
            'type': bool
        },
        'RunWeb': {
            '__info__': 'Run a web service to communicate with the main script. Will be overriden by a GUI or tray icon.',
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
        'RunAsAdministrator': {
            '__info__': 'This fixes tracking not working on elevated programs.',
            'value': True,
            'type': bool
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
        }
    }
}

def _get_priority_order(values, key='__priority__', default=None):
    """Use the __priority__ key to build a sorted list of config values.

    The list starts from the lowest value, and by default,
    the first gap will be filled with anything without a value.
    Changing default will instead assign all those values
    to a particular priority
    """
    #Build dict of values grouped by priority
    priorities = {}
    for k, v in iteritems(values):
        if not k.startswith('_'):
            priority = v.get(key, default)
            try:
                priorities[priority].append(k)
            except KeyError:
                priorities[priority] = [k]
                
    #Build list of sorted values
    try:
        current = min(i for i in priorities if i is not None)
    except ValueError:
        current = 0
    order = []
    while priorities:
        try:
            order += sorted(priorities.pop(current))
        except KeyError:
            try:
                order += sorted(priorities.pop(None))
            except KeyError:
                pass
        current += 1
    return order


class _ConfigItem(object):
    """Base class for values in the config file.
    All types inhert off this, which means they can be locked if needed.
    """
    @property
    def default(self):
        """Get the default value set by the config."""
        return self._data['default']
    
    @property
    def lock(self):
        """Lock the variable from being modified."""
        return self._data.get('lock', False)
    
    @lock.setter
    def lock(self, value):
        """Change the lock state."""
        self._data['lock'] = value
    
    @property
    def raw(self):
        """Return the actual value."""
        return self._data['value']


class _ConfigItemNumber(_ConfigItem):
    """Base class for floats and integerss.
    Inherits from _ConfigItem.
    """
    def validate(self, value):
        """Return a validated number or None."""
        try:
            value = self._data['type'](value)
        except ValueError:
            return None
        min_value = self._data.get('min', None)
        if min_value is not None:
            value = max(value, min_value)
        max_value = self._data.get('max', None)
        if max_value is not None:
            value = min(value, max_value)
        return value
            
    @property
    def min(self):
        return self._data.get('min', None)
        
    @property
    def max(self):
        return self._data.get('max', None)

        
class _ConfigItemStr(str, _ConfigItem):
    """Add controls to strings."""
    def __new__(cls, config_dict):
        cls._data = config_dict
        return str.__new__(cls, cls._data['value'])
    
    def validate(self, value):
        """Return a validated string or None."""
        value = str(value)
        case_sensitive = self._data.get('case_sensitive', False)
        valid_list = self._data.get('valid', None)
        if valid_list is not None:
            if not case_sensitive:
                valid_list = [i.lower() for i in valid_list]
                value = value.lower()
            if value not in valid_list:
                return None
        return value
    
    @property
    def valid(self):
        """Return tuple of all valid options, or None if not set."""
        return self._data.get('valid', None)
    
    @property
    def type(self):
        return str

        
class _ConfigItemInt(int, _ConfigItemNumber):
    """Add controls to integers."""
    def __new__(cls, config_dict):
        cls._data = config_dict
        return int.__new__(cls, cls._data['value'])
        
    @property
    def type(self):
        return int
    
        
class _ConfigItemFloat(float, _ConfigItemNumber):
    """Add controls to floats."""
    def __new__(cls, config_dict):
        cls._data = config_dict
        return float.__new__(cls, cls._data['value'])
    
    @property
    def type(self):
        return float

        
class _ConfigItemBool(int, _ConfigItem):
    """Add controls to booleans.
    
    Due to a limitation with Python not allowing bool inheritance,
    the values are actually stored as integers.
    """
    def __new__(cls, config_dict):
        cls._data = config_dict
        cls._data['default'] = int(cls._data['default'])
        return int.__new__(cls, cls._data['value'])
    
    def validate(self, value):
        if isinstance(value, str):
            if value.lower() in ('0', 'f', 'false', 'no', 'null', 'n'):
                return False
            else:
                return True
        return bool(value)
    
    @property
    def type(self):
        return bool


def create_config_item(config_dict, item_type=None):
    """Convert a normal variable into a config item."""
    config_items = {str: _ConfigItemStr, int: _ConfigItemInt, float: _ConfigItemFloat, bool: _ConfigItemBool}
    return config_items[item_type or config_dict['type']](config_dict)   

    
class _ConfigDict(dict):
    """Handle the variables inside the config."""
    def __init__(self, config_dict, show_hidden=False):
        self._data = config_dict
        super(_ConfigDict, self).__init__(self._data)
        self.hidden = not show_hidden

    def __repr__(self):
        return dict(self.__iter__()).__repr__()
        
    def __iter__(self):
        for k, v in iteritems(self):
            if self.hidden and k.startswith('_'):
                continue
            yield k, v['value']

    def __getitem__(self, item):
        """Return a config item instance."""
        return create_config_item(self._data[item])

    def __setitem__(self, item, value):
        """Set a new value and make sure it follows any set limits."""
        info = self._data[item]

        if info.get('lock', False):
            return
        
        validated = create_config_item(self._data[item]).validate(value)
        if validated is not None:
            self._data[item]['value'] = validated


class Config(dict):
    """Store all the variables used within the config file.
    
    Inheritance:
        Config
            _ConfigDict
                _ConfigItem
                    _ConfigItemStr
                    _ConfigItemNumber
                        _ConfigItemInt
                        _ConfigItemFloat
    
        Example:
            >>> c = Config
            >>> type(c)
            <class '__main__.Config'>
            >>> type(c['Main'])
            <class '__main__._ConfigDict'>
            >>> type(c['Main']['Language'])
            <class '__main__._ConfigItemStr'>
    """

    _DEFAULT_VALUES = {int: 0, float: 0.0, str: '', bool: False}
    
    def __init__(self, defaults=DEFAULTS, show_hidden=False):
        self._data = {}
        self._load_from_dict(defaults)
        self.hidden = not show_hidden
        self.is_new = False
        super(Config, self).__init__(self._data)

    def __repr__(self):
        """Convert to dict and use __repr__ from that."""
        return dict(self.__iter__()).__repr__()

    def __iter__(self):
        """Show only values when converting to dict."""
        for k, v in iteritems(self):
            yield k, _ConfigDict(v)
                
    def __getitem__(self, item):
        """Return all values under a heading."""
        return _ConfigDict(self._data[item], show_hidden=not self.hidden)

    def _load_from_dict(self, config_dict):
        """Read data from the default dictionary."""
        for heading, var_data in iteritems(config_dict):
            self._data[heading] = {}
            
            for var, info in iteritems(var_data):
                if not isinstance(info, dict):
                    continue
                    
                #Fill in type or value if not set
                if 'type' not in info:
                    info['type'] = type(info['value'])
                elif 'value' not in info:
                    info['value'] = self._DEFAULT_VALUES[info['type']]
                info['default'] = info['value']

                self._data[heading][var] = info

    def _update_from_file(self, file_name):
        """Replace all the default values with one from a file."""
            
        with open(file_name, 'r') as f:
            config_lines = [i.strip() for i in f.readlines()]
        for line in config_lines:
            line = line.split('//')[0].strip()
            if not line:
                continue

            if line[0] == '[' and line[-1] == ']':
                header = line[1:-1]
            else:
                variable, value = (i.strip() for i in line.split('='))
                if value:
                    #Make sure it's a valid config item
                    try:
                        self[header][variable] = value
                    except KeyError:
                        pass
                
    def _build_for_file(self):
        """Generate lines for a config file."""
        output = []
        for heading in _get_priority_order(DEFAULTS):
            #Add heading
            output.append('[{}]'.format(heading))

            #Add heading help if set
            try:
                header_info = DEFAULTS[heading]['__info__']
            except KeyError:
                pass
            else:
                for line in header_info.split('\n'):
                    output.append('// {}'.format(line))

            #Add each variable
            for variable in _get_priority_order(DEFAULTS[heading]):
                output.append('{} = {}'.format(variable, DEFAULTS[heading][variable]['value']))
                try:
                    output[-1] += '\t\t// {}'.format(DEFAULTS[heading][variable]['__info__'])
                except KeyError:
                    pass
            output.append('')
        return '\n'.join(output[:-1])

    def load(self, config_file, default_file=CONFIG_DEFAULT):
        """Load first from the default file, then from the main file."""
        if default_file is not None:
            try:
                self._update_from_file(default_file)
            except IOError:
                pass
        try:
            self._update_from_file(config_file)
        except IOError:
            self.is_new = True
        return self

    def save(self, file_name=CONFIG_PATH):
        """Save the config to a file."""
        output = self._build_for_file()
        create_folder(file_name)
        with open(file_name, 'w') as f:
            f.write(output)
        return self


def config_to_dict(conf):
    new_dict = {}
    for header, variables in iteritems(conf):
        new_dict[header] = {}
        for variable, info in iteritems(variables):
            new_dict[header][variable] = info['type'](info['value'])
    return new_dict
            
            
CONFIG = Config(DEFAULTS).load(CONFIG_PATH).save()