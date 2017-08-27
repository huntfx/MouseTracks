from __future__ import division, absolute_import
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

        
def numpy_merge(arrays, merge_type, dtype=None):
    
    merge_type = merge_type.lower()
    array_len = len(arrays)
    if not array_len:
        return None
    elif array_len > 1:
        if merge_type.startswith('max'):
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

        
def numpy_power(array, power, dtype=None):
    return numpy.power(array, power, dtype=_get_dtype(dtype))
        
        
def numpy_array(array, dtype=None):
    return numpy.array(array, dtype=_get_dtype(dtype))


def numpy_sum(array):
    return numpy.sum(array)
    

def upscale(array, factor):
    """Scale array by a factor.
    Got from https://stackoverflow.com/questions/45027220/expanding-zooming-in-a-numpy-array.
    """
    array = numpy.asarray(array)
    try:
        slices = [slice(0, v, 1 / factor[i]) for i, v in enumerate(array.shape)]
    except TypeError:
        slices = [slice(0, v, 1 / factor) for i, v in enumerate(array.shape)]
    return array[tuple(numpy.mgrid[slices].astype('i'))]
    
    
def _gaussian_kernel(size, size_y=None):
    size = int(size)
    if not size_y:
        size_y = size
    else:
        size_y = int(size_y)
    x, y = numpy.mgrid[-size:size+1, -size_y:size_y+1]
    g = numpy.exp(-(x**2/float(size)+y**2/float(size_y)))
    return g / g.sum()

    
def blur(array, size):
    gaussian_filter = _gaussian_kernel(size)
    raise NotImplementedError('gaussian blur in numpy not implemented, please install scipy for now')
