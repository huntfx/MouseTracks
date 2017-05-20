from re import sub
from sys import version_info
import time
import zlib

from core.os import remove_file, rename_file, create_folder, hide_file
from core.versions import VERSION, upgrade_version
from core.constants import DEFAULT_NAME, CONFIG

if version_info.major == 2:
    import cPickle
else:
    import pickle as cPickle

    
DATA_FOLDER = CONFIG.data['Paths']['Data']
DATA_NAME = '[PROGRAM].data'
DATA_BACKUP_FOLDER = '.backup'
DATA_TEMP_FOLDER = '.temp'


def format_folder_path(path):
    parts = path.replace('\\', '/').split('/')
    if '.' in parts[-1]:
        del parts[-1]
    return '/'.join(i for i in parts if i)


def load_program(program_name=None):
    if program_name is None:
        program_name = DEFAULT_NAME
    elif isinstance(program_name, (list, tuple)):
        program_name = program_name[0]
    name_format = sub('[^A-Za-z0-9]+', '', program_name).lower()
    path = CONFIG.data['Paths']['Data']
    try:
        with open('{}/{}.data'.format(path, name_format), 'rb') as f:
            loaded_data = cPickle.loads(zlib.decompress(f.read()))
    except (IOError, zlib.error):
        try:
            with open('{}/{}.data.old'.format(path, name_format), 'rb') as f:
                loaded_data = cPickle.loads(zlib.decompress(f.read()))
        except (IOError, zlib.error):
            return {'Maps': {'Tracks': {}, 'Clicks': {}, 'Speed': {}, 'Combined': {},
                             'Temp1': {}, 'Temp2': {}, 'Temp3': {}, 'Temp4': {},
                             'Temp5': {}, 'Temp6': {}, 'Temp7': {}, 'Temp8': {}},
                    'Keys': {'Pressed': {}, 'Held': {}},
                    'Time': {'Created': time.time(),
                             'Modified': time.time()},
                    'Version': VERSION,
                    'Ticks': {'Current': {'Tracks': 0, 'Speed': 0}, 'Total': 0, 'Recorded': 0},
                    'TimesLoaded': 0}
    else:
        loaded_data['TimesLoaded'] += 1
        return upgrade_version(loaded_data)


def save_program(program_name, data):
    if program_name is None:
        program_name = [DEFAULT_NAME]
    name_format = sub('[^A-Za-z0-9]+', '', program_name[0]).lower()
    data['Time']['Modified'] = time.time()
    data['Version'] = VERSION
    compressed_data = zlib.compress(cPickle.dumps(data))
    
    name = DATA_NAME.replace('[PROGRAM]', name_format)
    new_name = '{}/{}'.format(DATA_FOLDER, name)
    backup_folder = '{}/{}'.format(DATA_FOLDER, DATA_BACKUP_FOLDER)
    backup_name = '{}/{}'.format(backup_folder, name)
    temp_folder = '{}/{}'.format(DATA_FOLDER, DATA_TEMP_FOLDER)
    temp_name = '{}/{}'.format(temp_folder, name)
    
    if create_folder(backup_folder):
        hide_file(backup_folder)
    if create_folder(temp_folder):
        hide_file(temp_folder)
    with open(temp_name, 'wb') as f:
        f.write(compressed_data)
    remove_file(backup_name)
    rename_file(new_name, backup_name)
    if rename_file(temp_name, new_name):
        return True
    else:
        remove_file(temp_name)
        return False
