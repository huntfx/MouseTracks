from functions import SimpleConfig
VERSION = '2.0.0'
       
COLOURS_MAIN = {
    'red': (1.0, 0.0, 0.0),
    'green': (0.0, 1.0, 0.0),
    'blue': (0.0, 0, 1.0),
    'yellow': (1.0, 1.0, 0.0),
    'cyan': (0.0, 1.0, 1.0),
    'magenta': (1.0, 0.0, 1.0),
    'white': (1.0, 1.0, 1.0),
    'grey': (0.5, 0.5, 0.5),
    'gray': (0.5, 0.5, 0.5),
    'black': (0.0, 0.0, 0.0),
    'orange': (1.0, 0.5, 0.0),
    'pink': (1.0, 0.0, 0.5),
    'purple': (0.5, 0.0, 1.0)
}


COLOUR_MODIFIERS = {
    'light': (0.5, 0.5),
    'dark': (0, 0.5)
}


_config_defaults = [
    ('Main', {
        'UpdatesPerSecond': (60, int, 'This is probably best left at 60 even if'
                                      ' you have a higher refresh rate.'),
        'RepeatKeyPress': (0.25, float, 'Record a new key press at this frequency'
                                        ' if a key is being held down (set to 0 to disable).'),
        'RepeatClicks': (0.18, float, 'Record a new click at this frequency'
                                      ' if the mouse is being held down (set to 0 to disable).')
    }),
    ('CompressTracks', {
        '__note__': ['Set how often the older tracks should be compressed, and by how much.',
                     'This stops the tracking image from becoming fully black with extended use.'],
        'Frequency': (7200, int),
        'Multiplier': (1.1, float)
    }),
    ('Timer', {
        'Save': (120, int),
        'CheckPrograms': (2, int),
        'CheckResolution': (1, int),
        'ReloadPrograms': (600, int)
    }),
    ('GenerateImages', {
        '__note__': ['For the best results, make sure the upscale resolution'
                     ' is higher than or equal to the highest recorded resolution.'],
        'UpscaleResolutionX': (3840, int),
        'UpscaleResolutionY': (2160, int),
        'OutputResolutionX': (1920, int),
        'OutputResolutionY': (1080, int)
    }),
    ('GenerateHeatmap', {
        'NameFormat': ('Result\\[FriendlyName] - Heatmap', str, 'Variables: [UResX], [UResY],'
                                                                ' [ResX], [ResY], [ExpMult],'
                                                                ' [GaussianSize], [ColourProfile]'),
        'GaussianBlurSize': (20, int),
        'ExponentialMultiplier': (1.0, float),
        'ColourProfile': ('HeatMap', str),
        'SetMaxRange': (0, int, 'Manually set the highest value.'
                                ' Set to 0 to use auto, otherwise use trial and error'
                                ' to get it right.')
    }),
    ('GenerateTracks', {
        'NameFormat': ('Result\\[FriendlyName] - Tracks', str, 'Variables: [UResX], [UResY],'
                                                               ' [ResX], [ResY], [ColourProfile]'),
        'ColourProfile': ('BlackAndWhite', str)
    })
]

CONFIG = SimpleConfig('config.ini', _config_defaults)
