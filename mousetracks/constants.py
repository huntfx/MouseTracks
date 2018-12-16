"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Define important variables that don't depend on other imports

UPDATES_PER_SECOND = 60

DEFAULT_NAME = 'Default'

DEFAULT_PATH = '%DOCUMENTS%\\Mouse Tracks'

APP_LIST_FILE = 'AppList.txt'

APP_LIST_URL = 'https://raw.githubusercontent.com/Peter92/MouseTracks/master/config/AppList.txt'

DEFAULT_LANGUAGE = 'en_GB'

MAX_INT = pow(2, 63) - 1

TRACKING_DISABLE = '<disable>'

TRACKING_IGNORE = '<ignore>'

TRACKING_WILDCARD = '<*>'

KEY_STATS = set(ord(i) for i in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890')
KEY_STATS.update([8, 32, 188, 190]) #backspace, space, comma, period