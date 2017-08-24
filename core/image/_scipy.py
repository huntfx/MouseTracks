from __future__ import absolute_import
from scipy.ndimage.filters import gaussian_filter
from scipy.ndimage.interpolation import zoom
from warnings import catch_warnings


def blur(array, size):
    return gaussian_filter(array, sigma=size)

    
def upscale(array, factor):
    if factor[0] == 1 and factor[1] == 1:
        return array
    with catch_warnings('ignore'):
        return zoom(array, factor, order=0)
