from __future__ import division
from PIL import Image
from scipy.ndimage.filters import gaussian_filter
import numpy as np

from core.constants import HEATMAP, CONFIG
from core.files import load_program
from core.functions import ColourRange
from core.image import *

def generate_tracks(value_range, numpy_arrays, colour_list=None):

    print 'Generating mouse tracks...'
    cr = ColourRange(value_range[1] - value_range[0], colour_list or [[255, 255, 255], [0, 0, 0]])

    print 'Merging arrays...'
    max_array = merge_array_max(numpy_arrays)
    
    print 'Converting to RGB...'
    im = Image.fromarray(convert_to_rgb(max_array, cr))
    return im
    
def generate_clicks(numpy_arrays, colour_list=None, exponential_multiplier=None,
                    gaussian_blur=None, trim_edges=0):

    if exponential_multiplier is None:
        exponential_multiplier = CONFIG.data['GenerateHeatmap']['ExponentialMultiplier']
    if gaussian_blur is None:
        gaussian_blur = CONFIG.data['GenerateHeatmap']['GaussianBlurSize']

    print 'Merging arrays...'
    max_array = merge_array_add(numpy_arrays)

    print 'Converting to heatmap...'
    h = len(max_array)
    w = len(max_array[0])
    heatmap = np.zeros(h * w).reshape((h, w))
    height_range = range(trim_edges, h - trim_edges)
    width_range = range(trim_edges, w - trim_edges)
    for x in width_range:
        for y in height_range:
            heatmap[y][x] = max_array[y][x] ** exponential_multiplier
            
    print 'Applying gaussian blur...'
    heatmap = gaussian_filter(heatmap, sigma=gaussian_blur)

    #This part is temporary until the ColourRange function is fixed
    heatmap *= 1000000
    
    value_range = (min(i for j in heatmap for i in j), max(i for j in heatmap for i in j))
    cr = ColourRange(value_range[1] - value_range[0], colour_list or HEATMAP)
    
    print 'Converting to RGB...'
    im = Image.fromarray(convert_to_rgb(heatmap, cr))
    return im

#Options
profile = 'default'
desired_resolution = (CONFIG.data['GenerateImages']['OutputResolutionX'],
                      CONFIG.data['GenerateImages']['OutputResolutionY'])


main_data = load_program(profile)

print 'Desired resolution: {}x{}'.format(*desired_resolution)

def create_tracks(image_name, data):
    value_range, numpy_arrays = merge_resolutions(data)
    im = generate_tracks(value_range, numpy_arrays)
    im = im.resize(desired_resolution, Image.ANTIALIAS)
    print 'Saving mouse track image...'
    im.save(image_name)
    print 'Finished saving.'


def create_heatmap(image_name, data, trim_edges=None):
    if trim_edges is None:
        trim_edges = CONFIG.data['GenerateHeatmap']['TrimEdges']
    
    value_range, numpy_arrays = merge_resolutions(data, interpolate=False)
    im = generate_clicks(numpy_arrays, trim_edges=trim_edges)
    im = im.resize(desired_resolution, Image.ANTIALIAS)
    
    print 'Saving click heatmap...'
    im.save(image_name)
    print 'Finished saving.'

create_tracks('Result/Recent Tracks.png', main_data['Tracks'])    
create_heatmap('Result/Recent Clicks.png', main_data['Clicks'])
