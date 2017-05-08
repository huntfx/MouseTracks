from __future__ import division
import numpy as np
from scipy.ndimage.interpolation import zoom
from scipy.ndimage.filters import gaussian_filter
from PIL import Image

from constants import CONFIG, COLOURS_MAIN, COLOUR_MODIFIERS
from functions import ColourRange
from files import load_program

def merge_array_max(arrays):
    array_len = len(arrays)
    if not array_len:
        return None
    elif array_len > 1:
        return np.maximum.reduce(arrays)
    else:
        return arrays[0]


def merge_array_add(arrays):
    array_len = len(arrays)
    if not array_len:
        return None
    elif array_len > 1:
        return np.add.reduce(arrays)
    else:
        return arrays[0]


def merge_resolutions(main_data, max_resolution=None, interpolate=True, average=False):
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
    count = 0
    total = 0
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
                count += 1
                try:
                    new_data[-1].append(data[(x, y)])
                    total += data[(x, y)]
                except KeyError:
                    new_data[-1].append(0)

        #Calculate the zoom level needed
        if max_resolution != current_resolution:
            zoom_factor = (max_resolution[1] / current_resolution[1],
                           max_resolution[0] / current_resolution[0])
            
            numpy_arrays.append(zoom(np.array(new_data), zoom_factor, order=interpolate))
        else:
            numpy_arrays.append(np.array(new_data))
            
    if average:
        highest_value = int(12 * total / count)
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


class ImageName(object):
    """Generate an image name using values defined in the config.
    Not implemented yet: creation time | modify time | exe name
    """
    def __init__(self, program_name):
        self.name = program_name
        self.reload()

    def reload(self):
        self.output_res_x = str(CONFIG.data['GenerateImages']['OutputResolutionX'])
        self.output_res_y = str(CONFIG.data['GenerateImages']['OutputResolutionY'])
        self.upscale_res_x = str(CONFIG.data['GenerateImages']['UpscaleResolutionX'])
        self.upscale_res_y = str(CONFIG.data['GenerateImages']['UpscaleResolutionY'])

        self.heatmap_gaussian = str(CONFIG.data['GenerateHeatmap']['GaussianBlurSize'])
        self.heatmap_exp = str(CONFIG.data['GenerateHeatmap']['ExponentialMultiplier'])
        self.heatmap_colour = str(CONFIG.data['GenerateHeatmap']['ColourProfile'])

        self.track_colour = str(CONFIG.data['GenerateTracks']['ColourProfile'])

        self.speed_colour = str(CONFIG.data['GenerateSpeedMap']['ColourProfile'])

        self.combined_colour = str(CONFIG.data['GenerateCombined']['ColourProfile'])

    def generate(self, image_type):
        if image_type.lower() == 'clicks':
            name = CONFIG.data['GenerateHeatmap']['NameFormat']
            name = name.replace('[ExpMult]', self.heatmap_exp)
            name = name.replace('[GaussianSize]', self.heatmap_gaussian)
            name = name.replace('[ColourProfile]', self.heatmap_colour)
        elif image_type.lower() == 'tracks':
            name = CONFIG.data['GenerateTracks']['NameFormat']
            name = name.replace('[ColourProfile]', self.track_colour)
        elif image_type.lower() == 'speed':
            name = CONFIG.data['GenerateSpeedMap']['NameFormat']
            name = name.replace('[ColourProfile]', self.speed_colour)
        elif image_type.lower() == 'combined':
            name = CONFIG.data['GenerateCombined']['NameFormat']
            name = name.replace('[ColourProfile]', self.combined_colour)
        else:
            raise ValueError('incorred image type: {}, '
                             'must be tracks, heatmap or speed'.format(image_type))
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
        
        return '{}.{}'.format(name, CONFIG.data['GenerateImages']['FileType'])


def parse_colour_text(colour_name):
    """Convert text into a colour map.
    It could probably do with a rewrite to make it more efficient.

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
        ... CyanCyanBlueToCyanCyanCyanYellowToCyanYellowToCyan
        ... YellowYellowYellowToYellowToOrangeToRedOrangeToRed 
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
                colours['Temp'].append(COLOURS_MAIN[word])

                #Apply modifiers
                for mult in colours['Mult'][::-1]:
                    colours['Temp'][-1] = [mult[0] + mult[1] * c for c in colours['Temp'][-1]]
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
    print 'Merging arrays...'
    max_array = merge_array_add(numpy_arrays)
    if max_array is None:
        return None

    #Create a new numpy array and copy over the values
    #I'm not sure if there's a way to skip this step since it seems a bit useless
    print 'Converting to heatmap...'
    h = len(max_array)
    w = len(max_array[0])
    heatmap = np.zeros(h * w).reshape((h, w))
    height_range = range(h)
    width_range = range(w)
    exponential_multiplier = CONFIG.data['GenerateHeatmap']['ExponentialMultiplier']
    for x in width_range:
        for y in height_range:
            heatmap[y][x] = max_array[y][x] ** exponential_multiplier

    #Blur the array
    print 'Applying gaussian blur...'
    gaussian_blur = CONFIG.data['GenerateHeatmap']['GaussianBlurSize']
    heatmap = gaussian_filter(heatmap, sigma=gaussian_blur)

    #This part is temporary until the ColourRange function is fixed
    heatmap *= 1000000

    #Calculate the average of all the points
    print 'Calculating average...'
    total = [0, 0]
    for x in width_range:
        for y in height_range:
            total[0] += 1
            total[1] += heatmap[y][x]

    #Set range of heatmap
    min_value = 0
    max_value = 10 * total[1] / total[0]
    if CONFIG.data['GenerateHeatmap']['SetMaxRange']:
        max_value = CONFIG.data['GenerateHeatmap']['SetMaxRange']
        print 'Manually set highest range to {}'.format(max_value)
    
    #Convert each point to an RGB tuple
    print 'Converting to RGB...'    
    colour_map = CONFIG.data['GenerateHeatmap']['ColourProfile']
    colour_range = ColourRange(max_value - min_value, ColourMap()[colour_map])
    return Image.fromarray(convert_to_rgb(heatmap, colour_range))


def arrays_to_colour(value_range, numpy_arrays, image_type):
    image_type = image_type.lower()
    if image_type not in ('tracks', 'speed', 'combined'):
        raise ValueError('image type must be given as either tracks, speed or combined')
    elif image_type == 'tracks':
        colour_map = CONFIG.data['GenerateTracks']['ColourProfile']
    elif image_type == 'speed':
        colour_map = CONFIG.data['GenerateSpeedMap']['ColourProfile']
    elif image_type == 'combined':
        colour_map = CONFIG.data['GenerateCombined']['ColourProfile']

    max_array = merge_array_max(numpy_arrays)
    if max_array is None:
        return None
    colour_range = ColourRange(value_range[1] - value_range[0], ColourMap()[colour_map])
    return Image.fromarray(convert_to_rgb(max_array, colour_range))


class RenderImage(object):
    def __init__(self, profile):
        self.profile = profile
        self.data = load_program(profile)
        self.name = ImageName(profile)

    def generate(self, image_type):
        image_type = image_type.lower()
        if image_type not in ('tracks', 'speed', 'clicks', 'combined'):
            raise ValueError('image type must be given as either tracks, speed, clicks or combined')
        
        if image_type == 'tracks':
            value_range, numpy_arrays = merge_resolutions(self.data['Tracks'])
            image_output = arrays_to_colour(value_range, numpy_arrays, 'Tracks')
            image_name = self.name.generate('Tracks')
        elif image_type == 'speed':
            value_range, numpy_arrays = merge_resolutions(self.data['Speed'], average=True)
            image_output = arrays_to_colour(value_range, numpy_arrays, 'Speed')
            image_name = self.name.generate('Speed')
        elif image_type == 'clicks':
            value_range, numpy_arrays = merge_resolutions(self.data['Clicks'])
            image_output = _click_heatmap(numpy_arrays)
            image_name = self.name.generate('Clicks')
        elif image_type == 'combined':
            value_range, numpy_arrays = merge_resolutions(self.data['Combined'], average=True)
            image_output = arrays_to_colour(value_range, numpy_arrays, 'Combined')
            image_name = self.name.generate('Combined')
        resolution = (CONFIG.data['GenerateImages']['OutputResolutionX'],
                      CONFIG.data['GenerateImages']['OutputResolutionY'])
        if image_output is None:
            print 'No image data for type "{}"'.format(image_type)
        else:
            image_output = image_output.resize(resolution, Image.ANTIALIAS)
            print 'Saving image...'
            image_output.save(image_name)
            print 'Finished saving.'


class ColourMap(object):
    """Look up default colours or generate one if the set doesn't exist."""
    _MAPS = {
        'heatmap': ('BlackToDarkBlueToBlueToCyanBlueBlueBlueToCyanBlueTo'
                    'CyanCyanCyanBlueToCyanCyanCyanYellowToCyanYellowTo'
                    'CyanYellowYellowYellowToYellowToOrangeToRedOrangeToRed'),
        'default': 'WhiteToBlack',
        'citrus': 'BlackToDarkDarkGreyToDarkGreenToYellow',
        'ice': 'BlackToDarkBlueToDarkBlueLightDarkCyanToLightBlueDarkCyanToWhite',
        'neon': 'BlackToPurpleToPinkToBlackToPink',
        'sunburst': 'DarkDarkGrayToOrangeToBlackToOrangeToYellow',
        'demon': 'WhiteToRedToBlackToWhite',
        'chalk': 'BlackBlackToWhite',
        'lightning': 'DarkPurpleToLightMagentaToLightGrayToWhiteToWhite',
        'hazard': 'WhiteToBlackToYellow',
        'razer': 'BlackToDarkGreyToBlackToDarkGreenToGreenToBlack',
        'sketch': 'LightGreyToBlackToDarkPurpleToWhiteToLightGreyToBlackToBlue',
        'grape': 'WhiteToBlackToMagenta'
    }
    def __getitem__(self, colour_profile):
        if colour_profile.lower() in self._MAPS:
            return parse_colour_text(self._MAPS[colour_profile.lower()])
        else:
            generated_map = parse_colour_text(colour_profile)
            if generated_map:
                return generated_map
            else:
                raise ValueError('unknown colour map')
