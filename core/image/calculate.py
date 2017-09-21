from __future__ import division, absolute_import
from multiprocessing import Process, Queue, cpu_count
from PIL import Image

from core.image.scipy import blur, upscale
from core.compatibility import range, _print
from core.config import CONFIG
from core.maths import round_int
import core.numpy as numpy


def gaussian_size(width, height):
    """Calculate correct size of gaussian blur.
    Currently only height is taken into account, but this could change, so takes both values.
    """
    gaussian_base = CONFIG['GenerateHeatmap']['_GaussianBlurBase']
    gaussian_mult = CONFIG['GenerateHeatmap']['GaussianBlurMultiplier']
    try:
        return round_int(height * gaussian_base * gaussian_mult)
    except TypeError:
        raise ValueError('invalid input type, must be int')


def merge_resolutions(main_data, map_selection=False, 
                      session_start=None, high_precision=False):
    """Upscale each resolution to make them all match.
    A list of arrays and range of data will be returned.
    """
    
    numpy_arrays = []
    if map_selection:
        resolutions = main_data[map_selection[0]].keys()
    else:
        resolutions = main_data.keys()
            
    output_resolution = (CONFIG['GenerateImages']['OutputResolutionX'],
                         CONFIG['GenerateImages']['OutputResolutionY'])
        
    #Calculate upscale resolution
    max_x = max(x for x, y in resolutions)
    max_y = max(y for x, y in resolutions)
    if high_precision:
        max_x *= 2
        max_y *= 2
        
    _max_height_x = int(round(max_x / output_resolution[0] * output_resolution[1]))
    if _max_height_x > max_y:
        max_resolution = (max_x, _max_height_x)
    else:
        _max_width_y = int(round(max_y / output_resolution[1] * output_resolution[0]))
        max_resolution = (_max_width_y, max_y)
    CONFIG['GenerateImages']['_UpscaleResolutionX'], CONFIG['GenerateImages']['_UpscaleResolutionY'] = max_resolution
                     
    #Read total number of images that will need to be upscaled
    max_count = 0
    for current_resolution in resolutions:
        if map_selection:
            max_count += len(map_selection)
        else:
            max_count += 1
    
    i = 0
    count = 0
    total = 0
    
    #Upscale each resolution to the same level
    highest_value = 0
    lowest_value = 0
    for current_resolution in resolutions:
        if map_selection:
            array_list = [main_data[m][current_resolution] for m in map_selection]
        else:
            array_list = [main_data[current_resolution]]
            
        for data in array_list:
            i += 1
            if current_resolution == max_resolution:
                _print('Processing {}x{}... ({}/{})'.format(current_resolution[0], 
                                                            current_resolution[1],
                                                            i, max_count))
            else:
                _print('Processing {}x{} and resizing to {}x{}...'
                       ' ({}/{})'.format(current_resolution[0], current_resolution[1],
                                         max_resolution[0], max_resolution[1],
                                         i, max_count))
                                         
            lowest_value = min(lowest_value, numpy.min(data))
            highest_value = max(highest_value, numpy.max(data))

            #Calculate the zoom level needed
            zoom_factor = (max_resolution[1] / current_resolution[1],
                           max_resolution[0] / current_resolution[0])
            numpy_arrays.append(upscale(numpy.array(data), zoom_factor))
    
    if session_start is not None:
        highest_value -= session_start
    return (lowest_value, highest_value), numpy_arrays
    
    
def convert_to_rgb(image_array, colour_range):
    """Convert an array into colours."""
    
    _print('Converting {} points to RGB values... (this may take a few seconds)'.format(image_array.size))
    return colour_range.convert_array(image_array)
    
    

def arrays_to_heatmap(numpy_arrays, gaussian_size, clip):
    """Convert list of arrays into a heatmap.
    The stages and values are chosen with trial and error, 
    so this function is still open to improvement.
    """
    
    #Add all arrays together
    _print('Merging arrays...')
    merged_arrays = numpy.merge(numpy_arrays, 'add', 'float64')
    
    #Set to constant values
    _print('Flattening values...')
    flattened = numpy.remap_to_range(merged_arrays)
    
    #Blur the array
    if gaussian_size:
        _print('Applying gaussian blur...')
        heatmap = blur(flattened, gaussian_size)
    else:
        heatmap = flattened
    
    _print('Finding range limits...')
    min_value = numpy.min(heatmap)
    
    #Lower the maximum value a little
    all_values = numpy.sort(heatmap.ravel(), unique=True)
    max_value = all_values[round_int(all_values.size * clip)]
    
    return ((min_value, max_value), heatmap)


def arrays_to_colour(colour_range, numpy_arrays):
    """Convert an array of floats or integers into an image object."""

    max_array = numpy.merge(numpy_arrays, 'max')
    if max_array is None:
        return None
    
    return Image.fromarray(convert_to_rgb(max_array, colour_range))
