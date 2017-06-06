from __future__ import absolute_import
from re import sub
from sys import version_info
from os import listdir
import time
import zlib

from core.os import remove_file, rename_file, create_folder, hide_file
from core.versions import VERSION, upgrade_version
from core.constants import DEFAULT_NAME, CONFIG

if version_info.major == 2:
    import cPickle
else:
    import pickle as cPickle

    
DATA_FOLDER = CONFIG['Paths']['Data']
DATA_NAME = '[PROGRAM].data'
DATA_BACKUP_FOLDER = '.backup'
DATA_TEMP_FOLDER = '.temp'


def format_name(name):
    return sub('[^A-Za-z0-9]+', '', name).lower()
    

def format_folder_path(path):
    parts = path.replace('\\', '/').split('/')
    if '.' in parts[-1]:
        del parts[-1]
    return '/'.join(i for i in parts if i)

    
def _get_paths(program_name):

    if program_name is None:
        program_name = DEFAULT_NAME
    elif isinstance(program_name, (list, tuple)):
        program_name = program_name[0]
    name_format = format_name(program_name)
    
    name = DATA_NAME.replace('[PROGRAM]', name_format)
    new_name = '{}/{}'.format(DATA_FOLDER, name)
    backup_folder = '{}/{}'.format(DATA_FOLDER, DATA_BACKUP_FOLDER)
    backup_name = '{}/{}'.format(backup_folder, name)
    temp_folder = '{}/{}'.format(DATA_FOLDER, DATA_TEMP_FOLDER)
    temp_name = '{}/{}'.format(temp_folder, name)
    
    return {'Main': new_name, 'Backup': backup_name, 'Temp': temp_name,
            'BackupFolder': backup_folder, 'TempFolder': temp_folder}
    

def load_program(program_name=None, _update_version=True):

    paths = _get_paths(program_name)
    new_file = False
    
    #Load the main file
    try:
        with open(paths['Main'], 'rb') as f:
            loaded_data = cPickle.loads(zlib.decompress(f.read()))
            
    #Load backup if file is corrupted
    except zlib.error:
        try:
            with open(paths['Backup'], 'rb') as f:
                loaded_data = cPickle.loads(zlib.decompress(f.read()))
                
        except (IOError, zlib.error):
            new_file = True
    
    #Don't load backup if file has been deleted
    except IOError:
        new_file = True
    
    #Create empty data
    if new_file:
        loaded_data = {}
        
    return upgrade_version(loaded_data, update_metadata=_update_version)


def save_program(program_name, data):

    data['Time']['Modified'] = time.time()
    data['Version'] = VERSION
    compressed_data = zlib.compress(cPickle.dumps(data))
    
    paths = _get_paths(program_name)
    
    if create_folder(paths['BackupFolder']):
        hide_file(paths['BackupFolder'])
    if create_folder(paths['TempFolder']):
        hide_file(paths['TempFolder'])
    with open(paths['Temp'], 'wb') as f:
        f.write(compressed_data)
    remove_file(paths['Backup'])
    rename_file(paths['Main'], paths['Backup'])
    if rename_file(paths['Temp'], paths['Main']):
        return True
    else:
        remove_file(paths['Temp'])
        return False

        
def list_files():
    all_files = listdir(DATA_FOLDER)
    extension = DATA_NAME.replace('[PROGRAM]', '')
    return [i.replace(extension, '') for i in all_files if i.endswith(extension)]
