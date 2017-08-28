from __future__ import absolute_import

#Took only the necessary functions from scipy, as to not have a huge filesize
from core.image.scipy.gaussian import gaussian_filter
from core.image.scipy.zoom import zoom


def blur(array, size):
    return gaussian_filter(array, sigma=size)

    
def upscale(array, factor):
    if factor[0] == 1 and factor[1] == 1:
        return array
    return zoom(array, factor, order=0)
