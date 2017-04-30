from __future__ import division
from PIL import Image
from scipy.ndimage.filters import gaussian_filter

from image import *
from functions import ColourRange
from constants import COLOURS

def _generate(numpy_arrays):

    #Add all arrays together
    print 'Merging arrays...'
    max_array = merge_array_add(numpy_arrays)

    #Create a new numpy array and copy over the values
    #I'm not sure if there's a way to skip this step since it seems a bit useless
    print 'Converting to heatmap...'
    h = len(max_array)
    w = len(max_array[0])
    heatmap = np.zeros(h * w).reshape((h, w))
    height_range = range(h)
    width_range = range(w)
    exponential_multiplier = CONFIG.data['GenerateHeatmap']['ExponentialMultiplier']
    for x in width_range:
        for y in height_range:
            heatmap[y][x] = max_array[y][x] ** exponential_multiplier

    #Blur the array
    print 'Applying gaussian blur...'
    gaussian_blur = CONFIG.data['GenerateHeatmap']['GaussianBlurSize']
    heatmap = gaussian_filter(heatmap, sigma=gaussian_blur)

    #This part is temporary until the ColourRange function is fixed
    heatmap *= 1000000

    #Calculate the average of all the points
    print 'Calculating average...'
    total = [0, 0]
    for x in width_range:
        for y in height_range:
            total[0] += 1
            total[1] += heatmap[y][x]

    #Set range of heatmap
    min_value = 0
    max_value = 10 * total[1] / total[0]
    if CONFIG.data['GenerateHeatmap']['SetMaxRange']:
        max_value = CONFIG.data['GenerateHeatmap']['SetMaxRange']
        print 'Manually set highest range to {}'.format(max_value)
    
    #Convert each point to an RGB tuple
    print 'Converting to RGB...'    
    cr = ColourRange(max_value - min_value, COLOURS['HeatMap'])
    im = Image.fromarray(convert_to_rgb(heatmap, cr))
    return im


def generate(image_name, data):
    print 'Creating heatmap...'
    value_range, numpy_arrays = merge_resolutions(data, interpolate=False)
    im = _generate(numpy_arrays)
    resolution = (CONFIG.data['GenerateImages']['OutputResolutionX'],
                  CONFIG.data['GenerateImages']['OutputResolutionY'])
    im = im.resize(resolution, Image.ANTIALIAS)
    print 'Saving image...'
    im.save(image_name)
    print 'Finished saving.'
