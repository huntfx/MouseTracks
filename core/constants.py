from core.functions import SimpleConfig


DEFAULT_NAME = 'Default'

COLOURS_MAIN = {
    'red': (255, 0, 0),
    'green': (0, 255, 0),
    'blue': (0, 0, 255),
    'yellow': (255, 255, 0),
    'cyan': (0, 255, 255),
    'magenta': (255, 0, 255),
    'white': (255, 255, 255),
    'grey': (127, 127, 127),
    'gray': (127, 127, 127),
    'black': (0, 0, 0),
    'orange': (255, 127, 0),
    'pink': (255, 0, 127),
    'purple': (127, 0, 255)
}

COLOUR_MODIFIERS = {
    'light': (128, 0.5),
    'dark': (0, 0.5)
}

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
        'Frequency': (180, int, 20, 'Choose how often to save the file, don\'t set it too low'
                                          ' or the program won\'t be able to keep up.'),
        'MaximumAttemptsNormal': (3, int, 1, 'Maximum number of failed save attempts'
                                          ' before the tracking continues.'),
        'MaximumAttemptsSwitch': (24, int, 1, 'Maximum number of failed save attempts'
                                          ' when switching profile.'
                                          ' If this fails then the latest data will be lost.'),
        'WaitAfterFail': (5, int, 1, 'How many seconds to wait before trying again.')
    },
    'Paths': {
        'Data': ('Data', str)
    },
    'Timer': {
        'CheckPrograms': (2, int, 1),
        'CheckResolution': (1, int, 1),
        'ReloadPrograms': (300, int, 1)
    },
    'GenerateImages': {
        '__note__': ['For the best results, make sure the upscale resolution'
                     ' is higher than or equal to the highest recorded resolution.'],
        'UpscaleResolutionX': (3840, int, 1),
        'UpscaleResolutionY': (2160, int, 1),
        'OutputResolutionX': (1920, int, 1),
        'OutputResolutionY': (1080, int, 1),
        'FileType': ('png', str)
    },
    'GenerateHeatmap': {
        'NameFormat': ('Result\\[FriendlyName] [MouseButtons] Heatmap - [ColourProfile]', str),
        'MouseButtonLeft': (True, bool),
        'MouseButtonMiddle': (True, bool),
        'MouseButtonRight': (True, bool),
        'GaussianBlurSize': (28, int, 1), #at 5k: 36, 4k: 28, 2k: possibly 17
        'ExponentialMultiplier': (1.0, float, 'Multiply every pixel to the power of this number.'
                                              ' It can produce better results, but not all the time,'
                                              ' so it is best left at 1.0 normally.'),
        'ColourProfile': ('Jet', str),
        'MaximumValueMultiplier': (7.5, float, 'A higher value increases the range of the heatmap.'),
        'ForceMaximumValue': (0, int, 'Manually set the maximum value to limit the range.'
                                      ' Set to 0 for automatic, otherwise use trial and error'
                                      ' to get it right.')
    },
    'GenerateTracks': {
        'NameFormat': ('Result\\[FriendlyName] Tracks - [ColourProfile]', str),
        'ColourProfile': ('WhiteToBlack', str)
    }
}

_config_order = ['Main', 'Paths', 'CompressMaps', 'Save', 'Timer', 'GenerateImages', 'GenerateHeatmap', 'GenerateTracks']

CONFIG = SimpleConfig('config.ini', _config_defaults, _config_order)
