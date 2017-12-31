"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import, division

from multiprocessing import Process, Queue, cpu_count
from PIL import Image

import core.numpy as numpy
from core.image.scipy import blur, upscale
from core.compatibility import range, Message, get_items
from core.config import CONFIG
from core.maths import round_int


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


def calculate_resolution(resolutions, output_resolution=None):

    if output_resolution is None or not CONFIG['GenerateImages']['AutomaticResolution']:
        output_resolution = (CONFIG['GenerateImages']['OutputResolutionX'],
                             CONFIG['GenerateImages']['OutputResolutionY'])

    max_x = max(x for x, y in resolutions)
    max_y = max(y for x, y in resolutions)
    if CONFIG['GenerateImages']['HighPrecision']:
        max_x *= 2
        max_y *= 2
        
    _max_height_x = int(round(max_x / output_resolution[0] * output_resolution[1]))
    if _max_height_x > max_y:
        max_resolution = (max_x, _max_height_x)
    else:
        _max_width_y = int(round(max_y / output_resolution[1] * output_resolution[0]))
        max_resolution = (_max_width_y, max_y)

    CONFIG['GenerateImages']['_OutputResolutionX'], CONFIG['GenerateImages']['_OutputResolutionY'] = output_resolution
    CONFIG['GenerateImages']['_UpscaleResolutionX'], CONFIG['GenerateImages']['_UpscaleResolutionY'] = max_resolution

    return output_resolution, max_resolution


def upscale_arrays_to_resolution(arrays, target_resolution, skip=[]):
    """Upscale a dict of arrays to a certain resolution.
    The dictionary key must be a resolution,
    and the values can either be an array or list of arrays.
    
    Use skip to ignore array indexes in the list.
    """
    if isinstance(skip, int):
        skip = [skip]
    skip = set(skip)

    #Count number of arrays
    num_arrays = 0
    for resolution, array_list in get_items(arrays):
        if isinstance(array_list, (list, tuple)):
            array_len = len(array_list)
            num_arrays += array_len - len([i for i in range(array_len) if i in skip])
        elif 0 not in skip:
            num_arrays += 1

    #Upscale each array
    Message('Upscaling arrays to {}x{}...'.format(target_resolution[0], target_resolution[1]))
    processed = 0
    output = []
    for resolution, array_list in get_items(arrays):

        if not isinstance(array_list, (list, tuple)):
            array_list = [array_list]
            
        for i, array in enumerate(array_list):
            if i in skip:
                continue
            processed += 1
            Message('Processing array for {}x{} ({}/{})'.format(resolution[0], resolution[1], processed, num_arrays))
            zoom_factor = (target_resolution[1] / resolution[1],
                           target_resolution[0] / resolution[0])
            upscaled = upscale(array, zoom_factor)
            output.append(upscaled)
    return output


def arrays_to_heatmap(numpy_arrays, gaussian_size, clip):
    """Convert list of arrays into a heatmap.
    The stages and values are chosen with trial and error, 
    so this function is still open to improvement.
    """
    
    #Add all arrays together
    Message('Merging arrays...')
    merged_arrays = numpy.merge(numpy_arrays, 'add', 'float64')
    
    #Set to constant values
    Message('Flattening values...')
    flattened = numpy.remap_to_range(merged_arrays)
    
    #Blur the array
    if gaussian_size:
        Message('Applying gaussian blur...')
        heatmap = blur(flattened, gaussian_size)
    else:
        heatmap = flattened
    
    Message('Finding range limits...')
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
    
    return Image.fromarray(colour_range.convert_to_rgb(max_array))