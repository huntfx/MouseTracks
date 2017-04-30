from __future__ import division
from PIL import Image

from image import *
from functions import ColourRange
from constants import COLOURS

def _generate(value_range, numpy_arrays, colour_list=None):

    #Add highest values from each array together
    print 'Merging arrays...'
    max_array = merge_array_max(numpy_arrays)
    
    print 'Converting to RGB...'
    cr = ColourRange(value_range[1] - value_range[0], COLOURS['BlackToWhite'])
    im = Image.fromarray(convert_to_rgb(max_array, cr))
    return im

def generate(image_name, data):
    print 'Creating mouse tracks...'
    value_range, numpy_arrays = merge_resolutions(data)
    im = _generate(value_range, numpy_arrays)
    resolution = (CONFIG.data['GenerateImages']['OutputResolutionX'],
                  CONFIG.data['GenerateImages']['OutputResolutionY'])
    im = im.resize(resolution, Image.ANTIALIAS)
    print 'Saving image...'
    im.save(image_name)
    print 'Finished saving.'
