"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Image functions that require complicated or heavy processing

from __future__ import absolute_import, division

from operator import itemgetter
from collections import defaultdict
from multiprocessing import Process, Queue, cpu_count
from PIL import Image

from .scipy import blur, upscale
from ..utils import numpy
from ..config.settings import CONFIG
from ..config.language import LANGUAGE
from ..utils.compatibility import range, iteritems, Message
from ..utils.maths import round_int


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
    """Calculate the correct resolution."""

    #Find output resultion
    _res_x = CONFIG['GenerateImages']['OutputResolutionX']
    _res_y = CONFIG['GenerateImages']['OutputResolutionY']
    use_custom_res = (output_resolution is None or not CONFIG['GenerateImages']['AutomaticResolution']) and (_res_x or _res_y)
    
    if use_custom_res:

        #Find aspect ratio if any resolution is unset
        if not _res_x or not _res_y:
            aspects = defaultdict(int)
            for x, y in resolutions:
                aspects[round(x/y, 2)] += 1
            
            #Get most common aspect ratio, and find average if multiple
            max_value = sorted(iteritems(aspects), key=itemgetter(1))[-1][-1]
            max_aspects = [k for k, v in iteritems(aspects) if v == max_value]
            aspect = sum(max_aspects) / len(max_aspects)

            #Calculate the unset resolution
            if not _res_x:
                _res_x = round_int(_res_y * aspect)
            else:
                _res_y = round_int(_res_x / aspect)

        output_resolution = (_res_x, _res_y)

    #Calculate upscaling resolution
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
    
    #Force the upscale resolution to be lower if a lower resolution is requested
    if use_custom_res and (_res_x * 2 < max_resolution[0] or _res_y * 2 < max_resolution[1]):
        max_resolution = (_res_x * 2, _res_y * 2)

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
    for resolution, array_list in iteritems(arrays):
        if isinstance(array_list, (list, tuple)):
            array_len = len(array_list)
            num_arrays += array_len - len([i for i in range(array_len) if i in skip])
        elif 0 not in skip:
            num_arrays += 1

    #Upscale each array
    LANGUAGE.strings['Generation']['UpscaleArrayStart'].format_custom(XRES=target_resolution[0], YRES=target_resolution[1])
    processed = 0
    output = []
    for resolution, array_list in iteritems(arrays):

        if not isinstance(array_list, (list, tuple)):
            array_list = [array_list]
            
        for i, array in enumerate(array_list):
            if i in skip:
                continue
            processed += 1
            Message(LANGUAGE.strings['Generation']['UpscaleArrayProgress'].format_custom(XRES=resolution[0], YRES=resolution[1],
                                                                                CURRENT=processed, TOTAL=num_arrays))
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
    Message(LANGUAGE.strings['Generation']['ArrayMerge'])
    merged_arrays = numpy.merge(numpy_arrays, 'add', 'float64')
    
    #Set to constant values
    Message(LANGUAGE.strings['Generation']['ArrayRemap'])
    flattened = numpy.remap_to_range(merged_arrays)
    
    #Blur the array
    if gaussian_size:
        Message(LANGUAGE.strings['Generation']['ArrayBlur'])
        heatmap = blur(flattened, gaussian_size)
    else:
        heatmap = flattened
    
    Message(LANGUAGE.strings['Generation']['ArrayRange'])
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