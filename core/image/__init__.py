from __future__ import division, absolute_import
from multiprocessing import Process, Queue, cpu_count
from PIL import Image
import sys

from core.image._numpy import numpy_merge, numpy_array, numpy_power, numpy_sum
from core.image._scipy import blur, upscale
from core.image.keyboard import DrawKeyboard
from core.image.colours import ColourRange, ColourMap
from core.compatibility import range, get_items, _print
from core.config import CONFIG, _config_defaults
from core.constants import format_file_path
from core.files import load_program


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
        print 'Got result from process {}.'.format(data[0] + 1)
    
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


class ImageName(object):
    """Generate an image name using values defined in the config.
    Not implemented yet: creation time | modify time | exe name
    """
    def __init__(self, program_name):
        self.name = program_name.replace('\\', '').replace('/', '')
        self.reload()

    def reload(self):
        self.output_res_x = str(CONFIG['GenerateImages']['OutputResolutionX'])
        self.output_res_y = str(CONFIG['GenerateImages']['OutputResolutionY'])
        self.upscale_res_x = str(CONFIG['GenerateImages']['_UpscaleResolutionX'])
        self.upscale_res_y = str(CONFIG['GenerateImages']['_UpscaleResolutionY'])

        self.heatmap_gaussian = str(CONFIG['GenerateHeatmap']['GaussianBlurSize'])
        self.heatmap_exp = str(CONFIG['GenerateHeatmap']['ExponentialMultiplier'])
        self.heatmap_colour = str(CONFIG['GenerateHeatmap']['ColourProfile'])
        self.heatmap_buttons = {'LMB': CONFIG['GenerateHeatmap']['_MouseButtonLeft'],
                                'MMB': CONFIG['GenerateHeatmap']['_MouseButtonMiddle'],
                                'RMB': CONFIG['GenerateHeatmap']['_MouseButtonRight']}

        self.track_colour = str(CONFIG['GenerateTracks']['ColourProfile'])

        self.keyboard_colour = str(CONFIG['GenerateKeyboard']['ColourProfile'])

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
            
        elif image_type.lower() == 'keyboard':
            name = CONFIG['GenerateKeyboard']['NameFormat']
            name = name.replace('[ColourProfile]', self.keyboard_colour)
        
        else:
            raise ValueError('incorred image type: {}, '
                             'must be tracks, clicks or keyboard'.format(image_type))
        name = name.replace('[UResX]', self.upscale_res_x)
        name = name.replace('[UResY]', self.upscale_res_y)
        name = name.replace('[ResX]', self.output_res_x)
        name = name.replace('[ResY]', self.output_res_y)
        name = name.replace('[Name]', self.name)

        #Replace invalid characters
        invalid_chars = ':*?"<>|'
        for char in invalid_chars:
            if char in name:
                name = name.replace(char, '')
        
        return '{}.{}'.format(format_file_path(name), CONFIG['GenerateImages']['FileType'])


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
        if image_type not in ('tracks', 'clicks', 'keyboard'):
            raise ValueError('image type \'{}\' not supported'.format(image_type))
        
        session_start = self.data['Ticks']['Session']['Current'] if last_session else None
        if not self.data['Ticks']['Total']:
            image_output = None
        
        else:
            
            high_precision = CONFIG['GenerateImages']['HighPrecision']
            allow_resize = True
            
            #Generate mouse tracks image
            if image_type == 'tracks':
                (min_value, max_value), numpy_arrays = merge_resolutions(self.data['Maps']['Tracks'], 
                                                                         session_start=session_start,
                                                                         high_precision=high_precision)
                try:
                    colour_map = ColourMap()[CONFIG['GenerateTracks']['ColourProfile']]
                except ValueError:
                    default_colours = _config_defaults['GenerateTracks']['ColourProfile'][0]
                    colour_map = ColourMap()[default_colours]
                colour_range = ColourRange(min_value, max_value, colour_map)
                image_output = arrays_to_colour(colour_range, numpy_arrays)
                image_name = self.name.generate('Tracks', reload=True)
            
            #Generate click heatmap image
            elif image_type == 'clicks':
                lmb = CONFIG['GenerateHeatmap']['_MouseButtonLeft']
                mmb = CONFIG['GenerateHeatmap']['_MouseButtonMiddle']
                rmb = CONFIG['GenerateHeatmap']['_MouseButtonRight']
                mb = [i for i, v in enumerate((lmb, mmb, rmb)) if v]
                clicks = self.data['Maps']['Clicks']
                numpy_arrays = merge_resolutions(self.data['Maps']['Clicks'], multiple_selection=mb, 
                                                 session_start=session_start, _find_range=False,
                                                 high_precision=high_precision)

                (min_value, max_value), heatmap = arrays_to_heatmap(numpy_arrays,
                            gaussian_size=CONFIG['GenerateHeatmap']['GaussianBlurSize'],
                            exponential_multiplier=CONFIG['GenerateHeatmap']['ExponentialMultiplier'])
                
                #Adjust range of heatmap            
                if CONFIG['GenerateHeatmap']['ForceMaximumValue']:
                    max_value = CONFIG['GenerateHeatmap']['ForceMaximumValue']
                    _print('Manually set highest range to {}'.format(max_value))
                else:
                    max_value *= CONFIG['GenerateHeatmap']['MaximumValueMultiplier']
                
                #Convert each point to an RGB tuple
                _print('Converting to RGB...')
                try:
                    colour_map = ColourMap()[CONFIG['GenerateHeatmap']['ColourProfile']]
                except ValueError:
                    default_colours = _config_defaults['GenerateHeatmap']['ColourProfile'][0]
                    colour_map = ColourMap()[default_colours]
                colour_range = ColourRange(min_value, max_value, colour_map)
                image_output = Image.fromarray(convert_to_rgb(heatmap, colour_range))
              
              
                image_name = self.name.generate('Clicks', reload=True)
            
            elif image_type == 'keyboard':
                allow_resize = False
                kb = DrawKeyboard(self.profile, self.data, last_session=last_session)
                image_output = kb.draw_image()
                image_name = self.name.generate('Keyboard', reload=True)
            
        resolution = (CONFIG['GenerateImages']['OutputResolutionX'],
                      CONFIG['GenerateImages']['OutputResolutionY'])
            
        if image_output is None:
            _print('No image data was found for type "{}"'.format(image_type))
        else:
            if allow_resize:
                image_output = image_output.resize(resolution, Image.ANTIALIAS)
            if save_image:
                _print('Saving image...')
                image_output.save(image_name)
                _print('Finished saving.')
        return image_output
