from __future__ import absolute_import
from operator import itemgetter
from re import sub
from cStringIO import StringIO
import time
import zlib
import os
import zipfile

from core.config import CONFIG
from core.compatibility import PYTHON_VERSION, get_items
from core.constants import DEFAULT_NAME, format_file_path
from core.os import remove_file, rename_file, create_folder, hide_file, get_modified_time, list_directory
from core.versions import VERSION, upgrade_version, IterateMaps
import core.numpy as numpy

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

PICKLE_PROTOCOL = min(cPickle.HIGHEST_PROTOCOL, 2)


def format_name(name, extra_chars=''):
    """Remove any invalid characters for file name."""
    return sub('[^A-Za-z0-9{}]+'.format(extra_chars), '', name).lower()


def get_data_filename(name):
    """Get file name of data file."""
    return DATA_NAME.replace('[PROGRAM]', format_name(name))
    
    
def _get_paths(program_name):
    """Create file paths from the global variables."""
    if program_name is None:
        program_name = DEFAULT_NAME
    elif isinstance(program_name, (list, tuple)):
        program_name = program_name[0]
    
    name = get_data_filename(program_name)
    new_name = '{}/{}'.format(DATA_FOLDER, name)
    backup_folder = '{}/{}'.format(DATA_FOLDER, DATA_BACKUP_FOLDER)
    backup_name = '{}/{}'.format(backup_folder, name)
    temp_folder = '{}/{}'.format(DATA_FOLDER, DATA_TEMP_FOLDER)
    temp_name = '{}/{}'.format(temp_folder, name)
    corrupted_folder = '{}/{}'.format(DATA_FOLDER, DATA_CORRUPT_FOLDER)
    corrupted_name = '{}/{}'.format(corrupted_folder, name)
    
    return {'Main': new_name, 'Backup': backup_name, 'Temp': temp_name, 'Corrupted': corrupted_name,
            'BackupFolder': backup_folder, 'TempFolder': temp_folder, 'CorruptedFolder': corrupted_folder}


def prepare_file(data, legacy=False):
    """Prepare data for saving."""
    data['Time']['Modified'] = time.time()
    data['Version'] = VERSION
    
    if legacy:
        return zlib.compress(cPickle.dumps(data, PICKLE_PROTOCOL))
    
    #Separate the maps from the main dictionary
    numpy_maps = IterateMaps(data['Maps']).separate()
    
    #Write the maps to a zip file in memory
    io = StringIO()
    with CustomOpen(io, 'w') as f:
        f.write(cPickle.dumps(data, PICKLE_PROTOCOL), '_')
        f.write(str(len(numpy_maps)), 'n')
        for i, m in enumerate(numpy_maps):
            f.write(numpy.save(m), i)
    
    #Undo the modify
    IterateMaps(data['Maps']).join(numpy_maps)
    
    return io.getvalue()
    

def decode_file(f, legacy=False):
    """Read compressed data."""
    if legacy:
        return cPickle.loads(zlib.decompress(f.read()))
        
    data = cPickle.loads(f.read('_'))
    numpy_maps = [numpy.load(f.read(i)) for i in range(int(f.read('n')))]
    IterateMaps(data['Maps']).join(numpy_maps)
    return data
    

def load_data(profile_name=None, _update_version=True, _metadata_only=False, _create_new=True):
    """Read a profile (or create new one) and run it through the update."""
    paths = _get_paths(profile_name)
    new_file = False
    
    if _metadata_only:
        return {'Modified': get_modified_time(paths['Main'])}
    
    #Load the main file
    try:
        with CustomOpen(paths['Main'], 'rb') as f:
            loaded_data = decode_file(f, legacy=f.zip is None)
            
    #Load backup if file is corrupted
    except (zlib.error, ValueError):
        try:
            with CustomOpen(paths['Backup'], 'rb') as f:
                loaded_data = decode_file(f, legacy=f.zip is None)
                
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
        if _create_new:
            loaded_data = {}
        else:
            return None
        
    return upgrade_version(loaded_data, update_metadata=_update_version)
    

def save_data(profile_name, data, _compress=True):
    """Handle the safe saving of profiles.
    
    Instead of overwriting, it will save as a temprary file and attempt to rename.
    At any point in time there are two copies of the save.
    """
    
    #This is to allow pre-compressed data to be sent in
    if _compress:
        data = prepare_file(data)
    
    paths = _get_paths(profile_name)
    
    if create_folder(paths['BackupFolder']):
        hide_file(paths['BackupFolder'])
    if create_folder(paths['TempFolder']):
        hide_file(paths['TempFolder'])
    with open(paths['Temp'], 'wb') as f:
        f.write(data)
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

    
class CustomOpen(object):
    """Wrapper containing the default "open" function alongside the "zipfile" one.
    This allows for a lot cleaner method of reading a file that may or may not be a zip.
    """
    
    def __init__(self, filename=None, mode='r', as_zip=True):

        self.file = filename        
        if self.file is None:
            self.mode = 'w'
        else:
            self.mode = mode

        #Attempt to open as zip, or fallback to normal if invalid
        if as_zip:
            if self.mode.startswith('r'):
                try:
                    self._file_object = None
                    self.zip = zipfile.ZipFile(self.file, 'r')
                except zipfile.BadZipfile:
                    as_zip = False
            else:
                if self.file is None:
                    self._file_object = StringIO()
                    self.zip = zipfile.ZipFile(self._file_object, 'w', zipfile.ZIP_DEFLATED)
                else:
                    self._file_object = None
                    self.zip = zipfile.ZipFile(self.file, 'w', zipfile.ZIP_DEFLATED)

        #Open as normal file
        if not as_zip:
            self.zip = None
            if self.mode.startswith('r'):
                self._file_object = open(self.file, mode=self.mode)
            else:
                self._file_object = StringIO()
        
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        """Close the file objects and save file if a name was given."""
        if self.zip is not None:
            self.zip.close()
        if self.mode == 'w' and self.file is not None and self._file_object is not None:
            with open(self.file, 'wb') as f:
                f.write(self._file_object.getvalue())
        if self._file_object is not None:
            self._file_object.close()
        
    def read(self, filename=None, seek=0):
        """Read the file."""
        self.seek(seek)
        if self.zip is None:
            return self._file_object.read()
        return self.zip.read(str(filename))

    def write(self, data, filename=None):
        """Write to the file."""
        if self.zip is None:
            return self._file_object.write(data)
        if filename is None:
            raise TypeError('filename required when writing to zip')
        return self.zip.writestr(str(filename), data)
 
    def seek(self, amount):
        """Seek to a certain point of the file."""
        if amount is None or self._file_object is None:
            return
        return self._file_object.seek(amount)
