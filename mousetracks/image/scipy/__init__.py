"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Import the local scipy if possible, otherwise fallback to the installed one

from __future__ import absolute_import

from ...utils.numpy import process_numpy_array
try:
    from .gaussian import gaussian_filter
    from .zoom import zoom
except ImportError:
    from scipy.ndimage.filters import gaussian_filter
    from scipy.ndimage.interpolation import zoom
    

@process_numpy_array
def blur(array, size):
    return gaussian_filter(array, sigma=size)


@process_numpy_array
def upscale(array, factor):
    if factor[0] == 1 and factor[1] == 1:
        return array
    return zoom(array, factor, order=0)