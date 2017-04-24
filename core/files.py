import cPickle
import zlib
import re
import time
import os
from _os import remove_file, rename_file, create_folder
from constants import VERSION


def load_program(program_name=None):
    if program_name is None:
        program_name = 'Default'
    elif isinstance(program_name, (list, tuple)):
        program_name = program_name[0]
    name_format = re.sub('[^A-Za-z0-9]+', '', program_name).lower()
    try:
        with open('Data/{}.data'.format(name_format), 'rb') as f:
            loaded_data = cPickle.loads(zlib.decompress(f.read()))
            loaded_data['TimesLoaded'] += 1
            return loaded_data
    except (IOError, zlib.error):
        try:
            with open('Data/{}.data.old'.format(name_format), 'rb') as f:
                return cPickle.loads(zlib.decompress(f.read()))
        except (IOError, zlib.error):
            return {'Count': 0,
                    'Tracks': {},
                    'Clicks': {},
                    'Keys': {},
                    'LastSave': time.time(),
                    'Version': VERSION,
                    'Ticks': 0,
                    'TimesLoaded': 0}


def save_program(program_name, data):
    if program_name is None:
        program_name = ['Default', 'Default']
    name_format = re.sub('[^A-Za-z0-9]+', '', program_name[0]).lower()
    data['LastSave'] = time.time()
    data['Version'] = VERSION
    compressed_data = zlib.compress(cPickle.dumps(data))
        
    old_name = 'Data/{}.data.old'.format(name_format)
    new_name = 'Data/{}.data'.format(name_format)
    temp_name = 'Data/{}.data.{}'.format(name_format, time.time())

    create_folder('Data')
    with open(temp_name, 'wb') as f:
        f.write(compressed_data)
    remove_file(old_name)
    rename_file(new_name, old_name)
    if rename_file(temp_name, new_name):
        return True
    else:
        remove_file(temp_name)
        return False
