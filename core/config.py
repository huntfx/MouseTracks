"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import time
from locale import getdefaultlocale

from core.base import format_file_path
from core.compatibility import get_items
from core.constants import CONFIG_PATH, DEFAULT_PATH, DEFAULT_LANGUAGE, MAX_INT, APP_LIST_FILE
from core.os import get_resolution, create_folder, OS_DEBUG


class SimpleConfig(object):
    def __init__(self, file_name, default_data, group_order=None):
        self.file_name = format_file_path(file_name)
        self._default_data = default_data
        self.default_data = {}
        self.order = list(group_order) if group_order is not None else []
        for group, data in get_items(self._default_data):
            self.default_data[group] = self._default_data[group]
        self.load()
    
    def load(self):
        """Open config file and validate values.
        
        Allowed formats:
            value, type, [comment] 
            value, int/float, [min, [max]], [comment]
            value, str, [is case sensitive, item1, item2...], [comment]
        """
        try:
            with open(self.file_name, 'r') as f:
                config_lines = [i.strip() for i in f.readlines()]
        except IOError:
            config_lines = []
        
        #Read user values
        config_data = {}
        for line in config_lines:
            if not line:
                continue
            
            #Start new heading
            if line.startswith('['):
                current_group = line[1:].split(']', 1)[0]
                config_data[current_group] = {}
            
            #Skip comment
            elif line[0] in (';', '/', '#'):
                pass
            
            #Process value
            else:
                name, value = [i.strip() for i in line.split('=', 1)]
                value = value.replace('#', ';').replace('//', ';').split(';', 1)[0].strip()
                
                #Compare value in file to default settings
                try:
                    default_value, default_type = self.default_data[current_group][name][:2]
                except KeyError:
                    pass
                else:
                    #Process differently depending on variable type
                    if default_type == bool:
                        if value.lower() in ('0', 'false'):
                            value = False
                        elif value.lower() in ('1', 'true'):
                            value = True
                        else:
                            value = default_value
                            
                    elif default_type == int:
                        if '.' in value:
                            value = value.split('.')[0]
                        try:
                            value = int(value)
                        except ValueError:
                            value = default_value
                            
                    elif default_type == str:
                        value = str(value).rstrip()
                        
                    else:
                        value = default_type(value)
                    
                    #Handle min/max values
                    if default_type in (int, float):
                        no_text = [i for i in self.default_data[current_group][name] if not isinstance(i, str)]
                        if len(no_text) >= 3:
                            if no_text[2] is not None and no_text[2] > value:
                                value = no_text[2]
                            elif len(no_text) >= 4:
                                if no_text[3] is not None and no_text[3] < value:
                                    value = no_text[3]
                    if default_type == str:
                        if len(self.default_data[current_group][name]) >= 3:
                            if isinstance(self.default_data[current_group][name][2], tuple):
                                allowed_values = list(self.default_data[current_group][name][2])
                                case_sensitive = allowed_values.pop(0)
                                if case_sensitive:
                                    if not any(value == i for i in allowed_values):
                                        value = default_value
                                else:
                                    value_lower = value.lower()
                                    if not any(value_lower == i.lower() for i in allowed_values):
                                        value = default_value
                            
                config_data[current_group][name] = value
        
        #Add any remaining values that weren't in the file
        for group, variables in get_items(self.default_data):
            for variable, defaults in get_items(variables):
                try:
                    config_data[group][variable]
                except KeyError:
                    try:
                        config_data[group][variable] = defaults[0]
                    except KeyError:
                        config_data[group] = {variable: defaults[0]}

        self.data = config_data        
        return self.data

    def save(self):
        """Save config with currently loaded values."""
        extra_items = list(set(self._default_data.keys()) - set(self.order))
        
        output = []
        for group in self.order + extra_items:
            variables = self._default_data[group]
            if output:
                output.append('')
            output.append('[{}]'.format(group))
            if '__note__' in variables:
                for note in variables.pop('__note__'):
                    output.append('// {}'.format(note))
            for variable in sorted(variables.keys()):
                if variable.startswith('_'):
                    continue
                defaults = variables[variable]
                try:
                    value = self.data[group][variable]
                except KeyError:
                    value = defaults[0]
                output.append('{} = {}'.format(variable, value))
                try:
                    if isinstance(defaults[-1], str) and defaults[-1]:
                        output[-1] += '    // {}'.format(defaults[-1])
                except IndexError:
                    pass
        try:
            with open(self.file_name, 'w') as f:
                f.write('\n'.join(output))
        except IOError:
            create_folder(self.file_name)
            with open(self.file_name, 'w') as f:
                f.write('\n'.join(output))
            
    def __getitem__(self, item):
        return self.data[item]

        
def get_config_default(heading, value):
    return _config_defaults[heading][value][0]
        
        
try:
    _language = getdefaultlocale()[0]
except ValueError:
    #Fix for a mac error saying unknown locale
    _language = DEFAULT_LANGUAGE

_save_freq = 20 if OS_DEBUG else 180
    
_config_defaults = {
    'Main': {
        'Language': (_language, str, 'Choose a language. If there is any issue or the files don\'t exit yet,'
                                     ' {} will be used.'.format(_language, DEFAULT_LANGUAGE)),
        'HistoryLength': (7200, int, 0, 'How many seconds to store of the track history.',
                                     ' Each hour increases the file size by roughly 1.5mb.')
    },
    'Save': {
        'Frequency': (180, int, 0, 'Choose how often to save the file, don\'t set it too low'
                                    ' or the program won\'t be able to keep up.'
                                    ' Set to 0 to disable.'),
        'MaximumAttemptsNormal': (3, int, 1, 'Maximum number of failed save attempts'
                                             ' before the tracking continues.'),
        'MaximumAttemptsSwitch': (24, int, 1, 'Maximum number of failed save attempts'
                                          ' when switching profile.'
                                          ' If this fails then the latest data will be lost.'),
        'WaitAfterFail': (5, int, 1, 'How many seconds to wait before trying again.')
    },
    'Paths': {
        '__note__': ['You may use environment variables such as %APPDATA%.'],
        'Data': ('{}\\Data\\'.format(DEFAULT_PATH), str),
        'AppList': ('{}\\{}'.format(DEFAULT_PATH, APP_LIST_FILE), str),
        'Images': ('{}\\Images\\[Name]'.format(DEFAULT_PATH), str, 'Default place to save images. [Name] is replaced by the name of the application.')
        
    },
    'Internet': {
        'Enable': (True, bool),
        'UpdateApplications': (86400, int, 0, 'How often (in minutes) to update the list from the internet. Set to 0 to disable.')
    },
    'GenerateImages': {
        '_UpscaleResolutionX': (0, int),
        '_UpscaleResolutionY': (0, int),
        '_OutputResolutionX': (0, int),
        '_OutputResolutionY': (0, int),
        'HighPrecision': (False, bool, 'Enable this for higher quality images'
                                       ' that take longer to generate.'),
        'AutomaticResolution': (True, bool, 'If disabled, OutputResolutionX/Y must be set.'),
        'OutputResolutionX': (0, int),
        'OutputResolutionY': (0, int),
        'FileType': ('png', str, (False, 'jpg', 'png'), 'Choose if you want jpg (smaller size) or png (higher quality) image.'),
        'OpenOnFinish': (True, bool, 'Enable to open the image folder after generating.')
    },
    'GenerateHeatmap': {
        'FileName': ('[[RunningTimeSeconds]]Clicks ([MouseButton]) - [ColourProfile]', str),
        '_MouseButtonLeft': (True, bool),
        '_MouseButtonMiddle': (True, bool),
        '_MouseButtonRight': (True, bool),
        '_GaussianBlurBase': (0.0125, float, 0),
        'GaussianBlurMultiplier': (1.0, float, 0, 'Change the size multiplier of the gaussian blur.'
                                                  ' Smaller values are less smooth but show more detail.'),
        'ColourProfile': ('Jet', str)
    },
    'GenerateTracks': {
        'FileName': ('[[RunningTimeSeconds]]Tracks - [ColourProfile] [HighPrecision]', str),
        'ColourProfile': ('Citrus', str)
    },
    'GenerateKeyboard':{
        'FileName': ('[[RunningTimeSeconds]]Keyboard - [ColourProfile] ([DataSet])', str),
        'ColourProfile': ('Aqua', str),
        'ExtendedKeyboard': (True, bool, 'If the full keyboard should be shown, or just the main section.'),
        'SizeMultiplier': (1.0, float, 0, 'Change the size of everything at once.'),
        'LinearMapping': (False, bool, 'Set if a linear mapping for colours should be used.'),
        'LinearPower': (1.0, float, 0, 'Set the exponential to raise the linear values to.'),
        'DataSet': ('time', str, (False, 'time', 'press'), 'Set if the colours should be determined by the'
                                                          ' total time the key has been held (time),'
                                                          ' or the number of presses (press).')
    },
    'GenerateCSV':{
        '__note__': ['This is for anyone who may want to use the recorded data in their own projects.'],
        'FileNameTracks': ('[[RunningTimeSeconds]] Tracks ([Width], [Height])', str),
        'FileNameClicks': ('[[RunningTimeSeconds]] Clicks ([Width], [Height]) [MouseButton]', str),
        'FileNameKeyboard': ('[[RunningTimeSeconds]] Keyboard', str),
        'MinimumPoints': (50, int, 0, 'Files will not be generated for any resolutions that have fewer points than this recorded.'),
        '_GenerateTracks': (True, bool),
        '_GenerateClicks': (True, bool),
        '_GenerateKeyboard': (True, bool)
    },
    'SavedSettings': {
        '__note__': ['Anything put here is not for editing.'],
        'AppListUpdate': (0, int, None, int(time.time()))
    },
    'Advanced': {
        'MessageLevel': (int(not OS_DEBUG), int, 0, 3, 'Choose the level of messages to show.'
                                                   ' 0 will show everything, and 3 will show nothing.'),
        'HeatmapRangeClipping': (0.005, float, 0, 1, 'Lower the highest value when generating a heatmap.'),
        'CompressTrackMax': (425000, int, 0, MAX_INT, 'Maximum number of of ticks before compression happens.'
                                                      ' Set to 0 to disable.'),
        'CompressTrackAmount': (1.1, float, 1.001, 'How much to divide each pixel by when compression happens.'),
        'CheckResolution': (60, int, 0, 'How many ticks to wait between checking the resolution.'),
        'CheckRunningApplications': (60, int, 0, 'How many ticks to wait between checking if something is running.'),
        'ReloadApplicationList': (18000, int, 0, 'How many ticks to wait before reloading {}.'.format(APP_LIST_FILE)),
        'ShowQueuedCommands': (1200, int, 'How many ticks to wait before showing the number of commands waiting to be processed.'),
        'RepeatKeyPress': (0, int, 0, 'How many ticks to wait before recording a new key press'
                                          ' if a key is being held down (set to 0 to disable).'),
        'RepeatClicks': (14, int, 0, 'How many ticks to wait before recording a click'
                                         ' if a mouse button is being held down (set to 0 to disable).'),
        'RepeatButtonPress': (0, int, 0, 'How many ticks to wait before recording a new gamepad button press'
                                         ' if a button is being held down (set to 0 to disable).'),
        'KeyboardKeySize': (65.0, float, 0),
        'KeyboardKeyCornerRadius': (3.0, float, 0),
        'KeyboardKeyPadding': (8.0, float, 0),
        'KeyboardKeyBorder': (0.6, float, 0),
        'KeyboardDropShadowX': (1.25, float, 0),
        'KeyboardDropShadowY': (1.5, float, 0),
        'KeyboardImagePadding': (16.0, float, 0),
        'KeyboardFontSizeMain': (17.0, float, 0),
        'KeyboardFontSizeStats': (13.0, float, 0),
        'KeyboardFontHeightOffset': (5.0, float),
        'KeyboardFontWidthOffset': (5.0, float),
        'KeyboardFontSpacing': (5.0, float),
        'HistoryCheck': (1200, int, 0, 'How many ticks to wait before checking the history length and trimming if needed.'),
        'RunAsAdministrator': (True, bool, 'This fixes some issues with keyboard tracking.'),
        'RefreshGamepads': (600, int, 1, 'How many ticks to wait before refreshing the list of connected gamepads.')
    }
}

_config_order = [
    'Main',
    'Paths',
    'Internet',
    'Save',
    'GenerateImages',
    'GenerateTracks',
    'GenerateHeatmap',
    'GenerateKeyboard',
    'GenerateCSV',
    'Advanced',
    'SavedSettings'
]


CONFIG = SimpleConfig(CONFIG_PATH, _config_defaults, _config_order)