from mousetracks.files import LoadData

print(LoadData('Path Of Exile').keys())

'''import pickle

with open(r"D:\Peter\Documents\test.txt", 'rb') as f:
    x = f.read()


#with open(r"D:\Peter\Documents\test2.txt", 'wb') as f:
#    f.write(x)

class Core(object):
    def __init__(self, *args, **kwargs):
        pass
#pickle.loads(x)

import io
import pickle
import cPickle
import cStringIO

import sys

class _DictOverride(dict):
    pass
class _ImportOverride(object):
    LoadData = _DictOverride
    
sys.modules['core.files'] = _ImportOverride

class RenameUnpickler(pickle.Unpickler):

    def find_class(self, module, name):
        renamed_module = module
        print('pickle', module)
        #if module == "core.files":
        #    renamed_module = "mousetracks.utils"

        return pickle.Unpickler.find_class(self, renamed_module, name)
    
    def loads(self, bytes):
        file_obj = io.BytesIO(pickled_bytes)
        return renamed_load(file_obj)
        

def renamed_load(file_obj):
    return RenameUnpickler(file_obj).load()


def renamed_loads(pickled_bytes):
    file_obj = io.BytesIO(pickled_bytes)
    return renamed_load(file_obj)


    
y = cPickle.loads(x)
print type(y)

with open(r"D:\Peter\Documents\test3.txt", 'wb') as f:
    f.write(cPickle.dumps(y))

def print_types(x):
    if isinstance(x, dict):
        for k, v in x.items():
            print_types(v)
    elif isinstance(x, (list, tuple)):
        for i in x:
            print_types(i)
    else:
        t = type(x)
        if t not in (float, str, int):
            print(t)

print_types(y)


#['Distance', 'FileVersion', 'Gamepad', 'Sessions', 'Keys', 'Ticks', 'TimesLoaded', 'HistoryAnimation', 'Version', 'Time', 'VersionHistory', 'Resolution']'''