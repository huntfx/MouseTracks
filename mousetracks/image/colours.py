"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Colour handling for all images

from __future__ import absolute_import, division

from ..utils import numpy
from ..misc import TextFile, get_config_file
from ..utils.compatibility import Message, range, iteritems
from ..files import format_name
from ..utils.os import join_path


COLOUR_FILE = get_config_file('colours.txt')

MODIFIERS = {
    'light': {'ColourOffset': 128,
              'ColourShift': 1},
    'dark': {'ColourShift': 1},
    'transparent': {'AlphaShift': 8},
    'translucent': {'AlphaShift': 1},
    'opaque': {'AlphaShift': -1}
}

DUPLICATES = {
    'single': 1,
    'double': 2,
    'triple': 3,
    'quadruple': 4,
    'quintuple': 5,
    'pentuple': 5,
    'sextuple': 6,
    'hextuple': 6,
    'septuple': 7,
    'heptuple': 7,
    'octuple': 8,
    'nonuple': 9,
    'decuple': 10,
    'undecuple': 11,
    'hendecuple': 11,
    'duodecuple': 12,
    'tredecuple': 13
}

SEPERATORS = ['to', 'then']


class ColourRange(object):
    """Make a transition between colours.
    All possible colours within the range are cached for quick access.
    """
    
    def __init__(self, min_amount, max_amount, colours, offset=0, colour_steps=256, loop=False, cache=None, background=None):
        
        if min_amount >= max_amount:
            colours = [colours[0]]
            max_amount = min_amount + 1
        self.background = background
        self.max = max_amount
        self.min = min_amount
        self.amount = (self.min, self.max)
        self.amount_diff = self.max - self.min
        self.colours = colours
        self.offset = offset
        self.loop = loop
        self._len = len(colours)
        self._len_m = self._len - 1

        self.steps = colour_steps * self._len
        self._step_size = self.amount_diff / self.steps
        
        #Cache results for quick access
        if cache is None:
            self.cache = []
            for i in range(self.steps + 1):
                self.cache.append(self.calculate_colour(self.min + i * self._step_size))
        else:
            self.cache = cache
            
    def __getitem__(self, n):
        """Read an item from the cache."""
        if self.background is not None and not n:
            return self.background
            
        value_index = int(round((n - self.min) / self._step_size))
        
        if self.loop:
            if value_index != self.steps:
                return self.cache[value_index % self.steps]
        return self.cache[min(max(0, value_index), self.steps)]
    
    def calculate_colour(self, n, as_int=True):
        """Calculate colour for given value."""
        offset = (n + self.offset - self.min) / self.amount_diff
        index_f = self._len_m * offset

        #Calculate the indexes of colours to mix
        index_base = int(index_f)
        index_mix = index_base + 1
        if self.loop:
            index_base %= self._len
            index_mix %= self._len
        else:
            index_base = max(min(index_base, self._len_m), 0)
            index_mix = max(min(index_mix, self._len_m), 0)

        #Mix colours
        base_colour = self.colours[index_base]
        mix_colour = self.colours[index_mix]
        mix_ratio = max(min(index_f - index_base, 1), 0)
        mix_ratio_r = 1 - mix_ratio

        #Generate as tuple
        if as_int:
            return tuple(int(i * mix_ratio_r + j * mix_ratio)
                         for i, j in zip(base_colour, mix_colour))
        else:
            return tuple(i * mix_ratio_r + j * mix_ratio for i, j in zip(base_colour, mix_colour))

    def convert_to_rgb(self, array):
        """Convert an array into an RGB numpy array."""
        
        message = 'Converting {} points to RGB values... (this may take a few seconds)'
        try:
            Message(message.format(array.size))
        except AttributeError:
            array = numpy.array(array)
            Message(message.format(array.size))
        
        new = numpy.round(numpy.divide(array - self.min, self._step_size), 0, 'int64')
    
        start_colour = self.cache[0]
        end_colour = self.cache[-1]
        colour_array = [[self.cache[item] if 0 <= item <= self.steps 
                         else start_colour if item < 0 
                         else end_colour for item in sublst] 
                        for sublst in new.tolist()]
                        
        return numpy.array(colour_array, dtype='uint8')
    
    def _preview_gradient(self, width, height):
        """Draw a gradient to test the colours."""
        from PIL import Image
        
        colours = ColourRange(0, width, self.colours)
        
        image = Image.new('RGB', (width, height))
        pixels = image.load()
        
        height_range = range(height)
        for x in range(width):
            colour = colours[x]
            for y in height_range:
                pixels[x, y] = colour
                
        return image
        
            
def parse_colour_text(colours):
    """Convert text into a colour map.
    It could probably do with a rewrite to make it more efficient,
    as it was first written to only use capitals.

    Mixed Colour:
        Combine multiple colours.
        Examples: BlueRed, BlackYellowGreen
    Hexadecimal Colours:
        As well as typing in words, you may also use hex.
        All the same effects can apply to these.
        Supported formats are #RGB, #RGBA, #RRGGBB, #RRGGBBAA.
    Modified Colour:
        Apply a modification to a colour.
        If multiple ones are applied, they will work in reverse order.
        Light and dark are not opposites so will not cancel each other out.
        Examples: LightBlue, DarkLightYellow
    Transition:
        This ends the current colour mix and starts a new one.
        Examples: BlackToWhite, RedToGreenToBlue
    Duplicate:
        Avoid having to type out multiple versions of the same word.
        Be careful as it has different effects based on its position.
        It basically multiplies the next word, see below for usage.
        Examples:
            Before colour: DarkDoubleRed = DarkRedDarkRed
            Before modifier: TripleDarkLightRed = DarkDarkDarkLightRed
            Before transition: BlueDoubleToDarkRed = BlueToDarkRedToDarkRed
    Any number of these features can be combined together to create different effects.
        
    As an example, here are the values that would result in the heatmap:
        BlackToDarkBlueToBlueToCyanTripleBlueToCyanBlueTo
        + TripleCyanBlueToTripleCyanYellowToCyanYellowTo
        + CyanTripleYellowToYellowToOrangeToRedOrangeToRed 
    """
    
    colour_string = format_name(colours, '#')
    colour_data = parse_colour_file()['Colours']

    current_mix = [[]]
    current_colour = {'Mod': [], 'Dup': 1}
    while colour_string:
        edited = False

        #Check for colours
        colour_selection = None
        for colour, data in iteritems(colour_data):
            if colour_string.startswith(colour):
                colour_string = colour_string[len(colour):]
                colour_selection = data['Colour']
                break

        #Check for hex codes
        if colour_string.startswith('#'):
            length, colour_selection = hex_to_colour(colour_string[1:9])
            if colour_selection and length:
                colour_string = colour_string[1 + length:]

        #Process colour with stored modifiers/duplicates
        colour = None
        if colour_selection:
            edited = True
            
            #Apply modifiers in reverse order
            colour = list(colour_selection)
            for modifier in current_colour['Mod']:
                colour_offset = modifier.get('ColourOffset', 0)
                colour_shift = modifier.get('ColourShift', 0)
                alpha_offset = modifier.get('AlphaOffset', 0)
                alpha_shift = modifier.get('AlphaShift', 0)
                colour = [(colour[0] >> colour_shift) + colour_offset,
                          (colour[1] >> colour_shift) + colour_offset,
                          (colour[2] >> colour_shift) + colour_offset,
                          (colour[3] >> alpha_shift) + alpha_offset]
                          
            current_colour['Mod'] = []
            current_mix[-1] += [colour] * current_colour['Dup']
            current_colour['Dup'] = 1
            continue

        #Check for modifiers (dark, light, transparent etc)
        for i in MODIFIERS:
            if colour_string.startswith(i):
                colour_string = colour_string[len(i):]
                edited = True
                current_colour['Mod'] += [MODIFIERS[i]] * current_colour['Dup']
                current_colour['Dup'] = 1
        if edited:
            continue

        #Check for duplicates (double, triple, etc)
        for i in DUPLICATES:
            if colour_string.startswith(i):
                colour_string = colour_string[len(i):]
                edited = True
                current_colour['Dup'] *= DUPLICATES[i]
        if edited:
            continue

        #Start a new groups of colours
        for i in SEPERATORS:
            if colour_string.startswith(i):
                colour_string = colour_string[len(i):]
                edited = True

                #Handle putting a duplicate before 'to'
                new_list = []
                list_len = current_colour['Dup']
                if not current_mix[-1]:
                    new_list = current_mix[-1]
                    list_len -= 1

                #Start the ew list
                current_mix += [new_list] * list_len
                current_colour['Dup'] = 1
                break
        if edited:
            continue

        #Remove the first letter and try again
        colour_string = colour_string[1:]
    
    if not current_mix[0]:
        raise ValueError('invalid colour map: "{}"'.format(colours))

    #Merge colours together
    final_mix = []
    for colours in current_mix:
        
        result = colours[0]
        for colour in colours[1:]:
            result = [i + j for i, j in zip(result, colour)]
            
        num_colours = len(colours)
        final_mix.append(tuple(i / num_colours for i in result))
    return final_mix


def calculate_colour_map(colour_map):
    if not colour_map:
        raise ValueError('not enough colours to generate colour map')
    try:
        return parse_colour_text(parse_colour_file()['Maps'][format_name(colour_map)]['Colour'])
    except KeyError:
        generated_map = parse_colour_text(colour_map)
        if generated_map:
            if len(generated_map) < 2:
                raise ValueError('not enough colours to generate colour map')
            return generated_map
        else:
            raise ValueError('unknown colour map')
                

def get_luminance(r, g, b, a=None):
    return (0.2126*r + 0.7152*g + 0.0722*b)


def parse_colour_file(path=COLOUR_FILE):
    """Read the colours text file to get all the data.
    
    Returns a dictionary containing the keys 'Colours' and 'Maps'.
    
    Colours:
        Syntax: colour.name=value
        The value must be given as a hex code, where it will be converted 
        into an RGBA list with the range of 0 to 255.
        
        Format:
            {name.lower(): {'UpperCase': name, 
                            'Colour': [r, 
                                       g, 
                                       b,
                                       a]}}
            
    Maps:
        Syntax: maps.name.type[.options]=value
        
        Set a colour scheme for a map with "maps.Name.colour=__________".
        That will add a colour map that can be accessed with "Name".
        Add alternative options with "maps.Name.colour.Alter.native=__________"
        That will add a colour map that can be accessed with "nativeAlterName".
        Set if it is allowed for tracks, clicks, or the keyboard 
        with "maps.Name.tracks/clicks/keyboard=True".
        It may be enabled for more than one.
        
        Format:
            {name.lower(): {'Colour': value,
                            'UpperCase': name,
                            'Type': {'tracks': bool,
                                     'clicks': bool,
                                     'keyboard': bool}}}
    """
    with TextFile(path, 'r') as f:
        data = f.read()
    
    colours = {}
    colour_maps = {}
    for i, line in enumerate(data.splitlines()):
        var, value = [i.strip() for i in line.split('=', 1)]
        var_parts = var.split('.')
        
        #Parse colour part
        if var_parts[0] == 'colour':
            if len(var_parts) < 2:
                continue
                
            rgb = tuple(hex_to_colour(value)[1])
            if rgb is not None:
                colours[format_name(var_parts[1])] = {'Uppercase': var_parts[1], 'Colour': rgb}
        
        #Parse colour map part
        elif var_parts[0] == 'map':
            if len(var_parts) < 3:
                continue
        
            map_name = var_parts[1]
            map_name_l = format_name(map_name)
            var_type = var_parts[2].lower()
            
            if map_name_l not in colour_maps:
                colour_maps[map_name_l] = {'Colour': None, 'UpperCase': map_name,
                                         'Type': {'tracks': False, 'clicks': False, 'keyboard': False}}
                                         
            if var_type == 'colour':
            
                #Check if it is an alternative map, and if so, link to the main one
                map_name_ext = ''.join(var_parts[3:][::-1]) + map_name
                map_name_ext_l = format_name(map_name_ext)
                if map_name_l != map_name_ext_l:
                    colour_maps[map_name_ext_l] = {'Colour': value, 'UpperCase': map_name_ext,
                                                   'Type': colour_maps[map_name_l]['Type']}
                else:
                    colour_maps[map_name_ext_l]['Colour'] = value
                    
            elif var_type in ('clicks', 'tracks', 'keyboard'):
                if value.lower().startswith('t') or value.lower().startswith('y'):
                    colour_maps[map_name_l]['Type'][var_type] = True
                    
    return {'Colours': colours, 'Maps': colour_maps}


def get_map_matches(colour_maps=None, tracks=False, clicks=False, keyboard=False, linear=False):
    """Get colour maps for particular map types.

    Includes an optional linear argument to use the alternate linear colour variants.
    This should be used when LinearMapping is set for the keyboard colours.
    """
    if colour_maps is None:
        colour_maps = parse_colour_file()['Maps']

    #Get valid maps for selection
    result = set()
    linear_dups = set()
    for map_data in colour_maps.values():
        if tracks and map_data['Type'].get('tracks', False) or clicks and map_data['Type'].get('clicks', False) or keyboard and map_data['Type'].get('keyboard', False):
            result.add(map_data['UpperCase'])

            #Find if item is a "linear" variant
            if map_data['UpperCase'].startswith('Linear'):
                no_linear = map_data['UpperCase'][6:]
                linear_dups.add(no_linear)

    #Delete linear/non linear variants
    for linear_item in linear_dups:
        if not linear:
            linear_item = 'Linear' + linear_item
        try:
            result.remove(linear_item)
        except KeyError:
            pass

    return result

    
def hex_to_colour(h, _try_alt=True):
    """Convert a hex string to colour.
    Supports inputs as #RGB, #RGBA, #RRGGBB and #RRGGBBAA.
    If a longer string is invalid, it will try lower lengths.
    """
    if h.startswith('#'):
        h = h[1:]
    h_len = len(h)
    if h_len >= 8:
        try:
            return (8, [int(h[i*2:i*2+2], 16) for i in range(4)])
        except ValueError:
            if _try_alt:
                return hex_to_colour(h[:6])
    elif h_len >= 6:
        try:
            return (6, [int(h[i*2:i*2+2], 16) for i in range(3)] + [255])
        except ValueError:
            if _try_alt:
                return hex_to_colour(h[:4])
    elif h_len >= 4:
        try:
            return (3, [16*j+j for j in (int(h[i:i+1], 16) for i in range(4))])
        except ValueError:
            if _try_alt:
                return hex_to_colour(h[:3])
    elif h_len >= 3:
        try:
            return (3, [16*j+j for j in (int(h[i:i+1], 16) for i in range(3))] + [255])
        except ValueError:
            pass
    return (0, None)
    
    
def rgb_to_hex(rgb):
    return "#{0:02x}{1:02x}{2:02x}".format(*rgb)
    

def gradient_preview(folder, width=720, height=80):
    """Save each colour map as a gradient in a folder."""
    
    for map_lowercase, data in iteritems(parse_colour_file()['Maps']):
        colours = calculate_colour_map(map_lowercase)
        image = ColourRange(0, 1, colours)._preview_gradient(width, height)
        if data['Type']['tracks']:
            image.save(join_path((folder, 'Tracks', '{}.png'.format(data['UpperCase'])), create=True))
        if data['Type']['clicks']:
            image.save(join_path((folder, 'Clicks', '{}.png'.format(data['UpperCase'])), create=True))
        if data['Type']['keyboard']:
            image.save(join_path((folder, 'Keyboard', '{}.png'.format(data['UpperCase'])), create=True))