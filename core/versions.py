"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import time

import core.numpy as numpy
from core.compatibility import get_items, unicode


FILE_VERSION = 26

VERSION = '1.0 beta'


class IterateMaps(object):
    def __init__(self, maps):
        self.maps = maps
        
    def _iterate(self, maps, command, extra=None, _legacy=False):            
        for key, value in get_items(maps):
            
            #Old format where resolution was separate for each map
            if _legacy and isinstance(key, (str, unicode)):
                self._iterate(value, command, extra, _legacy=_legacy)
            
            #New format when each resolution contains all the maps
            elif not _legacy and isinstance(value, dict):
                self._iterate(value, command, extra, _legacy=_legacy)

            #Separate the numpy arrays from the data
            elif command == 'separate':
                array = maps[key]
                maps[key] = len(self._map_list)
                self._map_list.append(array)
            
            #Rejoin the numpy arrays with the data
            elif command == 'join':
                maps[key] = extra[value]
            
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

    def join(self, numpy_maps, _legacy=False):
        """Merge with the numpy maps again."""
        self._iterate(self.maps, 'join', numpy_maps, _legacy=_legacy)
    
    def convert(self):
        """Convert the old map dictionaries to numpy arrays."""
        self._iterate(self.maps, 'convert', _legacy=True)
        
        
def _get_id(id):
    """Read the ID for upgrading versions.
    If no ID exists, such as if the version may not be finished,
    it'll default to the first ID and not upgrade.
    """
    try:
        return VERSION_HISTORY.index(str(id))
    except ValueError:
        return 0


def upgrade_version(data={}, update_metadata=True):
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
            file_version = legacy_history.index(data['Version'])
        except KeyError:
            file_version = 0
            
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
        for old, new in get_items(changes):
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
        for resolution in data['Maps']['Tracks']:
            for k in data['Maps']['Tracks'][resolution].keys():
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
        resolutions = data['Maps']['Tracks'].keys()
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
    
    if update_metadata:     
    
        #Only count as new session if updated or last save was over an hour ago
        if (data.get('FileVersion', '0') != FILE_VERSION or not data['SessionStarts'] or current_time - 3600 > data['Time']['Modified']):
            data['Ticks']['Session']['Tracks'] = data['Ticks']['Tracks']
            data['Ticks']['Session']['Total'] = data['Ticks']['Total']
            data['Keys']['Session']['Pressed'] = {}
            data['Keys']['Session']['Held'] = {}
            data['Keys']['Session']['Intervals'] = {'Total': {}, 'Individual': {}}
            data['Keys']['Session']['Mistakes'] = {}
            
            #Empty session arrays
            for resolution, values in get_items(data['Resolution']):
                if 'Session' not in values['Clicks']:
                    values['Clicks']['Session'] = {'Single': {'Left': numpy.array(resolution, create=True),
                                                              'Middle': numpy.array(resolution, create=True),
                                                              'Right': numpy.array(resolution, create=True)},
                                                   'Double': {'Left': numpy.array(resolution, create=True),
                                                              'Middle': numpy.array(resolution, create=True),
                                                              'Right': numpy.array(resolution, create=True)}}
                else:
                    try:
                        values['Clicks']['Session']['Single']['Left'] = numpy.fill(values['Clicks']['Session']['Single']['Left'], 0)
                    except AttributeError:
                        values['Clicks']['Session']['Single']['Left'] = numpy.array(resolution, create=True)
                    try:
                        values['Clicks']['Session']['Single']['Middle'] = numpy.fill(values['Clicks']['Session']['Single']['Middle'], 0)
                    except AttributeError:
                        values['Clicks']['Session']['Single']['Middle'] = numpy.array(resolution, create=True)
                    try:
                        values['Clicks']['Session']['Single']['Right'] = numpy.fill(values['Clicks']['Session']['Single']['Right'], 0)
                    except AttributeError:
                        values['Clicks']['Session']['Single']['Right'] = numpy.array(resolution, create=True)
                    try:
                        values['Clicks']['Session']['Double']['Left'] = numpy.fill(values['Clicks']['Session']['Double']['Left'], 0)
                    except AttributeError:
                        values['Clicks']['Session']['Double']['Left'] = numpy.array(resolution, create=True)
                    try:
                        values['Clicks']['Session']['Double']['Middle'] = numpy.fill(values['Clicks']['Session']['Double']['Middle'], 0)
                    except AttributeError:
                        values['Clicks']['Session']['Double']['Middle'] = numpy.array(resolution, create=True)
                    try:
                        values['Clicks']['Session']['Double']['Right'] = numpy.fill(values['Clicks']['Session']['Double']['Right'], 0)
                    except AttributeError:
                        values['Clicks']['Session']['Double']['Right'] = numpy.array(resolution, create=True)
            
            data['Gamepad']['Session'] = {'Buttons': {'Pressed': {}, 'Held': {}}, 'Axis': {}}
            data['TimesLoaded'] += 1
            data['SessionStarts'].append(current_time)
            
        data['Version'] = VERSION
        data['FileVersion'] = FILE_VERSION
        
    return data