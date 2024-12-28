"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Easy to use wrappers for numpy

from __future__ import division, absolute_import

import numpy
from functools import wraps

from .compatibility import StringIO, BytesIO
from ..misc import CustomOpen


_NUMPY_DTYPES = {
    'int8': numpy.int8,
    'int16': numpy.int16,
    'int32': numpy.int32,
    'int64': numpy.int64,
    'uint8': numpy.uint8,
    'uint16': numpy.uint16,
    'uint32': numpy.uint32,
    'uint64': numpy.uint64,
    'float16': numpy.float16,
    'float32': numpy.float32,
    'float64': numpy.float64,
}

def process_numpy_array(func):
    """Convert LazyLoader class to numpy array if required."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            array = kwargs.pop('array')
        except KeyError:
            array = args[0]
            args = args[1:]
        if isinstance(array, LazyLoader):
            array = array.array
        return func(array, *args, **kwargs)
    return wrapper

def process_numpy_arrays(func):
    """Convert list of LazyLoader classes to numpy arrays if required."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            arrays = kwargs.pop('arrays')
        except KeyError:
            arrays = args[0]
            args = args[1:]
        arrays = [array.array if isinstance(array, LazyLoader) else array for array in arrays]
        return func(arrays, *args, **kwargs)
    return wrapper


def _get_dtype(dtype):
    """Convert a string to dtype.
    Inbuilt dtypes can't be used without importing numpy.
    """
    try:
        return _NUMPY_DTYPES[dtype]
    except KeyError:
        return None


@process_numpy_array
def set_type(array, dtype):
    if isinstance(dtype, str):
        return array.astype(_get_dtype(dtype))
    else:
        return array.astype(dtype)
        
        
@process_numpy_array
def array(array, create=False, dtype=None):
    if create:
        return numpy.zeros(array[::-1], dtype=_get_dtype(dtype))
    return numpy.array(array, dtype=_get_dtype(dtype))

    
@process_numpy_array
def count(array):
    return (array > 0).sum()
    
    
@process_numpy_array
def mean(array):
    return numpy.mean(array)
    
    
@process_numpy_array
def sum(array):
    return numpy.sum(array)

    
@process_numpy_array
def min(array, value=None):
    if value is None:
        return numpy.amin(array)
    array[array > value] = value
    return array
    
    
@process_numpy_array
def max(array, value=None):
    if value is None:
        return numpy.amax(array)
    array[array < value] = value
    return array
    
        
@process_numpy_array
def power(array, power, dtype=None):
    return numpy.power(array, power, dtype=_get_dtype(dtype))
       
       
@process_numpy_array
def multiply(array, amount, dtype=None):
    if isinstance(array, numpy.ndarray):
        return array * amount
    return numpy.multiply(array, amount, dtype=_get_dtype(dtype))
    
    
@process_numpy_array
def divide(array, amount, as_int=False, dtype=None):
    if as_int:
        return numpy.floor_divide(array, amount, dtype=_get_dtype(dtype))
    return numpy.true_divide(array, amount, dtype=_get_dtype(dtype))


@process_numpy_array
def round(array, decimals=0, dtype=None):
    new_array = numpy.round(array, decimals)
    if dtype is not None:
        return new_array.astype(_get_dtype(dtype))
    else:
        return new_array
    
    
@process_numpy_array
def sort(array, unique=False):
    if unique:
        array = numpy.unique(array)
    return numpy.sort(array)
    
    
def compare(result):
    return len(numpy.where(result)[0])

    
def vectorize(func, otype=None):
    return numpy.vectorize(func, otypes=[_get_dtype(otype)])
    
        
@process_numpy_arrays
def merge(arrays, merge_type, dtype=None):
    """Merge multiple arrays for the same size together.
    The type of merge must also be set.
    """

    merge_type = merge_type.lower()
    array_len = len(arrays)
    
    if not array_len:
        return None
    
    elif merge_type.startswith('max'):
        return numpy.maximum.reduce(arrays, dtype=_get_dtype(dtype))
        
    elif merge_type.startswith('min'):
        return numpy.minimum.reduce(arrays, dtype=_get_dtype(dtype))
        
    elif merge_type.startswith('add'):
        return numpy.add.reduce(arrays, dtype=_get_dtype(dtype))
        
    elif merge_type.startswith('sub'):
        return numpy.subtract.reduce(arrays, dtype=_get_dtype(dtype))
        
    elif merge_type.startswith('mul'):
        return numpy.multiply.reduce(arrays, dtype=_get_dtype(dtype))
        
    elif merge_type.startswith('div'):
        return numpy.divide.reduce(arrays, dtype=_get_dtype(dtype))
            
    return arrays[0]


@process_numpy_array
def convert_to_dict(array, dictionary, dtype=None):
    """Assign dictionary values to array where key is the array value."""
    return vectorize(dictionary.__getitem__, dtype)(array)


@process_numpy_array
def remap_to_range(array, dtype=None):
    """Remap an array to a constant 0-n range.

    For example, the values (0, 1, 1.1, 1.5, 50, 50.002, 1054)
    will be remapped to (0, 1, 2, 3, 4, 5, 6).
    """
    values = {v: i for i, v in enumerate(sorted(set(array.ravel())))}
    return convert_to_dict(array, values, dtype)

    
@process_numpy_array
def csv(array):
    io = StringIO
    numpy.savetxt(io, array, fmt='%d', delimiter=',')
    return io.getvalue()
    

@process_numpy_array
def save(array):
    f = BytesIO()
    numpy.save(f, array, fix_imports=True)
    return f.getvalue()

    
def load(saved_array):
    f = BytesIO()
    f.write(saved_array)
    f.seek(0)
    return numpy.load(f)
    

@process_numpy_array
def fill(array, value):
    array.fill(value)
    return array


class LazyLoader(object):
    """Store the file path and array index, and only load when required.
    Reduces memory usage by up to 90%, and significantly speeds up loading.
    """
    def __init__(self, path, index, resolution=None):
        
        self.path = path
        self.index = index

        self._array = None
        self._raw = None
        self._resolution = tuple(resolution) if resolution is not None else None
    
    def _load(self, as_numpy=True):
        """Load from zip file."""
        with CustomOpen(self.path, 'rb') as f:
            try:
                array = f.read('maps/{}.npy'.format(self.index))
            except KeyError:
                array = f.read(self.index)
        if as_numpy:
            return load(array)
        else:
            return array

    @property
    def is_loaded(self):
        """Return True or False if the array is currently loaded."""
        return self._array is not None

    @property
    def array(self):
        """Load array if it doesn't exist or just return it."""
        if not self.is_loaded:
            self._array = self._load()
        
        #If the resolution was somehow created wrongly, then set a new one
        loaded_resolution = tuple(map(int, self._array.shape[::-1]))
        if self._resolution is not None and loaded_resolution != self._resolution:
            self._array = array(self._resolution, create=True, dtype=self._array.dtype)

        return self._array

    def __getitem__(self, item):
        return self.array[item]

    def __setitem__(self, item, value):
        self.array[item] = value
    
    def clear(self):
        """Clear the array from memory."""
        self._array = None

    def pop(self, raw=False):
        """Return the array and free up memory."""
        try:
            if raw:
                return self._load(as_numpy=False)
            else:
                return self.array
        finally:
            self.clear()
    
    #Numpy specific functions since inhertiance doesn't really work
    def __truediv__(self, n):
        return self.array.__truediv__(n)

    def __floordiv__(self, n):
        return self.array.__floordiv__(n)

    def __div__(self, n):
        return self.array.__div__(n)
    
    def __add__(self, n):
        return self.array + n
    __radd__ = __add__
    
    def __sub__(self, n):
        return self.array - n

    def __rsub__(self, n):
        return n - self.array
    
    def any(self):
        return self.array.any()

    def all(self):
        return self.array.all()