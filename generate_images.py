from __future__ import division
from PIL import Image
from scipy.ndimage.filters import gaussian_filter
import numpy as np

from core.constants import HEATMAP, CONFIG
from core.files import load_program
from core.functions import ColourRange
from core.image import *

def generate_tracks(value_range, numpy_arrays, colour_list=None):

    #Add highest values from each array together
    print 'Merging arrays...'
    max_array = merge_array_max(numpy_arrays)
    
    print 'Converting to RGB...'
    cr = ColourRange(value_range[1] - value_range[0], colour_list or [[255, 255, 255], [0, 0, 0]])
    im = Image.fromarray(convert_to_rgb(max_array, cr))
    return im
    
def generate_clicks(numpy_arrays, colour_list=None):

    #Add all arrays together
    print 'Merging arrays...'
    max_array = merge_array_add(numpy_arrays)

    #Create a new numpy array and copy over the values
    #I'm not sure if there's a way to skip this step since it seems a bit useless
    print 'Converting to heatmap...'
    trim_edges = CONFIG.data['GenerateHeatmap']['TrimEdges']
    h = len(max_array)
    w = len(max_array[0])
    heatmap = np.zeros(h * w).reshape((h, w))
    height_range = range(trim_edges, h - trim_edges)
    width_range = range(trim_edges, w - trim_edges)
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
    cr = ColourRange(max_value - min_value, colour_list or HEATMAP)
    im = Image.fromarray(convert_to_rgb(heatmap, cr))
    return im


def create_tracks(image_name, data):
    print 'Creating mouse tracks...'
    value_range, numpy_arrays = merge_resolutions(data)
    im = generate_tracks(value_range, numpy_arrays)
    im = im.resize(desired_resolution, Image.ANTIALIAS)
    print 'Saving image...'
    im.save(image_name)
    print 'Finished saving.'


def create_heatmap(image_name, data):
    print 'Creating heatmap...'
    value_range, numpy_arrays = merge_resolutions(data, interpolate=False)
    im = generate_clicks(numpy_arrays)
    im = im.resize(desired_resolution, Image.ANTIALIAS)
    print 'Saving image...'
    im.save(image_name)
    print 'Finished saving.'


#Options
profile = 'default'
desired_resolution = (CONFIG.data['GenerateImages']['OutputResolutionX'],
                      CONFIG.data['GenerateImages']['OutputResolutionY'])


main_data = load_program(profile)
print 'Desired resolution: {}x{}'.format(*desired_resolution)

create_tracks('Result/Recent Tracks.png', main_data['Tracks'])    
create_heatmap('Result/Recent Clicks.png', main_data['Clicks'])
