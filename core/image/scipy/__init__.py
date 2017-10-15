from __future__ import absolute_import

try:
    from core.image.scipy.gaussian import gaussian_filter
    from core.image.scipy.zoom import zoom
except ImportError: #DLL load failed: %1 is not a valid Win32 application - maybe issue with 32 bit python, needs testing
    from scipy.ndimage.filters import gaussian_filter
    from scipy.ndimage.interpolation import zoom
    

def blur(array, size):
    return gaussian_filter(array, sigma=size)

    
def upscale(array, factor):
    if factor[0] == 1 and factor[1] == 1:
        return array
    return zoom(array, factor, order=0)
