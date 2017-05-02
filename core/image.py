from __future__ import division
import numpy as np
from scipy.ndimage.interpolation import zoom

from constants import CONFIG, COLOURS_MAIN, COLOUR_MODIFIERS


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


class ImageName(object):
    """Generate an image name using values defined in the config.
    Not implemented yet: creation time | modify time | exe name
    """
    def __init__(self):
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

    def generate(self, program_name, image_type):
        if image_type.lower() == 'heatmap':
            name = CONFIG.data['GenerateHeatmap']['NameFormat']
            name = name.replace('[ExpMult]', self.heatmap_exp)
            name = name.replace('[GaussianSize]', self.heatmap_gaussian)
            name = name.replace('[ColourProfile]', self.heatmap_colour)
        elif image_type.lower() == 'tracks':
            name = CONFIG.data['GenerateTracks']['NameFormat']
            name = name.replace('[ColourProfile]', self.track_colour)
        else:
            raise ValueError('incorred image type, must be "tracks" or "heatmap"')
        name = name.replace('[UResX]', self.upscale_res_x)
        name = name.replace('[UResY]', self.upscale_res_y)
        name = name.replace('[ResX]', self.output_res_x)
        name = name.replace('[ResY]', self.output_res_y)
        name = name.replace('[FriendlyName]', program_name)

        #Replace invalid characters
        invalid_chars = ':*?"<>|'
        for char in invalid_chars:
            if char in name:
                name = name.replace(char, '')
        
        return '{}.png'.format(name)


def parse_colour_text(colour_name):
    """Convert text into a colour map.
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


class ColourMap(object):
    """Look up default colours or generate one if the set doesn't exist."""
    _MAIN = {
        'heatmap': (
            (0, 0, 0), (0, 0, 127), (0, 0, 255), (0, 63, 255),
            (0, 127, 255), (0, 191, 255), (63, 255, 191),
            (127, 255, 127), (191, 255, 63), (255, 255, 0),
            (255, 127, 0), (255, 63, 0), (255, 0, 0)
        )
    }
    def __getitem__(self, colour_profile):
        if colour_profile.lower() in self._MAIN:
            return self._MAIN[colour_profile.lower()]
        else:
            generated_map = parse_colour_text(colour_profile)
            if generated_map:
                return generated_map
            else:
                raise ValueError('unknown colour map')
