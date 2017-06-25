from core.functions import SimpleConfig


DEFAULT_NAME = 'Default'

COLOURS_MAIN = {
    'red': (255, 0, 0, 255),
    'green': (0, 255, 0, 255),
    'blue': (0, 0, 255, 255),
    'yellow': (255, 255, 0, 255),
    'cyan': (0, 255, 255, 255),
    'magenta': (255, 0, 255, 255),
    'white': (255, 255, 255, 255),
    'grey': (127, 127, 127, 255),
    'gray': (127, 127, 127, 255),
    'black': (0, 0, 0, 255),
    'orange': (255, 127, 0, 255),
    'pink': (255, 0, 127, 255),
    'purple': (127, 0, 255, 255)
}

COLOUR_MODIFIERS = {
    #name: (add_base, multiplier, alpha_multiplier)
    'light': (128, 0.5, 1.0),
    'dark': (0, 0.5, 1.0),
    'transparent': (0, 1.0, 0.0),
    'translucent': (0, 1.0, 0.5),
    'opaque': (0, 1.0, 2.0)
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
        '__note__': ['You may use environment variables such as %APPDATA% in any paths.'],
        'Data': ('%DOCUMENTS%\\Mouse Tracks\Data', str)
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
        'NameFormat': ('%DOCUMENTS%\\Mouse Tracks\\Images\\[FriendlyName] Heatmap ([MouseButtons]) - [ColourProfile]', str),
        'MouseButtonLeft': (True, bool),
        'MouseButtonMiddle': (True, bool),
        'MouseButtonRight': (True, bool),
        
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
        'NameFormat': ('%DOCUMENTS%\\Mouse Tracks\\Images\\[FriendlyName] Tracks - [ColourProfile]', str),
        'ColourProfile': ('WhiteToBlack', str)
    }
}

_config_order = ['Main', 'Paths', 'CompressMaps', 'Save', 'Timer', 'GenerateImages', 'GenerateHeatmap', 'GenerateTracks']

CONFIG = SimpleConfig('config.ini', _config_defaults, _config_order)

PROGRAM_LIST_URL = 'https://raw.githubusercontent.com/Peter92/MouseTrack/master/Program%20List.txt'
