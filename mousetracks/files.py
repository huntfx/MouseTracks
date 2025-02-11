"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Handle reading and saving of custom file types

from __future__ import absolute_import

import time
import zlib
import os
import sys
import zipfile
from operator import itemgetter
from pickle import Unpickler  # cPickle.Unpickler in Py 2.7 is not inheritable
from tempfile import gettempdir

from .utils import numpy
from .config.settings import CONFIG
from .constants import DEFAULT_NAME, MAX_INT
from .misc import CustomOpen, format_file_path, format_name
from .utils.compatibility import PYTHON_VERSION, ModuleNotFoundError, BytesIO, unicode, pickle, iteritems, BytesIO
from .utils.os import remove_file, rename_file, create_folder, hide_file, get_modified_time, list_directory, file_exists, get_file_size
from .versions import VERSION, FILE_VERSION, upgrade_version, IterateMaps


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


class RenameUnpickler(Unpickler):
    """Any data saved before file version 34 will also have the "core.files.LoadData" class saved.
    This will remap it

    https://stackoverflow.com/a/53327348/2403000
    """
    def find_class(self, module, name):
        renamed_module = module
        if module == 'core.files':
            renamed_module = 'mousetracks.files'
        return super(RenameUnpickler, self).find_class(renamed_module, name)

    @classmethod
    def loads(cls, pickled_bytes):
        file_obj = BytesIO(pickled_bytes)
        return cls(file_obj).load()


def get_data_filename(name=None):
    """Get file name of data file."""
    if name is None:
        name = DEFAULT_NAME
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
        f.write(pickle.dumps(dict(data), PICKLE_PROTOCOL), 'data.pkl')
        
        #Write metadata for quick access
        f.write(str(VERSION), 'metadata\\version.txt')
        f.write(str(FILE_VERSION), 'metadata\\file.txt')
        f.write(str(data['Time']['Modified']), 'metadata/modified.txt')
        f.write(str(data['Time']['Created']), 'metadata/created.txt')
        f.write(str(data['TimesLoaded']), 'metadata/sessions.txt')
        f.write(str(data['Ticks']['Total']), 'metadata/time.txt')
        
        #Pickle the numpy map, or load it raw if not edited
        for i, m in enumerate(numpy_maps):
            if isinstance(m, numpy.LazyLoader) and m.is_loaded:
                m = m.pop()
            if isinstance(m, numpy.LazyLoader):
                f.write(m.pop(raw=True), 'maps/{}.npy'.format(i))
            else:
                f.write(numpy.save(m), 'maps/{}.npy'.format(i))
    
    #Undo the modify
    IterateMaps(data['Resolution']).join(numpy_maps)
    
    return io.getvalue()
    

def decode_file(f, legacy=False, lazy_load_path=None):
    """Read compressed data."""
    #Old file format
    if legacy:
        return pickle.loads(zlib.decompress(f.read()))
    
    #New zip format (file version 26)
    try:
        data = RenameUnpickler.loads(f.read('data.pkl'))
        numpy_maps = []
        i = 0
        if lazy_load_path is None:
            while True:
                try:
                    numpy_maps.append(numpy.load(f.read('maps/{}.npy'.format(i))))
                except KeyError:
                    break
                i += 1
            
    #Original zip format
    except KeyError:
        data = RenameUnpickler.loads(f.read('_'))
        numpy_maps = [numpy.load(f.read(i)) for i in range(int(f.read('n')))]
    
    #Reconnect the numpy maps
    try:
        IterateMaps(data['Maps']).join(numpy_maps, _legacy=True)
    except KeyError:
        IterateMaps(data['Resolution']).join(numpy_maps, _legacy=False, _lazy_load_path=lazy_load_path)
        
    return data
    

def load_data(profile_name=None, _reset_sessions=True, _update_metadata=True, _create_new=True, _metadata_only=False):
    """Read a profile (or create new one) and run it through the update.
    Use LoadData class instead of this.
    """
    paths = _get_paths(profile_name)
    new_file = False
    
    if _metadata_only:
        with CustomOpen(paths['Main'], 'rb') as f:
            metadata = {}

            #Read metadata from zip file
            if f.zip is not None:
                metadata_files = [path for path in f.zip.namelist() if path.startswith('metadata/')]
                for path in metadata_files:
                    metadata[path[9:-4]] = f.read(path)

            #Use inbuilt OS way to get modified time if no metadata
            if 'modified' not in metadata:
                metadata['modified'] = get_modified_time(paths['Main'])
            
            #Get misc information
            metadata['filesize'] = get_file_size(paths['Main'])

            return metadata

    #Load the main file
    try:
        with CustomOpen(paths['Main'], 'rb') as f:
            loaded_data = decode_file(f, legacy=f.zip is None, lazy_load_path=paths['Main'])
            
    #Load backup if file is corrupted
    except (zlib.error, ValueError, zipfile.BadZipfile):
        try:
            with CustomOpen(paths['Backup'], 'rb') as f:
                loaded_data = decode_file(f, legacy=f.zip is None, lazy_load_path=paths['Main'])
                
        except (IOError, zlib.error, ValueError):
            new_file = True
            
            #Move corrupt file into a folder instead of just silently delete
            if create_folder(paths['CorruptedFolder'], is_file=False):
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
    
    return upgrade_version(loaded_data, reset_sessions=_reset_sessions, update_metadata=_update_metadata)


def get_metadata(profile):
    try:
        return load_data(profile, _metadata_only=True)
    except IOError:
        return None

    
class LoadData(dict):
    """Wrapper for the load_data function to allow for custom functions."""
    def __init__(self, profile_name=None, empty=False, _reset_sessions=True, _update_metadata=True):
        if empty:
            data = upgrade_version()
        else:
            data = load_data(profile_name=profile_name, _reset_sessions=_reset_sessions, _update_metadata=_update_metadata, _create_new=True)
                         
        super(self.__class__, self).__init__(data)
        
        self.version = self['Version']
        self.name = profile_name
    
    def _get_track_map(self, track_type, session=False):
        """Return dictionary of tracks along with top resolution and range of values.
        
        TODO: Test sum of arrays vs length of arrays to get top resolution
        """
        start_time = self['Ticks']['Session'][track_type] if session else 0
        
        top_resolution = None
        max_records = 0
        min_value = float('inf')
        max_value = -float('inf')
        result = {}
        for resolution, maps in iteritems(self['Resolution']):
            array = numpy.max(maps[track_type] - start_time, 0)
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
        
    def get_tracks(self, session=False):
        """Return top resolution, min/max values, and dictionary of normal tracks."""
        return self._get_track_map('Tracks', session=session)
        
    def get_speed(self, session=False):
        """Return top resolution, min/max values, and dictionary of speed tracks."""
        return self._get_track_map('Speed', session=session)
        
    def get_strokes(self, session=False):
        """Return top resolution, min/max values, and dictionary of stroke tracks."""
        return self._get_track_map('Strokes', session=session)
    
    def get_clicks(self, double_click=False, session=False):
        click_type = 'Double' if double_click else 'Single'
        
        top_resolution = None
        max_records = 0
        min_value = float('inf')
        max_value = -float('inf')
        result = {}
        for resolution, maps in iteritems(self['Resolution']):
            click_maps = (maps['Clicks'][click_type]['Left'],
                          maps['Clicks'][click_type]['Middle'],
                          maps['Clicks'][click_type]['Right'])
            
            #Get information on array
            contains_data = False
            for array in click_maps:
                if not array.any():
                    continue

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
    
    if create_folder(paths['BackupFolder'], is_file=False):
        hide_file(paths['BackupFolder'])
    if create_folder(paths['TempFolder'], is_file=False):
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

        
def get_data_files():
    """Get the name and metadata of every saved profile in the data folder.
    Some of the metadata may not exist in older files.
    """
    all_files = list_directory(DATA_FOLDER, force_extension=DATA_EXTENSION, remove_extensions=True)
    if all_files is None:
        return []
    output = {}
    for f in all_files:
        metadata = get_metadata(f)
        output[f.replace(DATA_EXTENSION, '')] = metadata
    return output

       
class Lock(object):
    """Stop two versions of the script from being loaded at the same time.
    
    TODO: Figure out how to make Python actually close the damn files when I want them closed.
    This has to be disabled if a script restart option is provided, because this happens with multiprocessing:
        >>> file = open(filename, 'w')
        >>> file.closed
        False
        >>> file.close()
        >>> file.closed
        True
        >>> rename(filename, newname)
        #ERROR FILE ISNT CLOSED (fu python)
    """
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
        """Open a new locked file, or return None if it already exists.
        Do not hide the file or Python can't close it.
        """
        if not file_exists(self._name) or remove_file(self._name):
            f = open(self._name, 'w')
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