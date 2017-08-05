from __future__ import absolute_import
from locale import getdefaultlocale
import time

from core.compatibility import get_items
from core.constants import format_file_path, CONFIG_PATH, DEFAULT_PATH, DEFAULT_LANGUAGE
from core.os import get_resolution


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
                value = value.replace('#', ';').replace('//', ';').split(';', 1)[0]
                
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
        with open(self.file_name, 'w') as f:
            f.write('\n'.join(output))

    def __getitem__(self, item):
        return self.data[item]

#Get the current resolution to set for image generation
try:
    _res_x, _res_y = get_resolution()
except TypeError:
    _res_x = 1920
    _res_y = 1080

try:
    _language = getdefaultlocale()[0]
except ValueError:
    #Fix for a mac error saying unknown locale
    _language = DEFAULT_LANGUAGE
    
_config_defaults = {
    'Main': {
        'UpdatesPerSecond': (60, int, 1, 'It is recommended to leave at 60 even if'
                                         ' you have a higher refresh rate.'),
        'RepeatKeyPress': (0.0, float, 0, 'Record a new key press at this frequency'
                                          ' if a key is being held down (set to 0.0 to disable).'),
        'RepeatClicks': (0.18, float, 0, 'Record a new click at this frequency'
                                         ' if a mouse button is being held down (set to 0.0 to disable).'),
        'Language': (_language, str, 'Choose a language. If the files don\'t exit yet,'
                                     ' {} will be used.'.format(_language, DEFAULT_LANGUAGE))
    },
    'CompressMaps': {
        '__note__': ['Set how often the older tracks should be compressed, and by how much.',
                     'This helps keep the most recent data visibile.'],
        'TrackMaximum': (425000, int, 1),
        'TrackReduction': (1.1, float)
    },
    'Save': {
        'Frequency': (180, int, 10, 'Choose how often to save the file, don\'t set it too low'
                                    ' or the program won\'t be able to keep up.'),
        'MaximumAttemptsNormal': (3, int, 1, 'Maximum number of failed save attempts'
                                             ' before the tracking continues.'),
        'MaximumAttemptsSwitch': (24, int, 1, 'Maximum number of failed save attempts'
                                          ' when switching profile.'
                                          ' If this fails then the latest data will be lost.'),
        'WaitAfterFail': (5, int, 1, 'How many seconds to wait before trying again.')
    },
    'Paths': {
        '__note__': ['You may use environment variables such as %APPDATA% in any paths.'],
        'Data': ('{}\\Data\\'.format(DEFAULT_PATH), str),
        'AppList': ('{}\\AppList.txt'.format(DEFAULT_PATH), str)
        
    },
    'Internet': {
        'Enable': (True, bool),
        'UpdateApplications': (86400, int, 'How often to update the list from the internet. Set to 0 to disable.')
    },
    'Timer': {
        'CheckPrograms': (2, int, 1),
        'CheckResolution': (1, int, 1),
        'ReloadPrograms': (300, int, 1),
        '_ShowQueuedCommands': (20, int),
        '_Ping': (5, int)
    },
    'GenerateImages': {
        '__note__': ['For the best results, make sure the upscale resolution'
                     ' is higher than or equal to the highest recorded resolution.'],
        '_UpscaleResolutionX': (_res_x, int, 1),
        '_UpscaleResolutionY': (_res_y, int, 1),
        'HighPrecision': (False, bool),
        'OutputResolutionX': (_res_x, int, 1),
        'OutputResolutionY': (_res_y, int, 1),
        'AllowedCores': (0, int, 0, 8, 'Number of cores allowed for generating images.'
                                       ' Set to 0 to use all available.'),
        'FileType': ('png', str, (False, 'jpg', 'png'))
    },
    'GenerateHeatmap': {
        'NameFormat': ('{}\\Images\\[FriendlyName] Heatmap ([MouseButtons]) - [ColourProfile]'.format(DEFAULT_PATH), str),
        '_MouseButtonLeft': (True, bool),
        '_MouseButtonMiddle': (True, bool),
        '_MouseButtonRight': (True, bool),
        
        #To get a consistent result -
        #   36 at 2880p, 28 at 2160p, 18 at 1440p, 15 at 1080p, 10 at 720p
        #Roughly that is a factor of 80, so it may be possible to give a consistent multiplier instead
        'GaussianBlurSize': (28, float, 1),
        
        'ExponentialMultiplier': (1.0, float, 0.001, 'Multiply every pixel to the power of this number.'
                                                     ' It can produce better results, but not all the time,'
                                                     ' so it is best left at 1.0 normally.'),
        'ColourProfile': ('Jet', str),
        'MaximumValueMultiplier': (7.5, float, 0.001, 'A lower value pushes more areas to the maximum.',
                                                      ' Change this for each image to get the best heatmap results.'),
        'ForceMaximumValue': (0.0, float, 0, 'Manually set the maximum value to limit the range'
                                             ', which is generally between 0 and 1.'
                                             ' Set to 0.0 for automatic, otherwise use trial and error'
                                             ' to get it right.')
    },
    'GenerateTracks': {
        'NameFormat': ('{}\\Images\\[FriendlyName] Tracks - [ColourProfile]'.format(DEFAULT_PATH), str),
        'ColourProfile': ('WhiteToBlack', str)
    },
    'GenerateKeyboard':{
        'NameFormat': ('{}\\Images\\[FriendlyName] Keyboard Heatmap - [ColourProfile]'.format(DEFAULT_PATH), str),
        'ColourProfile': ('Aqua', str),
        'ExtendedKeyboard': (True, bool, 'Set if the full keyboard should be shown.'),
        'SizeMultiplier': (1.0, float, 0, 'Change the size of everything at once.'),
        'KeySize': (65, int, 0),
        'KeyCornerRadius': (3, int, 0),
        'KeyPadding': (8, int, 0),
        'KeyBorder': (0.6, float, 0),
        'DropShadowX': (1.25, float, 0),
        'DropShadowY': (1.5, float, 0),
        'ImagePadding': (16, int, 0),
        'FontSizeMain': (17, int, 0),
        'FontSizeStats': (13, int, 0),
        'FontHeightOffset': (5, int),
        'FontWidthOffset': (5, int),
        'FontSpacing': (5, int),
        'LinearScale': (False, bool, ('If using linear, it is recommended to use a simple colour map such as'
                                      ' "WhiteTo____".')),
        'LinearExponential': (1.0, float, 0),
        'DataSet': ('time', str, (False, 'time', 'count', 'Set if the colours should be determined by the'
                                                          ' total time the key has been held (time), '
                                                          ' or the number of presses (count).'))
    },
    'SavedSettings': {
        '__note__': ['Anything put here is not for editing.'],
        'AppListUpdate': (0, int, None, int(time.time()))
    },
    'Advanced': {
        'MessageLevel': (1, int, 0, 3, 'Choose how many messages to show.'
                                       ' 0 will show everything, and 3 will show nothing.')
    }
}

_config_order = [
    'Main',
    'Paths',
    'Internet',
    'Save',
    'Timer',
    'CompressMaps',
    'GenerateImages',
    'GenerateTracks',
    'GenerateHeatmap',
    'GenerateKeyboard',
    'Advanced',
    'SavedSettings'
]


CONFIG = SimpleConfig(CONFIG_PATH, _config_defaults, _config_order)
