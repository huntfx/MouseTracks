from scipy.ndimage.filters import gaussian_filter
from scipy.ndimage.interpolation import zoom


def blur(array, size):
    return gaussian_filter(array, sigma=size)

    
def upscale(array, factor):
    if factor[0] == 1 and factor[1] == 1:
        return array
    return zoom(array, factor, order=0)
