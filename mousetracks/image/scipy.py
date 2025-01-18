"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

import sys

try:
    from scipy import ndimage
except ImportError:
    sys.path.append('resources/build')
    from scipy import ndimage

from ..utils.numpy import process_numpy_array


@process_numpy_array
def blur(array, size):
    return ndimage.gaussian_filter(array, sigma=size)


@process_numpy_array
def upscale(array, factor):
    if factor[0] == 1 and factor[1] == 1:
        return array
    return ndimage.zoom(array, factor, order=0)