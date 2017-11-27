"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

try:
    from core.image.scipy.gaussian import gaussian_filter
    from core.image.scipy.zoom import zoom
except ImportError:
    from scipy.ndimage.filters import gaussian_filter
    from scipy.ndimage.interpolation import zoom
    

def blur(array, size):
    return gaussian_filter(array, sigma=size)

    
def upscale(array, factor):
    if factor[0] == 1 and factor[1] == 1:
        return array
    return zoom(array, factor, order=0)