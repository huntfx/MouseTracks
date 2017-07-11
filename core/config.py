from __future__ import absolute_import

from core.basic import get_items, format_file_path
from core.constants import CONFIG_PATH, DEFAULT_PATH
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
        """Open config file and validate values."""
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
            if line.startswith('['):
                current_group = line[1:].split(']', 1)[0]
                config_data[current_group] = {}
            elif line[0] in (';', '/', '#'):
                pass
            else:
                name, value = [i.strip() for i in line.split('=')]
                value = value.replace('#', ';').replace('//', ';').split(';', 1)[0]
                try:
                    default_value, default_type = self.default_data[current_group][name][:2]
                except KeyError:
                    pass
                else:
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
                
                config_data[current_group][name] = value
        
        #Add any remaining default values
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

_config_defaults = {
    'Main': {
        'UpdatesPerSecond': (60, int, 1, 'It is recommended to leave at 60 even if'
                                         ' you have a higher refresh rate.'),
        'RepeatKeyPress': (0.0, float, 0, 'Record a new key press at this frequency'
                                          ' if a key is being held down (set to 0.0 to disable).'),
        'RepeatClicks': (0.18, float, 0, 'Record a new click at this frequency'
                                         ' if a mouse button is being held down (set to 0.0 to disable).')
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
        'UpscaleResolutionX': (_res_x * 2, int, 1),
        'UpscaleResolutionY': (_res_y * 2, int, 1),
        'OutputResolutionX': (_res_x, int, 1),
        'OutputResolutionY': (_res_y, int, 1),
        'FileType': ('png', str)
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
    'SavedSettings': {
        'AppListUpdate': (0, int)
    },
    'Advanced': {
        'MessageLevel': (1, int, 0, 2)
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
    'GenerateHeatmap',
    'GenerateTracks',
    'Advanced',
    'SavedSettings'
]


CONFIG = SimpleConfig(CONFIG_PATH, _config_defaults, _config_order)
