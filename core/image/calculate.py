from __future__ import division, absolute_import
from multiprocessing import Process, Queue, cpu_count
from PIL import Image

from core.image._numpy import numpy_merge, numpy_array, numpy_power, numpy_sum
from core.image._scipy import blur, upscale
from core.compatibility import range, _print
from core.config import CONFIG


def merge_resolutions(main_data, multiple_selection=False, 
                      session_start=None, high_precision=False, _find_range=True):
    """Upscale each resolution to make them all match.
    A list of arrays and range of data will be returned.
    """
    
    numpy_arrays = []
    highest_value = None
    lowest_value = None
    resolutions = main_data.keys()

    if any(not isinstance(i, tuple) for i in resolutions) or any(len(i) != 2 for i in resolutions):
        raise ValueError('incorrect resolutions')

            
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
        if multiple_selection:
            max_count += len([n for n in main_data[current_resolution] if n])
        else:
            max_count += 1
    
    i = 0
    count = 0
    total = 0
    
    #Upscale each resolution to the same level
    for current_resolution in resolutions:
        if multiple_selection:
            array_list = [main_data[current_resolution][n] 
                          for n in multiple_selection if main_data[current_resolution][n]]
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

            #Try find the highest and lowest value
            if _find_range:
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
                        value = data[(x, y)]
                        if session_start is not None:
                            value = max(0, value - session_start)
                        new_data[-1].append(value)
                        total += value
                    except KeyError:
                        new_data[-1].append(0)
                    else:
                        count += 1

            #Calculate the zoom level needed
            zoom_factor = (max_resolution[1] / current_resolution[1],
                           max_resolution[0] / current_resolution[0])
            numpy_arrays.append(upscale(numpy_array(new_data), zoom_factor))
    
    if _find_range:
        if session_start is not None:
            highest_value -= session_start
        return (lowest_value, highest_value), numpy_arrays
    return numpy_arrays
    
    
def convert_to_rgb(image_array, colour_range):
    """Convert an array into colours."""
    
    #Calculate how many processes to use
    num_processes = CONFIG['GenerateImages']['AllowedCores']
    max_cores = cpu_count()
    if not 0 < num_processes <= max_cores:
        _print('Splitting up data for each process...')
        num_processes = max_cores
        
    if num_processes == 1:
        return _rgb_process_single(image_array, colour_range)
    
    p = range(num_processes)
    
    #Get actual image dimensions
    height = len(image_array)
    width = len(image_array[0])
    
    #Figure how to split for each process
    width_range = range(width)
    height_per_process = height // num_processes
    heights = [[i * height_per_process, (i + 1) * height_per_process] 
               for i in range(num_processes)]
    
    #Setup the queue and send it to each process
    q_send = Queue()
    q_recv = Queue()
    for i in p:
        height_range = range(heights[i][0], heights[i][1])
        q_send.put((i, width_range, height_range, colour_range, image_array))
        
        Process(target=_rgb_process_worker, args=(q_send, q_recv)).start()
        _print('Started process {}.'.format(i + 1))
    
    _print('Waiting for processes to finish...')
    
    #Wait for the results to come back
    result_data = {}
    for i in p:
        data = q_recv.get()
        result_data[data[0]] = data[1]
        _print('Got result from process {}.'.format(data[0] + 1))
    
    #Join results
    results = []
    for i in p:
        results += result_data[i]
    
    return numpy_array(results, dtype='uint8')

    
def _rgb_process_worker(q_recv, q_send):
    """Turn each element in a 2D array to its corresponding colour.
    This is a shortened version of _rgb_process_single meant for multiprocessing.
    """
    i, width_range, height_range, colour_range, image_array = q_recv.get()
    result = [[]]
    for y in height_range:
        if result[-1]:
            result.append([])
        for x in width_range:
            result[-1].append(colour_range[image_array[y][x]])
    q_send.put((i, result))
    
    
def _rgb_process_single(image_array, colour_range):
    """Turn each element in a 2D array to its corresponding colour."""
    
    height_range = range(len(image_array))
    width_range = range(len(image_array[0]))
    
    new_data = [[]]
    total = len(image_array) * len(image_array[0])
    count = 0
    one_percent = int(round(total / 100))
    for y in height_range:
        if new_data[-1]:
            new_data.append([])
        for x in width_range:
            new_data[-1].append(colour_range[image_array[y][x]])
            count += 1
            if not count % one_percent:
                _print('{}% complete ({} pixels)'.format(int(round(100 * count / total)), count))
            
    return numpy_array(new_data, dtype='uint8')


def arrays_to_heatmap(numpy_arrays, gaussian_size, exponential_multiplier=1.0):
    """Convert list of arrays into a heatmap."""
    #Add all arrays together
    _print('Merging arrays...')
    max_array = numpy_power(numpy_merge(numpy_arrays, 'add'), exponential_multiplier, dtype='float64')
    if max_array is None:
        return None

    #Blur the array
    _print('Applying gaussian blur...')            
    heatmap = blur(max_array, gaussian_size)

    #Calculate the average of all the points
    _print('Calculating average...')
    average = numpy_sum(heatmap) / heatmap.size
    
    return ((0, average), heatmap)


def arrays_to_colour(colour_range, numpy_arrays):
    """Convert an array of floats or integers into an image object."""

    max_array = numpy_merge(numpy_arrays, 'max')
    if max_array is None:
        return None
    
    return Image.fromarray(convert_to_rgb(max_array, colour_range))
