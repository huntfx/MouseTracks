from __future__ import division, absolute_import
from cStringIO import StringIO
import numpy


_NUMPY_DTYPES = {
    'bool_': numpy.bool_,
    'int_': numpy.int_,
    'float_': numpy.float_,
    'complex_': numpy.complex_,
    'intc': numpy.intc,
    'intp': numpy.intp,
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
    'complex64': numpy.complex64,
    'complex128': numpy.complex128,
}


def _get_dtype(dtype):
    try:
        return _NUMPY_DTYPES[dtype]
    except KeyError:
        return None


def set_type(array, dtype):
    if isinstance(dtype, str):
        return array.astype(_get_dtype(dtype))
    else:
        return array.astype(dtype)
        
        
def array(array, create=False, dtype=None):
    if create:
        return numpy.zeros(array[::-1], dtype=_get_dtype(dtype))
    return numpy.array(array, dtype=_get_dtype(dtype))

    
def len(array):
    return (array > 0).sum()
    
    
def mean(array):
    return numpy.mean(array)
    
    
def sum(array):
    return numpy.sum(array)

    
def min(array):
    return numpy.amin(array)
    
    
def max(array):
    return numpy.amax(array)

        
def power(array, power, dtype=None):
    return numpy.power(array, power, dtype=_get_dtype(dtype))
       
       
def multiply(array, amount, dtype=None):
    if isinstance(array, numpy.ndarray):
        return array * amount
    return numpy.multiply(array, amount, dtype=_get_dtype(dtype))
    
    
def divide(array, amount, as_int=False, dtype=None):
    if as_int:
        return numpy.floor_divide(array, amount, dtype=_get_dtype(dtype))
    return numpy.true_divide(array, amount, dtype=_get_dtype(dtype))

    
def compare(result):
    return len(numpy.where(result)[0])

    
def vectorize(func, otype=None):
    return numpy.vectorize(func, otypes=[_get_dtype(otype)])
    
        
def merge(arrays, merge_type, dtype=None):
    
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


def convert_to_dict(array, dictionary, dtype=None):
    """Assign dictionary values to array where key is the array value."""
    return vectorize(dictionary.__getitem__, dtype)(array)


def remap_to_range(array, dtype=None):
    """Remap an array to a 0-n range."""
    values = {v: i for i, v in enumerate(sorted(set(array.ravel())))}
    return convert_to_dict(array, values, dtype)

    
def csv(array):
    f = StringIO
    numpy.savetxt(f, array, fmt='%d', delimiter=',')
    return io.getvalue()
    

def save(array):
    f = StringIO()
    numpy.save(f, array, fix_imports=True)
    return f.getvalue()

    
def load(saved_array):
    f = StringIO()
    f.write(saved_array)
    f.seek(0)
    return numpy.load(f)
