from __future__ import absolute_import
from re import sub
from operator import itemgetter
import time
import zlib
import os

from core.config import CONFIG
from core.compatibility import PYTHON_VERSION, get_items
from core.constants import DEFAULT_NAME, format_file_path
from core.os import remove_file, rename_file, create_folder, hide_file, get_modified_time, list_directory
from core.versions import VERSION, upgrade_version

if PYTHON_VERSION < 3:
    import cPickle
else:
    import pickle as cPickle


DATA_FOLDER = format_file_path(CONFIG['Paths']['Data'])

DATA_EXTENSION = '.data'

DATA_NAME = '[PROGRAM]' + DATA_EXTENSION

DATA_BACKUP_FOLDER = '.backup'

DATA_TEMP_FOLDER = '.temp'

DATA_CORRUPT_FOLDER = '.corrupted'

DATA_SAVED_FOLDER = 'Saved'


def format_name(name):
    """Remove any invalid characters for file name."""
    return sub('[^A-Za-z0-9]+', '', name).lower()

    
def _get_paths(program_name):
    """Create file paths from the global variables."""
    if program_name is None:
        program_name = DEFAULT_NAME
    elif isinstance(program_name, (list, tuple)):
        program_name = program_name[0]
    name_format = format_name(program_name)
    
    name = '{}'.format(DATA_NAME.replace('[PROGRAM]', name_format))
    new_name = '{}/{}'.format(DATA_FOLDER, name)
    backup_folder = '{}/{}'.format(DATA_FOLDER, DATA_BACKUP_FOLDER)
    backup_name = '{}/{}'.format(backup_folder, name)
    temp_folder = '{}/{}'.format(DATA_FOLDER, DATA_TEMP_FOLDER)
    temp_name = '{}/{}'.format(temp_folder, name)
    corrupted_folder = '{}/{}'.format(DATA_FOLDER, DATA_CORRUPT_FOLDER)
    corrupted_name = '{}/{}'.format(corrupted_folder, name)
    
    return {'Main': new_name, 'Backup': backup_name, 'Temp': temp_name, 'Corrupted': corrupted_name,
            'BackupFolder': backup_folder, 'TempFolder': temp_folder, 'CorruptedFolder': corrupted_folder}


def prepare_file(data):
    """Prepare data for saving."""
    data['Time']['Modified'] = time.time()
    data['Version'] = VERSION
    return zlib.compress(cPickle.dumps(data, min(cPickle.HIGHEST_PROTOCOL, 2)))


def decode_file(data):
    """Read compressed data."""
    return cPickle.loads(zlib.decompress(data))
    

def load_program(program_name=None, _update_version=True, _metadata_only=False):
    """Read a profile (or create new one) and run it through the update."""
    paths = _get_paths(program_name)
    new_file = False
    
    if _metadata_only:
        return {'Modified': get_modified_time(paths['Main'])}
    
    #Load the main file
    try:
        with open(paths['Main'], 'rb') as f:
            loaded_data = decode_file(f.read())
            
    #Load backup if file is corrupted
    except (zlib.error, ValueError):
        try:
            with open(paths['Backup'], 'rb') as f:
                loaded_data = decode_file(f.read())
                
        except (IOError, zlib.error, ValueError):
            new_file = True
            
            #Move corrupt file into a folder instead of just silently delete
            if create_folder(paths['CorruptedFolder']):
                hide_file(paths['CorruptedFolder'])
            rename_file(paths['Main'], '{}.{}'.format(paths['Corrupted'], int(time.time())))
    
    #Don't load backup if file has been deleted
    except IOError:
        new_file = True
    
    #Create empty data
    if new_file:
        loaded_data = {}
        
    return upgrade_version(loaded_data, update_metadata=_update_version)
    

def save_program(program_name, data, compress=True):
    """Handle the safe saving of profiles.
    
    Instead of overwriting, it will save as a temprary file and attempt to rename.
    At any point in time there are two copies of the save.
    """
    if compress:
        compressed_data = prepare_file(data)
    else:
        compressed_data = data
    
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

        
def list_data_files():
    """List the name of every saved profile in the data folder.
    The extension is checked, but removed in the output list.
    """
    all_files = list_directory(DATA_FOLDER)
    if all_files is None:
        return []
    date_modified = {f: get_modified_time(os.path.join(DATA_FOLDER, f)) for f in all_files}
    date_sort = sorted(get_items(date_modified), key=itemgetter(1))
    return [k.replace(DATA_EXTENSION, '') for k, v in date_sort if k.endswith(DATA_EXTENSION)][::-1]
