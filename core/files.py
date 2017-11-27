"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import time
import zlib
import os
import zipfile
from operator import itemgetter
from tempfile import gettempdir

import core.numpy as numpy
from core.base import format_file_path, format_name
from core.config import CONFIG
from core.compatibility import PYTHON_VERSION, get_items, BytesIO, unicode, pickle
from core.constants import DEFAULT_NAME, MAX_INT
from core.os import remove_file, rename_file, create_folder, hide_file, get_modified_time, list_directory, file_exists
from core.versions import VERSION, FILE_VERSION, upgrade_version, IterateMaps


TEMPORARY_PATH = gettempdir()

DATA_FOLDER = format_file_path(CONFIG['Paths']['Data'])

DATA_EXTENSION = '.mtk'

DATA_NAME = '[PROGRAM]' + DATA_EXTENSION

DATA_BACKUP_FOLDER = '.backup'

DATA_TEMP_FOLDER = '.temp'

DATA_CORRUPT_FOLDER = '.corrupted'

DATA_SAVED_FOLDER = 'Saved'

PICKLE_PROTOCOL = min(pickle.HIGHEST_PROTOCOL, 2)

LOCK_FILE = '{}/mousetrack-{}.lock'.format(TEMPORARY_PATH, format_name(DATA_FOLDER, '-_'))   #Temporary folder
#LOCK_FILE = '{}/mousetrack-{}.lock'.format(DATA_FOLDER, 1)   #Data folder (for testing)


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
    data['FileVersion'] = FILE_VERSION
    data['Version'] = VERSION
    
    if legacy:
        return zlib.compress(pickle.dumps(data, PICKLE_PROTOCOL))
    
    #Separate the maps from the main dictionary
    numpy_maps = IterateMaps(data['Resolution']).separate()
    
    #Write the maps to a zip file in memory
    io = BytesIO()
    with CustomOpen(io, 'w') as f:
        f.write(pickle.dumps(data, PICKLE_PROTOCOL), '_')
        f.write(str(len(numpy_maps)), 'n')
        for i, m in enumerate(numpy_maps):
            f.write(numpy.save(m), i)
    
    #Undo the modify
    IterateMaps(data['Resolution']).join(numpy_maps)
    
    return io.getvalue()
    

def decode_file(f, legacy=False):
    """Read compressed data."""
    if legacy:
        return pickle.loads(zlib.decompress(f.read()))
        
    data = pickle.loads(f.read('_'))
    numpy_maps = [numpy.load(f.read(i)) for i in range(int(f.read('n')))]
    try:
        IterateMaps(data['Maps']).join(numpy_maps, _legacy=True)
    except KeyError:
        IterateMaps(data['Resolution']).join(numpy_maps, _legacy=False)
    return data

    
def read_metadata(profile_name=None):
    paths = _get_paths(profile_name)
    return {'Modified': get_modified_time(paths['Main'])}
    

def load_data(profile_name=None, _update_metadata=True, _create_new=True):
    """Read a profile (or create new one) and run it through the update.
    Use LoadData class instead of this.
    """
    paths = _get_paths(profile_name)
    new_file = False
    
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
    
    return upgrade_version(loaded_data, update_metadata=_update_metadata)

    
class LoadData(dict):
    """Wrapper for the load_data function to allow for custom functions."""
    def __init__(self, profile_name=None, empty=False, _update_metadata=True):
        if empty:
            data = upgrade_version()
        else:
            data = load_data(profile_name=profile_name, _update_metadata=_update_metadata, _create_new=True)
                         
        super(LoadData, self).__init__(data)
        
        self.version = self['Version']
        self.name = profile_name
    
    def get_tracks(self, session=False):
        """Return dictionary of tracks along with top resolution and range of values."""
        start_time = self['Ticks']['Session']['Tracks'] if session else 0
        
        top_resolution = None
        max_records = 0
        min_value = float('inf')
        max_value = -float('inf')
        result = {}
        for resolution, maps in get_items(self['Resolution']):
            array = numpy.max(maps['Tracks'] - start_time, 0)
            num_records = numpy.count(array)
            if num_records:
                result[resolution] = array
                
                #Find resolution with most data
                if num_records > max_records:
                    max_records = num_records
                    top_resolution = resolution
                
                #Find the highest and lowest recorded values
                min_value = min(min_value, numpy.min(array))
                max_value = max(max_value, numpy.max(array))
        
        if not result:
            return None
        
        return top_resolution, (int(min_value), int(max_value)), result
    
    def get_clicks(self, double_click=False, session=False):
        session = 'Session' if session else 'All'
        click_type = 'Double' if double_click else 'Single'
        
        top_resolution = None
        max_records = 0
        min_value = float('inf')
        max_value = -float('inf')
        result = {}
        for resolution, maps in get_items(self['Resolution']):
            click_maps = (maps['Clicks'][session][click_type]['Left'],
                          maps['Clicks'][session][click_type]['Middle'],
                          maps['Clicks'][session][click_type]['Right'])
            
            #Get information on array
            contains_data = False
            for array in click_maps:
                num_records = numpy.count(array)
                if num_records:
                    contains_data = True
                
                #Find resolution with most data
                if num_records > max_records:
                    max_records = num_records
                    top_resolution = resolution
                
                #Find the highest and lowest recorded values
                min_value = min(min_value, numpy.min(array))
                max_value = max(max_value, numpy.max(array))
                
            if contains_data:
                result[resolution] = click_maps
        
        if not result:
            return None
        
        return top_resolution, (int(min_value), int(max_value)), result
                
        
    def get_keys(self):
        raise NotImplementedError
        
    def get_buttons(self):
        raise NotImplementedError
        
        
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
                    self._file_object = BytesIO()
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
                self._file_object = BytesIO()
        
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
            if isinstance(data, (str, unicode)):
                return self._file_object.write(data.encode('utf-8'))
            return self._file_object.write(data)
        if filename is None:
            raise TypeError('filename required when writing to zip')
        return self.zip.writestr(str(filename), data)
 
    def seek(self, amount):
        """Seek to a certain point of the file."""
        if amount is None or self._file_object is None:
            return
        return self._file_object.seek(amount)
        
        
class Lock(object):
    """Stop two versions of the script from being loaded at the same time."""
    def __init__(self, file_name=LOCK_FILE):
        self._name = file_name
        self.closed = False
    
    def __enter__(self):
        self._file = self.create()
        return self
        
    def __exit__(self, *args):
        self.release()
        
    def __bool__(self):
        return self._file is not None
    __nonzero__ = __bool__
    
    def get_file_name(self):
        return self._name
        
    def get_file_object(self):
        return self._file
    
    def create(self):
        """Open a new locked file, or return None if it already exists."""
            
        #Check if file is locked, or create one
        if not file_exists(self._name) or remove_file(self._name):
            f = open(self._name, 'w')
            hide_file(self._name)
        else:
            f = None
        return f
    
    def release(self):
        """Release the locked file, and delete if possible.
        Issue with multithreading where the file seems impossible to delete, so just ignore for now.
        """            
        if not self.closed:
            if self._file is not None:
                self._file.close()
            self.closed = True
            return remove_file(self._name)