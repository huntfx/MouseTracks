from __future__ import division
from PIL import Image
from scipy.ndimage.interpolation import zoom
from scipy.ndimage.filters import gaussian_filter
from scipy.signal import resample
import numpy as np

from _track_constants import HEATMAP
from _track_files import load_program
from _track_functions import ColourRange

def merge_resolutions(main_data, max_resolution=(3840, 2160), interpolate=True):
    """Upscale each resolution to make them all match.
    A list of arrays and range of data will be returned.
    """
    numpy_arrays = []
    highest_value = None
    lowest_value = None
    resolutions = main_data.keys()
    
    if any(not isinstance(i, tuple) for i in resolutions) or any(len(i) != 2 for i in resolutions):
        raise ValueError('incorrect resolutions')

    i = 0
    for current_resolution in resolutions:
        i += 1
        print ('Resizing {}x{} to {}x{}...'
               '({}/{})'.format(*(current_resolution + max_resolution + (i, len(resolutions)))))
        data = main_data[current_resolution]

        #Try find the highest and lowest value
        all_values = set(data.values())
        if not all_values:
            continue
        _lowest_value = min(all_values)
        if lowest_value is None or lowest_value > _lowest_value:
            lowest_value = _lowest_value
        _highest_value = max(all_values)
        if highest_value is None or highest_value < _highest_value:
            highest_value = _highest_value    

        #Build 2D array from data
        new_data = []
        width_range = range(current_resolution[0])
        height_range = range(current_resolution[1])
        for y in height_range:
            new_data.append([])
            for x in width_range:
                try:
                    new_data[-1].append(data[(x, y)])
                except KeyError:
                    new_data[-1].append(0)

        #Calculate the zoom level needed
        zoom_factor = (max_resolution[1] / current_resolution[1],
                       max_resolution[0] / current_resolution[0])
        
        numpy_arrays.append(zoom(np.array(new_data), zoom_factor, order=interpolate))

    return (lowest_value, highest_value), numpy_arrays


def convert_to_rgb(image_array, colour_range):
    """Turn each element in a 2D array to its corresponding colour."""
    
    height_range = range(len(image_array))
    width_range = range(len(image_array[0]))
    
    new_data = [[]]
    total = len(image_array) * len(image_array[0])
    count = 0
    one_percent = int(total / 100)
    last_percent = -1
    for y in height_range:
        if new_data[-1]:
            new_data.append([])
        for x in width_range:
            new_data[-1].append(colour_range.get_colour(image_array[y][x]))
            count += 1
            if not count % one_percent:
                print '{}% complete ({} pixels)'.format(int(round(100 * count / total)), count)
            

    return np.array(new_data, dtype=np.uint8)


def generate_tracks(value_range, numpy_arrays, colour_list=None):

    print 'Generating mouse tracks...'
    #Set up the list of colours
    if colour_list is None:
        colour_list = [[255, 255, 255], [0, 0, 0]]
    cr = ColourRange(value_range[1] - value_range[0], colour_list)

    print 'Merging arrays...'
    if len(numpy_arrays) > 1:
        max_array = np.maximum.reduce(numpy_arrays)
    else:
        max_array = numpy_arrays[0]
    
    print 'Converting to RGB...'
    im = Image.fromarray(convert_to_rgb(max_array, cr))
    return im
    
def generate_clicks(numpy_arrays, colour_list=None, exponential_multiplier=0.5, gaussian_blur=25):

    print 'Merging arrays...'
    if len(numpy_arrays) > 1:
        max_array = np.add.reduce(numpy_arrays)
    else:
        max_array = numpy_arrays[0]
        
    print 'Applying exponential reduction...'
    h = len(max_array)
    w = len(max_array[0])
    heatmap = np.zeros(h * w).reshape((h, w))
    height_range = range(h)
    width_range = range(w)
    for x in width_range:
        for y in height_range:
            try:
                heatmap[y][x] = max_array[y][x] ** exponential_multiplier
            except KeyError:
                pass
            
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
desired_resolution = (1920, 1080)
upscale_resolution = (3840, 2160)
upscale_multiplier = 1

upscale_resolution = tuple(int(i * upscale_multiplier) for i in upscale_resolution)
main_data = load_program(profile)

print 'Desired resolution: {}x{}'.format(*desired_resolution)

value_range, numpy_arrays = merge_resolutions(main_data['Tracks'], upscale_resolution)
im = generate_tracks(value_range, numpy_arrays)
im = im.resize(desired_resolution, Image.ANTIALIAS)
print 'Saving mouse track image...'
im.save('Result/Recent Movement.png')
print 'Finished saving.'


value_range, numpy_arrays = merge_resolutions(main_data['Clicks'], upscale_resolution, interpolate=False)
im = generate_clicks(numpy_arrays)
im = im.resize(desired_resolution, Image.ANTIALIAS)
print 'Saving click heatmap image...'
im.save('Result/Recent Clicks.png')
print 'Finished saving.'
