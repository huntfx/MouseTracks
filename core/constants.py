from functions import SimpleConfig
VERSION = 2.0

HEATMAP = [
    (0, 0, 0), (0, 0, 128), (0, 0, 255), (0, 64, 255),
    (0, 128, 255), (0, 192, 255), (64, 255, 192),
    (128, 255, 128), (192, 255, 64), (255, 255, 0),
    (255, 128, 0), (255, 64, 0), (255, 0, 0)
]

_config_defaults = [
    ('Main', {
        'UpdatesPerSecond': (60, int, 'This is probably best left at 60 even if'
                                      ' you have a higher refresh rate.'),
        'RepeatKeyPress': (0.25, float, 'Record a new key press at this frequency'
                                        ' if a key is being held down (set to 0 to disable).')
    }),
    ('CompressTracks', {
        '__note__': ['Set how often the older tracks should be compressed, and by how much.',
                     'This stops the tracking image from becoming fully black with extended use.'],
        'Frequency': (7200, int),
        'Multiplier': (1.1, float)
    }),
    ('Timer', {
        'Save': (30, int),
        'CheckPrograms': (2, int),
        'CheckScreen': (3, int),
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
        'GaussianBlurSize': (25, int),
        'ExponentialMultiplier': (0.5, float),
        'ColourProfile': ('HeatMap', str),
        'TrimEdges': (20, int, 'Removes edges so that frequently clicked things like the close'
                              ' button won\'t affect the rest of the results.')
    }),
    ('GenerateTracks', {
        'ColourProfile': ('BlackAndWhite', str)
    })
]

CONFIG = SimpleConfig('config.ini', _config_defaults)

if __name__ == '__main__':
    CONFIG.save()
