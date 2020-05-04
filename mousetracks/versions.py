"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Version control for the tracking data
#Handles upgrading older files, as well as separating/joining the data for saving

from __future__ import absolute_import

import time

from .misc import CustomOpen
from .config.settings import CONFIG
from .utils import numpy
from .utils.compatibility import unicode, iteritems


FILE_VERSION = 34

VERSION = '1.0 beta'


class IterateMaps(object):
    """Iterate and process all resolutions for a profile."""
    def __init__(self, maps):
        self.maps = maps

    def _iterate(self, maps, command, extra=None, _legacy=False, _lazy_load_path=None, _resolution=None):
        for key, value in iteritems(maps):

            if isinstance(key, tuple):
                _resolution = key

            #Old format where resolution was separate for each map
            if _legacy and isinstance(key, (str, unicode)):
                self._iterate(value, command, extra, _legacy=_legacy)

            #New format when each resolution contains all the maps
            elif not _legacy and isinstance(value, dict):
                self._iterate(value, command, extra, _legacy=_legacy, _lazy_load_path=_lazy_load_path, _resolution=_resolution)

            #Separate the numpy arrays from the data
            elif command == 'separate':
                array = maps[key]
                maps[key] = len(self._map_list)
                self._map_list.append(array)

            #Rejoin the numpy arrays with the data
            elif command == 'join':
                if _lazy_load_path is None:
                    maps[key] = extra[value]
                else:
                    maps[key] = numpy.LazyLoader(_lazy_load_path, value, resolution=_resolution)

            #Convert dicts to numpy arrays (only used on old files)
            elif command == 'convert' and _legacy:
                width, height = key
                numpy_array = numpy.array((width, height), create=True, dtype='int64')
                for x, y in value:
                    numpy_array[y][x] = value[(x, y)]
                maps[key] = numpy_array

    def separate(self):
        """Separate the numpy maps from the main data, and replace with an integer."""
        self._map_list = []
        self._iterate(self.maps, 'separate')
        return self._map_list

    def join(self, numpy_maps, _legacy=False, _lazy_load_path=None):
        """Merge with the numpy maps again."""
        self._iterate(self.maps, 'join', numpy_maps, _legacy=_legacy, _lazy_load_path=_lazy_load_path)

    def convert(self):
        """Convert the old map dictionaries to numpy arrays."""
        self._iterate(self.maps, 'convert', _legacy=True)


def upgrade_version(data={}, reset_sessions=True, update_metadata=True):
    """Files from an older version will be run through this function.
    It will always be compatible between any two versions.
    """

    #Convert from old versions to new
    try:
        file_version = data['FileVersion']
    except KeyError:
        legacy_history = ['-1', '2.0'] + ['2.0.{}'.format(i) for i in (1, '1b', 2, 3, 4, 5, '5b', 6, '6b',
                                                                       '6c', 7, 8, 9, '9b', '9c', '9d', '9e',
                                                                       10, '10b', '10c', '10d', 11, 12, 13)]
        try:
            file_version = legacy_history.index(str(data['Version']))
        except KeyError:
            file_version = 0
    original_version = file_version

    current_time = time.time()

    #Base format
    if file_version < 1:
        data['Count'] = 0
        data['Tracks'] = {}
        data['Clicks'] = {}
        data['Keys'] = {}
        data['Ticks'] = 0
        data['LastSave'] = current_time
        data['TimesLoaded'] = 0
        data['Version'] = '2.0'

    #Add acceleration tracking
    if file_version < 2:
        data['Acceleration'] = {}

    #Rename acceleration to speed, change tracking method
    if file_version < 3:
        del data['Acceleration']
        data['Speed'] = {}

    #Experimenting with combined speed and position tracks
    if file_version < 4:
        data['Combined'] = {}

    #Separate click maps, record both keys pressed and how long
    if file_version < 5:
        if update_metadata:
            data['Clicks'] = {}
        else:
            for resolution in data['Clicks']:
                data['Clicks'][resolution] = [data['Clicks'][resolution], {}, {}]
        data['Keys'] = {'Pressed': {}, 'Held': {}}
        data['Ticks'] = {'Current': data['Count'],
                         'Total': data['Ticks'],
                         'Recorded': data['Count']}
        del data['Count']

    #Save creation date and rename modified date
    if file_version < 6:
        data['Time'] = {'Created': data['LastSave'],
                        'Modified': data['LastSave']}
        del data['LastSave']

    #Group maps and add extras for experimenting on
    if file_version < 7:
        data['Maps'] = {'Tracks': data['Tracks'], 'Clicks': data['Clicks'],
                        'Speed': data['Speed'], 'Combined': data['Combined'],
                        'Temp1': {}, 'Temp2': {}, 'Temp3': {}, 'Temp4': {},
                        'Temp5': {}, 'Temp6': {}, 'Temp7': {}, 'Temp8': {}}
        del data['Tracks']
        del data['Clicks']
        del data['Speed']
        del data['Combined']

    #Separate tick counts for different maps
    if file_version < 8:
        data['Ticks']['Current'] = {'Tracks': data['Ticks']['Current'],
                                    'Speed': data['Ticks']['Current']}

    #Remove speed and combined maps as they don't look very interesting
    if file_version < 9:
        del data['Maps']['Speed']
        del data['Maps']['Combined']
        del data['Ticks']['Current']['Speed']

    #Record when session started
    if file_version < 10:
        data['Ticks']['Session'] = {'Current': data['Ticks']['Current']['Tracks'],
                                    'Total': data['Ticks']['Total']}

    #Record keystokes per session
    if file_version < 11:
        data['Keys'] = {'All': data['Keys'], 'Session': {'Pressed': {}, 'Held': {}}}

    #Fixed some incorrect key names
    if file_version < 12:
        changes = {'UNDERSCORE': 'HYPHEN',
                   'MULTIPLY': 'ASTERISK',
                   'AT': 'APOSTROPHE',
                   'HASH': 'NUMBER'}
        for old, new in iteritems(changes):
            try:
                data['Keys']['All']['Pressed'][new] = data['Keys']['All']['Pressed'].pop(old)
                data['Keys']['All']['Held'][new] = data['Keys']['All']['Held'].pop(old)
            except KeyError:
                pass
            try:
                data['Keys']['Session']['Pressed'][new] = data['Keys']['Session']['Pressed'].pop(old)
                data['Keys']['Session']['Held'][new] = data['Keys']['Session']['Held'].pop(old)
            except KeyError:
                pass

    #Store each session start
    if file_version < 13:
        data['SessionStarts'] = []

    #Remove invalid track coordinates
    if file_version < 14:
        for resolution, resolution_data in tuple(data['Maps']['Tracks'].items()):
            for k in tuple(resolution_data):
                if not 0 < k[0] < resolution[0] or not 0 < k[1] < resolution[1]:
                    del data['Maps']['Tracks'][resolution][k]

    #Matched format of session and total ticks, converted all back to integers
    if file_version < 15:
        data['Ticks']['Tracks'] = int(data['Ticks']['Current']['Tracks'])
        data['Ticks']['Session']['Tracks'] = int(data['Ticks']['Session']['Current'])
        del data['Ticks']['Current']
        del data['Ticks']['Session']['Current']
        for resolution in data['Maps']['Tracks']:
            for k in data['Maps']['Tracks'][resolution]:
                if isinstance(data['Maps']['Tracks'][resolution][k], float):
                    data['Maps']['Tracks'][resolution][k] = int(data['Maps']['Tracks'][resolution][k])

    #Created separate map for clicks this session
    if file_version < 16:
        data['Maps']['Session'] = {'Clicks': {}}

    #Remove temporary maps as they were messy, add double clicks
    if file_version < 17:
        del data['Maps']['Temp1']
        del data['Maps']['Temp2']
        del data['Maps']['Temp3']
        del data['Maps']['Temp4']
        del data['Maps']['Temp5']
        del data['Maps']['Temp6']
        del data['Maps']['Temp7']
        del data['Maps']['Temp8']
        data['Maps']['DoubleClicks'] = {}
        data['Maps']['Session']['DoubleClicks'] = {}

    #Maintainence to remove invalid resolutions (the last update caused a few)
    if file_version < 18:

        def _test_resolution(aspects, x, y):
            for ax, ay in aspects:
                dx = x / ax
                if not dx % 1 and dx * ay == y:
                    return True
            return False

        aspects = [
            (4, 3),
            (16, 9),
            (16, 10),
            (18, 9),
            (21, 9),
        ]

        #Reverse and check for multi monitor setups
        aspects += [(y, x) for x, y in aspects]
        aspects += [(x * 2, y) for x, y in aspects] + [(x * 3, y) for x, y in aspects] + [(x * 5, y) for x, y in aspects]

        maps = ('Tracks', 'Clicks', 'DoubleClicks')
        for map in maps:
            for resolution in data['Maps'][map].keys():
                if not _test_resolution(aspects, *resolution):
                    del data['Maps'][map][resolution]

    #Rearrange some maps and convert to numpy arrays
    if file_version < 19:

        for maps in (data['Maps'], data['Maps']['Session']):
            maps['Click'] = {'Single': {'Left': {}, 'Middle': {}, 'Right': {}},
                             'Double': {'Left': {}, 'Middle': {}, 'Right': {}}}
            for resolution in maps['Clicks']:
                maps['Click']['Single']['Left'][resolution] = maps['Clicks'][resolution][0]
                maps['Click']['Single']['Middle'][resolution] = maps['Clicks'][resolution][1]
                maps['Click']['Single']['Right'][resolution] = maps['Clicks'][resolution][2]
            del maps['Clicks']
            for resolution in maps['DoubleClicks']:
                maps['Click']['Double']['Left'][resolution] = maps['DoubleClicks'][resolution][0]
                maps['Click']['Double']['Middle'][resolution] = maps['DoubleClicks'][resolution][1]
                maps['Click']['Double']['Right'][resolution] = maps['DoubleClicks'][resolution][2]
            del maps['DoubleClicks']

        IterateMaps(data['Maps']).convert()

    #Reset double click maps for code update
    if file_version < 20:
        data['Maps']['Click']['Double'] = {'Left': {}, 'Middle': {}, 'Right': {}}

    #Track time between key presses and mistakes
    if file_version < 21:
        data['Keys']['All']['Intervals'] = {}
        data['Keys']['Session']['Intervals'] = {}
        data['Keys']['All']['Mistakes'] = {}
        data['Keys']['Session']['Mistakes'] = {}

    #Record more accurate intervals for each keystroke
    if file_version < 22:
        data['Keys']['All']['Intervals'] = {'Total': data['Keys']['All']['Intervals'], 'Individual': {}}
        data['Keys']['Session']['Intervals'] = {'Total': data['Keys']['Session']['Intervals'], 'Individual': {}}

    #Gamepad tracking
    if file_version < 23:
        data['Gamepad'] = {'All': {'Buttons': {'Pressed': {}, 'Held': {}}, 'Axis': {}}}

    #Change resolutions to major keys
    if file_version < 24:
        data['Resolution'] = {}
        resolutions = list(data['Maps']['Tracks'].keys())
        for resolution in resolutions:
            data['Resolution'][resolution] = {}
            data['Resolution'][resolution]['Tracks'] = data['Maps']['Tracks'].pop(resolution)
            data['Resolution'][resolution]['Clicks'] = {}
            try:
                click_s_l = data['Maps']['Click']['Single']['Left'].pop(resolution)
            except KeyError:
                click_s_l = numpy.array(resolution, create=True)
            try:
                click_s_m = data['Maps']['Click']['Single']['Middle'].pop(resolution)
            except KeyError:
                click_s_m = numpy.array(resolution, create=True)
            try:
                click_s_r = data['Maps']['Click']['Single']['Right'].pop(resolution)
            except KeyError:
                click_s_r = numpy.array(resolution, create=True)
            try:
                click_d_l = data['Maps']['Click']['Double']['Left'].pop(resolution)
            except KeyError:
                click_d_l = numpy.array(resolution, create=True)
            try:
                click_d_m = data['Maps']['Click']['Double']['Middle'].pop(resolution)
            except KeyError:
                click_d_m = numpy.array(resolution, create=True)
            try:
                click_d_r = data['Maps']['Click']['Double']['Right'].pop(resolution)
            except KeyError:
                click_d_r = numpy.array(resolution, create=True)
            clicks = {'Single': {'Left': click_s_l,
                                 'Middle': click_s_m,
                                 'Right': click_s_r},
                      'Double': {'Left': click_d_l,
                                 'Middle': click_d_m,
                                 'Right': click_d_r}}
            data['Resolution'][resolution]['Clicks']['All'] = clicks

        del data['Maps']

    #Record history for later animation
    if file_version < 25:
        data['HistoryAnimation'] = {'Tracks': [], 'Clicks': [], 'Keyboard': []}

    #Add version update history and distance travelled
    if file_version < 27:
        data['VersionHistory'] = {}
        data['Distance'] = {'Tracks': 0.0}

    #Add speed maps
    if file_version < 28:
        for resolution in data['Resolution']:
            data['Resolution'][resolution]['Speed'] = numpy.array(resolution, create=True)

    #Reset all intervals due to bug in how they were calculated, and clean mistakes
    if file_version < 29:
        data['Keys']['All']['Intervals'] = {'Total': {}, 'Individual': {}}

        allowed_keys = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890')
        allowed_keys.update(['SPACE', 'COMMA', 'PERIOD', 'BACK'])

        #Build list of invalid keys
        invalid = []
        for first_key, values in iteritems(data['Keys']['All']['Mistakes']):

            if first_key not in allowed_keys:
                invalid.append(first_key)
                continue

            for last_key in values:
                if last_key not in allowed_keys:
                    invalid.append((first_key, last_key))

        #Remove invalid keys
        for key in invalid:
            if isinstance(key, (str, unicode)):
                del data['Keys']['All']['Mistakes'][key]
            else:
                first_key, last_key = key
                del data['Keys']['All']['Mistakes'][first_key][last_key]


    #Add brush stroke maps (speed map only recorded while clicking)
    if file_version < 30:
        for resolution in data['Resolution']:
            data['Resolution'][resolution]['Strokes'] = numpy.array(resolution, create=True)

    #Remove click sessions and add map for separate brush stroke tracking
    if file_version < 31:
        for resolution in data['Resolution']:
            data['Resolution'][resolution]['Clicks'] = data['Resolution'][resolution]['Clicks']['All']
            data['Resolution'][resolution]['StrokesSeparate'] = {'Left': numpy.array(resolution, create=True),
                                                                 'Middle': numpy.array(resolution, create=True),
                                                                 'Right': numpy.array(resolution, create=True)}

    #Add capability for session time tracking
    if file_version < 32:
        data['Sessions'] = [[i, 0, 0] for i in data.pop('SessionStarts')]

    #Convert keys to their actual numbers
    if file_version < 33:
        all_keys = {
            'THUMB1': 5,
            'THUMB2': 6,
            'BACK': 8,
            'TAB': 9,
            'CLEAR': 12,
            'RETURN': 13,
            'PAUSE': 19,
            'CAPSLOCK': 20,
            'ESC': 27,
            'SPACE': 32,
            'PGUP': 33,
            'PGDOWN': 34,
            'END': 35,
            'HOME': 36,
            'LEFT': 37,
            'UP': 38,
            'RIGHT': 39,
            'DOWN': 40,
            'INSERT': 45,
            'DELETE': 46,
            'LWIN': 91,
            'RWIN': 92,
            'MENU': 93,
            'NUM0': 96,
            'NUM1': 97,
            'NUM2': 98,
            'NUM3': 99,
            'NUM4': 100,
            'NUM5': 101,
            'NUM6': 102,
            'NUM7': 103,
            'NUM8': 104,
            'NUM9': 105,
            'ASTERISK': 106,
            'MULTIPLY': 106,
            'ADD': 107,
            'SUBTRACT': 109,
            'DECIMAL': 110,
            'DIVIDE': 111,
            'F1': 112,
            'F2': 113,
            'F3': 114,
            'F4': 115,
            'F5': 116,
            'F6': 117,
            'F7': 118,
            'F8': 119,
            'F9': 120,
            'F10': 121,
            'F11': 122,
            'F12': 123,
            'F13': 124,
            'F14': 125,
            'F15': 126,
            'F16': 127,
            'F17': 128,
            'F18': 129,
            'F19': 130,
            'F20': 131,
            'F21': 132,
            'F22': 133,
            'F23': 134,
            'F24': 135,
            'NUMLOCK': 144,
            'SCROLLLOCK': 145,
            'LSHIFT': 160,
            'RSHIFT': 161,
            'LCTRL': 162,
            'RCTRL': 163,
            'LALT': 164,
            'RALT': 165,
            'COLON': 186,
            'EQUALS': 187,
            'COMMA': 188,
            'HYPHEN': 189,
            'UNDERSCORE': 189,
            'PERIOD': 190,
            'FORWARDSLASH': 191,
            'AT': 192,
            'APOSTROPHE': 192,
            'LBRACKET': 219,
            'BACKSLASH': 220,
            'RBRACKET': 221,
            'HASH': 222,
            'NUMBER': 222,
            'TILDE': 223
        }
        for c in list('ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'):
            all_keys[c] = ord(c)

        #Update held/pressed keys
        for dict_key in ('Held', 'Pressed'):
            for session in ('All', 'Session'):
                separated = data['Keys'][session][dict_key]
                data['Keys'][session][dict_key] = {}

                for key_name, key_int in iteritems(all_keys):
                    try:
                        count = separated[key_name]
                    except KeyError:
                        pass
                    else:
                        data['Keys'][session][dict_key][key_int] = count + data['Keys'][session][dict_key].get(key_int, 0)

        #Update key intervals
        for session in ('All', 'Session'):
            separated = data['Keys'][session]['Intervals']['Individual']
            data['Keys'][session]['Intervals']['Individual'] = {}

            for key_name, interval_group in iteritems(separated):
                if all_keys[key_name] not in data['Keys'][session]['Intervals']['Individual']:
                    data['Keys'][session]['Intervals']['Individual'][all_keys[key_name]] = {}

                for key_name_2, intervals in iteritems(interval_group):
                    try:
                        existing_dict = data['Keys'][session]['Intervals']['Individual'][all_keys[key_name]][all_keys[key_name_2]]
                    except KeyError:
                        data['Keys'][session]['Intervals']['Individual'][all_keys[key_name]][all_keys[key_name_2]] = intervals
                    else:
                        intervals_new = {interval: intervals.get(interval, 0) + existing_dict.get(interval, 0) for interval in set(intervals) | set(existing_dict)}
                        data['Keys'][session]['Intervals']['Individual'][all_keys[key_name]][all_keys[key_name_2]] = intervals_new

        #Update mistakes
        for session in ['All']:
            separated = data['Keys'][session]['Mistakes']
            data['Keys'][session]['Mistakes'] = {}

            for key_name, mistake_group in iteritems(separated):
                if all_keys[key_name] not in data['Keys'][session]['Mistakes']:
                    data['Keys'][session]['Mistakes'][all_keys[key_name]] = {}

                for key_name_2, mistake_count in iteritems(mistake_group):
                    data['Keys'][session]['Mistakes'][all_keys[key_name]][all_keys[key_name_2]] = mistake_count + data['Keys'][session]['Mistakes'][all_keys[key_name]].get(all_keys[key_name_2], 0)

    #Marks the new folder structure, before this will have the pickle bug
    if file_version < 34:
        pass

    version_update = data.get('FileVersion', '0') != FILE_VERSION

    #Track when the updates happen
    if version_update:
        start_version = max(original_version, 27)
        for i in range(start_version, FILE_VERSION+1):
            data['VersionHistory'][i] = current_time

    if update_metadata:
        data['Version'] = VERSION

        #TODO: Auto update file version
        data['FileVersion'] = FILE_VERSION

    #Only count as new session if updated or last save was recent (<60 minutes)
    new_session = reset_sessions and (not data['Sessions'] or current_time - 3600 > data['Time']['Modified'])
    if new_session or version_update and original_version < 27:

        #Remove old session if too short, since it's recreated we can technically just change the time to keep the stats
        if data['Sessions'] and 0 < data['Sessions'][-1][1] < CONFIG['Advanced']['MinSessionTime']:
            data['Sessions'][-1][0] = current_time
        else:
            data['Sessions'].append([current_time, 0, 0])

        data['Ticks']['Session']['Tracks'] = data['Ticks']['Tracks']
        data['Ticks']['Session']['Total'] = data['Ticks']['Total']
        data['Keys']['Session']['Pressed'] = {}
        data['Keys']['Session']['Held'] = {}
        data['Keys']['Session']['Intervals'] = {'Total': {}, 'Individual': {}}
        data['Keys']['Session']['Mistakes'] = {}
        data['Gamepad']['Session'] = {'Buttons': {'Pressed': {}, 'Held': {}}, 'Axis': {}}
        data['TimesLoaded'] += 1

    return data