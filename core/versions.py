from __future__ import absolute_import
import time


VERSION_HISTORY = [
    '-1',
    '2.0',
    '2.0.1',
    '2.0.1b',
    '2.0.2',
    '2.0.3',
    '2.0.4',
    '2.0.5',
    '2.0.5b',
    '2.0.6',
    '2.0.6b',
    '2.0.6c',
    '2.0.7',
    '2.0.8',
    '2.0.9',
    '2.0.9b',
    '2.0.9c',
    '2.0.9d'
]

VERSION = VERSION_HISTORY[-1]


def _get_id(id):
    """Read the ID for upgrading versions.
    If no ID exists, such as if the version may not be finished,
    it'll default to the first ID and not upgrade.
    """
    try:
        return VERSION_HISTORY.index(str(id))
    except ValueError:
        return 0


def upgrade_version(data, update_metadata=True):
    """Files from an older version will be run through this function.

    History:
    2.0: Base script
    2.0.1: Add acceleration tracking
    2.0.1b: Rename acceleration to speed, change tracking method
    2.0.2: Experimenting with combined speed and position tracks
    2.0.3: Separate click maps, record both keys pressed and how long
    2.0.4: Save creation date and rename modified date
    2.0.5: Group maps and add extras for experimenting on
    2.0.5b: Separate tick counts for different maps
    2.0.6: Remove speed and combined maps as they don't look very interesting
    2.0.6b: Record when session started
    2.0.6c: Record key presses per session
    2.0.7: Fixed some incorrect key names
    2.0.8: Store each session start
    2.0.9: Remove invalid track coordinates
    2.0.9b: Matched format of session and total ticks, converted all back to integers
    2.0.9c: Created separate map for clicks this session
    2.0.9d: Remove temporary maps as they were messy, add double clicks to test
    """

    #Make sure version is in history, otherwise set to lowest version
    current_version_id = _get_id(data.get('Version', '-1'))
    current_time = time.time()
        
    if current_version_id < _get_id('2.0'):
        data['Count'] = 0
        data['Tracks'] = {}
        data['Clicks'] = {}
        data['Keys'] = {}
        data['Ticks'] = 0
        data['LastSave'] = current_time
        data['TimesLoaded'] = 0
        data['Version'] = '2.0'
        
    if current_version_id < _get_id('2.0.1'):
        data['Acceleration'] = {}
        
    if current_version_id < _get_id('2.0.1b'):
        del data['Acceleration']
        data['Speed'] = {}
        
    if current_version_id < _get_id('2.0.2'):
        data['Combined'] = {}
        
    if current_version_id < _get_id('2.0.3'):
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
        
    if current_version_id < _get_id('2.0.4'):
        data['Time'] = {'Created': data['LastSave'],
                        'Modified': data['LastSave']}
        del data['LastSave']
        
    if current_version_id < _get_id('2.0.5'):
        data['Maps'] = {'Tracks': data['Tracks'], 'Clicks': data['Clicks'],
                        'Speed': data['Speed'], 'Combined': data['Combined'],
                        'Temp1': {}, 'Temp2': {}, 'Temp3': {}, 'Temp4': {},
                        'Temp5': {}, 'Temp6': {}, 'Temp7': {}, 'Temp8': {}}
        del data['Tracks']
        del data['Clicks']
        del data['Speed']
        del data['Combined']
        
    if current_version_id < _get_id('2.0.5b'):
        data['Ticks']['Current'] = {'Tracks': data['Ticks']['Current'],
                                    'Speed': data['Ticks']['Current']}
                                    
    if current_version_id < _get_id('2.0.6'):
        del data['Maps']['Speed']
        del data['Maps']['Combined']
        del data['Ticks']['Current']['Speed']
        
    if current_version_id < _get_id('2.0.6b'):
        data['Ticks']['Session'] = {'Current': data['Ticks']['Current']['Tracks'],
                                    'Total': data['Ticks']['Total']}
                                    
    if current_version_id < _get_id('2.0.6c'):
        data['Keys'] = {'All': data['Keys'], 'Session': {'Pressed': {}, 'Held': {}}}
        
    if current_version_id < _get_id('2.0.7'):
        changes = {'UNDERSCORE': 'HYPHEN',
                   'MULTIPLY': 'ASTERISK',
                   'AT': 'APOSTROPHE',
                   'HASH': 'NUMBER'}
        for old, new in changes.iteritems():
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
                
    if current_version_id < _get_id('2.0.8'):
        data['SessionStarts'] = []
        
    if current_version_id < _get_id('2.0.9'):
        for resolution in data['Maps']['Tracks']:
            for k in data['Maps']['Tracks'][resolution].keys():
                if not 0 < k[0] < resolution[0] or not 0 < k[1] < resolution[1]:
                    del data['Maps']['Tracks'][resolution][k]
                    
    if current_version_id < _get_id('2.0.9b'):
        data['Ticks']['Tracks'] = int(data['Ticks']['Current']['Tracks'])
        data['Ticks']['Session']['Tracks'] = int(data['Ticks']['Session']['Current'])
        del data['Ticks']['Current']
        del data['Ticks']['Session']['Current']
        for resolution in data['Maps']['Tracks']:
            for k in data['Maps']['Tracks'][resolution]:
                if isinstance(data['Maps']['Tracks'][resolution][k], float):
                    data['Maps']['Tracks'][resolution][k] = int(data['Maps']['Tracks'][resolution][k])
                    
    if current_version_id < _get_id('2.0.9c'):
        data['Maps']['Session'] = {'Clicks': {}}
        
    if current_version_id < _get_id('2.0.9d'):
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
        
    if update_metadata:     
    
        #Only count as new session if updated or last save was over an hour ago
        if (data.get('Version', '-1') != VERSION 
                or not data['SessionStarts'] 
                or current_time - 3600 > data['Time']['Modified']):
            data['Ticks']['Session']['Tracks'] = data['Ticks']['Tracks']
            data['Ticks']['Session']['Total'] = data['Ticks']['Total']
            data['Keys']['Session']['Pressed'] = {}
            data['Keys']['Session']['Held'] = {}
            data['Maps']['Session']['Clicks'] = {}
            data['Maps']['Session']['DoubleClicks'] = {}
            data['TimesLoaded'] += 1
            data['SessionStarts'].append(current_time)
            
        data['Version'] = VERSION
            
    return data
