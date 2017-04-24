'https://www.reddit.com/r/discordapp/comments/3plprj/games_exe_list_post_games_you_want_to_be_added/'
'https://hastebin.com/catuyoguxi.apache'
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
        'UpdatesPerSecond': (60, int)
    }),
    ('Frequency', {
        'Save': (30, int),
        'CheckPrograms': (2, int),
        'CheckScreen': (3, int),
        'ReloadPrograms': (600, int)
    }),
    ('GenerateImages', {
        '__note__': ['For the best results, make sure the upscale resolution'
                     ' is higher than or equal to the highest recorded resolution'],
        'UpscaleResolutionX': (3840, int),
        'UpscaleResolutionY': (2160, int),
        'OutputResolutionX': (1920, int),
        'OutputResolutionY': (1080, int)
    }),
    ('HeatMap', {
        'GaussianBlurSize': (32, int),
        'ExponentialMultiplier': (0.5, float),
        'ColourProfile': ('HeatMap', str)
    }),
    ('Tracks', {
        'ColourProfile': ('BlackAndWhite', str)
    })
]

config = SimpleConfig('../config.ini', _config_defaults)

if __name__ == '__main__':
    config.save()
