from __future__ import division, absolute_import
from multiprocessing import Process, Queue, cpu_count
from PIL import Image
from scipy.ndimage.interpolation import zoom
from scipy.ndimage.filters import gaussian_filter
import sys
import numpy as np

from core.colours import ColourRange, ColourMap
from core.config import CONFIG
from core.files import load_program
from core.basic import format_file_path, get_items, get_python_version
from core.misc import print_override

if get_python_version() == 2:
    range = xrange
    

def merge_array_max(arrays):
    """Find the maximum values of different arrays."""
    array_len = len(arrays)
    if not array_len:
        return None
    elif array_len > 1:
        return np.maximum.reduce(arrays)
    else:
        return arrays[0]


def merge_array_add(arrays):
    """Add the values of different arrays."""
    array_len = len(arrays)
    if not array_len:
        return None
    elif array_len > 1:
        return np.add.reduce(arrays)
    else:
        return arrays[0]


def merge_resolutions(main_data, interpolate=False, multiple=False, session_start=None):
    """Upscale each resolution to make them all match.
    A list of arrays and range of data will be returned.
    """
    
    numpy_arrays = []
    highest_value = None
    lowest_value = None
    resolutions = main_data.keys()

    if any(not isinstance(i, tuple) for i in resolutions) or any(len(i) != 2 for i in resolutions):
        raise ValueError('incorrect resolutions')

    #Calculate upscale resolution
    max_x = max(x for x, y in resolutions)
    max_y = max(y for x, y in resolutions)
    max_resolution = (CONFIG['GenerateImages']['UpscaleResolutionX'], CONFIG['GenerateImages']['UpscaleResolutionY'])
    CONFIG['GenerateImages']['UpscaleResolutionX'], CONFIG['GenerateImages']['UpscaleResolutionY'] = max_resolution
                      
    #Read total number of images that will need to be upscaled
    max_count = 0
    for current_resolution in resolutions:
        if multiple:
            max_count += len([n for n in main_data[current_resolution] if n])
        else:
            max_count += 1
    
    i = 0
    count = 0
    total = 0
    for current_resolution in resolutions:
        if multiple:
            array_list = [main_data[current_resolution][n] for n in multiple if main_data[current_resolution][n]]
        else:
            array_list = [main_data[current_resolution]]
            
        for data in array_list:
            i += 1
            print_override('Resizing {}x{} to {}x{}...'
                           '({}/{})'.format(current_resolution[0], current_resolution[1],
                                            max_resolution[0], max_resolution[1],
                                            i, max_count))

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
            if max_resolution != current_resolution:
                zoom_factor = (max_resolution[1] / current_resolution[1],
                               max_resolution[0] / current_resolution[0])
                
                numpy_arrays.append(zoom(np.array(new_data), zoom_factor, order=interpolate))
            else:
                numpy_arrays.append(np.array(new_data))
    
    if session_start is not None:
        highest_value -= session_start
    return (lowest_value, highest_value), numpy_arrays

    
def convert_to_rgb(image_array, colour_range):
    
    print_override('Splitting up data for each process...')
    
    #Calculate how many processes to use
    num_processes = CONFIG['GenerateImages']['AllowedCores']
    max_cores = cpu_count()
    if not 0 < num_processes <= 8:
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
        print_override('Started process {}.'.format(i + 1))
    
    print_override('Waiting for processes to finish...')
    
    #Wait for the results to come back
    result_data = {}
    for i in p:
        data = q_recv.get()
        result_data[data[0]] = data[1]
        print 'Got result from process {}.'.format(data[0] + 1)
    
    #Join results
    results = []
    for i in p:
        results += result_data[i]
    
    return np.array(results, dtype=np.uint8)

    
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
                print_override('{}% complete ({} pixels)'.format(int(round(100 * count / total)), count))
            
    return np.array(new_data, dtype=np.uint8)


class ImageName(object):
    """Generate an image name using values defined in the config.
    Not implemented yet: creation time | modify time | exe name
    """
    def __init__(self, program_name):
        self.name = program_name
        self.reload()

    def reload(self):
        self.output_res_x = str(CONFIG['GenerateImages']['OutputResolutionX'])
        self.output_res_y = str(CONFIG['GenerateImages']['OutputResolutionY'])
        self.upscale_res_x = str(CONFIG['GenerateImages']['UpscaleResolutionX'])
        self.upscale_res_y = str(CONFIG['GenerateImages']['UpscaleResolutionY'])

        self.heatmap_gaussian = str(CONFIG['GenerateHeatmap']['GaussianBlurSize'])
        self.heatmap_exp = str(CONFIG['GenerateHeatmap']['ExponentialMultiplier'])
        self.heatmap_colour = str(CONFIG['GenerateHeatmap']['ColourProfile'])
        self.heatmap_buttons = {'LMB': CONFIG['GenerateHeatmap']['_MouseButtonLeft'],
                                'MMB': CONFIG['GenerateHeatmap']['_MouseButtonMiddle'],
                                'RMB': CONFIG['GenerateHeatmap']['_MouseButtonRight']}

        self.track_colour = str(CONFIG['GenerateTracks']['ColourProfile'])

    def generate(self, image_type, reload=False):
    
        if reload:
            self.reload()
            
        if image_type.lower() == 'clicks':
            name = CONFIG['GenerateHeatmap']['NameFormat']
            name = name.replace('[ExpMult]', self.heatmap_exp)
            name = name.replace('[GaussianSize]', self.heatmap_gaussian)
            name = name.replace('[ColourProfile]', self.heatmap_colour)
            
            selected_buttons = [k for k, v in get_items(self.heatmap_buttons) if v]
            if all(self.heatmap_buttons.values()):
                name = name.replace('[MouseButtons]', 'Combined')
            elif len(selected_buttons) == 2:
                name = name.replace('[MouseButtons]', '+'.join(selected_buttons))
            elif len(selected_buttons) == 1:
                name = name.replace('[MouseButtons]', selected_buttons[0])
            else:
                name = name.replace('[MouseButtons]', 'Empty')

        elif image_type.lower() == 'tracks':
            name = CONFIG['GenerateTracks']['NameFormat']
            name = name.replace('[ColourProfile]', self.track_colour)
        else:
            raise ValueError('incorred image type: {}, '
                             'must be tracks or clicks'.format(image_type))
        name = name.replace('[UResX]', self.upscale_res_x)
        name = name.replace('[UResY]', self.upscale_res_y)
        name = name.replace('[ResX]', self.output_res_x)
        name = name.replace('[ResY]', self.output_res_y)
        name = name.replace('[FriendlyName]', self.name)

        #Replace invalid characters
        invalid_chars = ':*?"<>|'
        for char in invalid_chars:
            if char in name:
                name = name.replace(char, '')
        
        return '{}.{}'.format(format_file_path(name), CONFIG['GenerateImages']['FileType'])


def _click_heatmap(numpy_arrays):

    #Add all arrays together
    print_override('Merging arrays...')
    max_array = merge_array_add(numpy_arrays)
    if max_array is None:
        return None

    #Create a new numpy array and copy over the values
    #I'm not sure if there's a way to skip this step since it seems a bit useless
    print_override('Converting to heatmap...')
    h = len(max_array)
    w = len(max_array[0])
    heatmap = np.zeros(h * w).reshape((h, w))
    height_range = range(h)
    width_range = range(w)
    
    #Make this part a little faster for the sake of a few extra lines
    exponential_multiplier = CONFIG['GenerateHeatmap']['ExponentialMultiplier']
    if exponential_multiplier != 1.0:
        for x in width_range:
            for y in height_range:
                heatmap[y][x] = max_array[y][x] ** exponential_multiplier
    else:
        for x in width_range:
            for y in height_range:
                heatmap[y][x] = max_array[y][x]

    #Blur the array
    print_override('Applying gaussian blur...')
    gaussian_blur = CONFIG['GenerateHeatmap']['GaussianBlurSize']
    heatmap = gaussian_filter(heatmap, sigma=gaussian_blur)

    #Calculate the average of all the points
    print_override('Calculating average...')
    total = [0, 0]
    for x in width_range:
        for y in height_range:
            total[0] += 1
            total[1] += heatmap[y][x]

    #Set range of heatmap
    min_value = 0
    max_value = CONFIG['GenerateHeatmap']['MaximumValueMultiplier'] * total[1] / total[0]
    if CONFIG['GenerateHeatmap']['ForceMaximumValue']:
        max_value = CONFIG['GenerateHeatmap']['ForceMaximumValue']
        print_override('Manually set highest range to {}'.format(max_value))
    
    #Convert each point to an RGB tuple
    print_override('Converting to RGB...')    
    colour_map = CONFIG['GenerateHeatmap']['ColourProfile']
    colour_range = ColourRange(min_value, max_value, ColourMap()[colour_map])
    return Image.fromarray(convert_to_rgb(heatmap, colour_range))


def arrays_to_colour(colour_range, numpy_arrays):
    """Convert an array of floats or integers into an image object."""

    max_array = merge_array_max(numpy_arrays)
    if max_array is None:
        return None
    
    return Image.fromarray(convert_to_rgb(max_array, colour_range))


class RenderImage(object):
    def __init__(self, profile, data=None):
        self.profile = profile
        if data is None:
            self.data = load_program(profile, _update_version=False)
        else:
            self.data = data
        self.name = ImageName(profile)

    def generate(self, image_type, last_session=False, save_image=True):
        image_type = image_type.lower()
        if image_type not in ('tracks', 'clicks'):
            raise ValueError('image type must be given as either tracks or clicks')
        
        session_start = self.data['Ticks']['Session']['Current'] if last_session else None
        
        if not self.data['Ticks']['Total']:
            image_output = None
        
        else:
            if image_type == 'tracks':
                value_range, numpy_arrays = merge_resolutions(self.data['Maps']['Tracks'], 
                                                              session_start=session_start)
                colour_map = CONFIG['GenerateTracks']['ColourProfile']
                colour_range = ColourRange(value_range[0], value_range[1], ColourMap()[colour_map])
                image_output = arrays_to_colour(colour_range, numpy_arrays)
                image_name = self.name.generate('Tracks', reload=True)
                
            elif image_type == 'clicks':
                lmb = CONFIG['GenerateHeatmap']['_MouseButtonLeft']
                mmb = CONFIG['GenerateHeatmap']['_MouseButtonMiddle']
                rmb = CONFIG['GenerateHeatmap']['_MouseButtonRight']
                mb = [i for i, v in enumerate((lmb, mmb, rmb)) if v]
                value_range, numpy_arrays = merge_resolutions(self.data['Maps']['Clicks'], interpolate=False, multiple=mb,
                                                              session_start=session_start)
                image_output = _click_heatmap(numpy_arrays)
                image_name = self.name.generate('Clicks', reload=True)
            
            resolution = (CONFIG['GenerateImages']['OutputResolutionX'],
                          CONFIG['GenerateImages']['OutputResolutionY'])
                          
        if image_output is None:
            print_override('No image data was found for type "{}"'.format(image_type))
        else:
            image_output = image_output.resize(resolution, Image.ANTIALIAS)
            if save_image:
                print_override('Saving image...')
                image_output.save(image_name)
                print_override('Finished saving.')
        return image_output
