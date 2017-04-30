from __future__ import division
import numpy as np
from scipy.ndimage.interpolation import zoom

from constants import CONFIG


def merge_array_max(arrays):
    if len(arrays) > 1:
        return np.maximum.reduce(arrays)
    else:
        return arrays[0]


def merge_array_add(arrays):
    if len(arrays) > 1:
        return np.add.reduce(arrays)
    else:
        return arrays[0]


def merge_resolutions(main_data, max_resolution=None, interpolate=True):
    """Upscale each resolution to make them all match.
    A list of arrays and range of data will be returned.
    """
    if max_resolution is None:
        max_resolution = (CONFIG.data['GenerateImages']['UpscaleResolutionX'],
                          CONFIG.data['GenerateImages']['UpscaleResolutionY'])
    
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
        if max_resolution != current_resolution:
            zoom_factor = (max_resolution[1] / current_resolution[1],
                           max_resolution[0] / current_resolution[0])
            
            numpy_arrays.append(zoom(np.array(new_data), zoom_factor, order=interpolate))
        else:
            numpy_arrays.append(np.array(new_data))

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
