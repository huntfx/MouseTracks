from __future__ import division
from PIL import Image
from scipy.ndimage.interpolation import zoom
from scipy.ndimage.filters import gaussian_filter
import sys
import numpy as np

from core.constants import CONFIG, COLOURS_MAIN, COLOUR_MODIFIERS
from core.files import load_program
from core.simple import format_file_path
from core.functions import ColourRange, print_override
from core.simple import get_items

if sys.version_info.major == 2:
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


def merge_resolutions(main_data, interpolate=True, multiple=False, session_start=None):
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
    """Turn each element in a 2D array to its corresponding colour."""
    
    height_range = range(len(image_array))
    width_range = range(len(image_array[0]))
    
    new_data = [[]]
    total = len(image_array) * len(image_array[0])
    count = 0
    one_percent = int(round(total / 100))
    last_percent = -1
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
        self.heatmap_buttons = {'LMB': CONFIG['GenerateHeatmap']['MouseButtonLeft'],
                                'MMB': CONFIG['GenerateHeatmap']['MouseButtonMiddle'],
                                'RMB': CONFIG['GenerateHeatmap']['MouseButtonRight']}

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


def parse_colour_text(colour_name):
    """Convert text into a colour map.
    It could probably do with a rewrite to make it more efficient,
    as it was first written to only use capitals.

    Mixed Colour:
        Combine multiple colours.
        Examples: BlueRed, BlackYellowGreen
    Modified Colour:
        Apply a modification to a colour.
        If multiple ones are applied, they will work in reverse order.
        Light and dark are not opposites so will not cancel each other out.
        Examples: LightBlue, DarkLightYellow
    Transition:
        This ends the current colour mix and starts a new one.
        Examples: BlackToWhite, RedToGreenToBlue
    Any number of these features can be combined together to create different effects.
        
    As an example, here are the values that would result in the heatmap:
        BlackToDarkBlueToBlueToCyanBlueBlueBlueToCyanBlueToCyan
        + CyanCyanBlueToCyanCyanCyanYellowToCyanYellowToCyan
        + YellowYellowYellowToYellowToOrangeToRedOrangeToRed 
    """
    colours = {'Final': [],
               'Temp': [],
               'Mult': []}
    word = ''
    i = 0
    
    #Loop letters until end of word has been reached
    while True:
        done_stuff = False
        skip = False
        try:
            letter = colour_name[i]
        except IndexError:
            try:
                letter = colour_name[i - 1]
            except IndexError:
                break
            skip = True

        if letter in 'abcdefghijklmnopqrstuvwxyz':
            word += letter
            done_stuff = True

        word_colours = word in COLOURS_MAIN
        word_mods = word in COLOUR_MODIFIERS
        word_to = word == 'to'
        
        #Build colours
        if skip or word_colours or word_mods or word_to or letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            
            if word_mods:
                colours['Mult'].append(COLOUR_MODIFIERS[word])
            elif word_colours:
                colours['Temp'].append(list(COLOURS_MAIN[word]))

                #Apply modifiers
                for mult in colours['Mult'][::-1]:
                    alpha = colours['Temp'][-1].pop()
                    colours['Temp'][-1] = [mult[0] + mult[1] * c for c in colours['Temp'][-1]]
                    colours['Temp'][-1] += [min(255, alpha * mult[2])]
                colours['Mult'] = []

            #Merge colours together
            if word_to or skip:
                num_colours = len(colours['Temp'])
                joined_colours = tuple(sum(c) / num_colours for c in zip(*colours['Temp']))
                colours['Final'].append(joined_colours)
                colours['Temp'] = []
                
            if not done_stuff:
                word = letter.lower()
            else:
                word = ''
            done_stuff = True
                
        i += 1
        if not done_stuff:
            raise ValueError('invalid characters in colour map')
    return tuple(colours['Final'])


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
    def __init__(self, profile):
        self.profile = profile
        self.data = load_program(profile, _update_version=False)
        self.name = ImageName(profile)

    def generate(self, image_type, last_session=False):
        image_type = image_type.lower()
        if image_type not in ('tracks', 'clicks'):
            raise ValueError('image type must be given as either tracks or clicks')
        
        session_start = self.data['Ticks']['Session']['Current'] if last_session else None
        
        if not self.data['Ticks']['Total']:
            image_output = None
        
        else:
            if image_type == 'tracks':
                value_range, numpy_arrays = merge_resolutions(self.data['Maps']['Tracks'], interpolate=True, 
                                                              session_start=session_start)
                colour_map = CONFIG['GenerateTracks']['ColourProfile']
                colour_range = ColourRange(value_range[0], value_range[1], ColourMap()[colour_map])
                image_output = arrays_to_colour(colour_range, numpy_arrays)
                image_name = self.name.generate('Tracks', reload=True)
                
            elif image_type == 'clicks':
                lmb = CONFIG['GenerateHeatmap']['MouseButtonLeft']
                mmb = CONFIG['GenerateHeatmap']['MouseButtonMiddle']
                rmb = CONFIG['GenerateHeatmap']['MouseButtonRight']
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
            print_override('Saving image...')
            image_output.save(image_name)
            print_override('Finished saving.')


class ColourMap(object):
    """Look up default colours or generate one if the set doesn't exist."""
    _MAPS = {
        'jet': ('BlackToDarkBlueToBlueToCyanBlueBlueBlueToCyanBlueTo'
                'CyanCyanCyanBlueToCyanCyanCyanYellowToCyanYellowTo'
                'CyanYellowYellowYellowToYellowToOrangeToRedOrangeToRed'),
        'transparentjet': ('TransparentBlackToTranslucentTranslucentDarkBlueTo'
                           'TranslucentBlueToTranslucentCyanTranslucentBlueBlueBlueTo'
                           'CyanBlueToCyanCyanCyanBlueToCyanCyanCyanYellowToCyanYellow'
                           'ToCyanYellowYellowYellowToYellowToOrangeToRedOrangeToRed'),
        'radiation': 'BlackToRedToYellowToWhiteToWhiteWhiteWhiteLightLightGrey',
        'transparentradiation': ('TransparentBlackToTranslucentRedToYellowTo'
                                 'WhiteToWhiteWhiteWhiteLightLightGrey'),
        'default': 'WhiteToBlack',
        'citrus': 'BlackToDarkDarkGreyToDarkGreenToYellow',
        'ice': 'BlackToDarkBlueToDarkBlueLightDarkCyanToLightBlueDarkCyanToWhite',
        'neon': 'BlackToPurpleToPinkToBlackToPink',
        'sunburst': 'DarkDarkGrayToOrangeToBlackToOrangeToYellow',
        'demon': 'WhiteToRedToBlackToWhite',
        'chalk': 'BlackToWhite',
        'lightning': 'DarkPurpleToLightMagentaToLightGrayToWhiteToWhite',
        'hazard': 'WhiteToBlackToYellow',
        'razer': 'BlackToDarkGreyToBlackToDarkGreenToGreenToBlack',
        'sketch': 'LightGreyToBlackToDarkPurpleToWhiteToLightGreyToBlackToBlue',
        'grape': 'WhiteToBlackToMagenta',
        'spiderman': 'RedToBlackToWhite',
        'shroud': 'GreyToBlackToLightPurple',
        'blackwidow': 'PurpleToLightCyanWhiteToPurpleToBlack'
    }
    def __getitem__(self, colour_profile):
        if colour_profile.lower() in self._MAPS:
            return parse_colour_text(self._MAPS[colour_profile.lower()])
        else:
            generated_map = parse_colour_text(colour_profile)
            if generated_map:
                if len(generated_map) < 2:
                    raise ValueError('not enough colours to generate colour map')
                return generated_map
            else:
                raise ValueError('unknown colour map')
