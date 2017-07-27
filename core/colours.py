from __future__ import division, absolute_import

from core.compatibility import range


COLOURS_MAIN = {
    'red': (255, 0, 0, 255),
    'green': (0, 255, 0, 255),
    'blue': (0, 0, 255, 255),
    'yellow': (255, 255, 0, 255),
    'cyan': (0, 255, 255, 255),
    'magenta': (255, 0, 255, 255),
    'white': (255, 255, 255, 255),
    'grey': (127, 127, 127, 255),
    'gray': (127, 127, 127, 255),
    'black': (0, 0, 0, 255),
    'orange': (255, 127, 0, 255),
    'pink': (255, 0, 127, 255),
    'purple': (127, 0, 255, 255),
    'sky': (0, 164, 255, 255)
}

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

SEPERATORS = ['to']


class ColourRange(object):
    """Make a transition between colours.
    All possible colours within the range are cached for quick access.
    """
    
    def __init__(self, min_amount, max_amount, colours, offset=0, loop=False, cache=None):
        
        if min_amount >= max_amount:
            colours = [colours[0]]
            max_amount = min_amount + 1
        self.amount = (min_amount, max_amount)
        self.amount_diff = max_amount - min_amount
        self.colours = colours
        self.offset = offset
        self.loop = loop
        self._len = len(colours)
        self._len_m = self._len - 1

        self._step_max = 255 * self._len
        self._step_size = self.amount_diff / self._step_max
        
        #Cache results for quick access
        if cache is None:
            self.cache = []
            for i in range(self._step_max + 1):
                self.cache.append(self.calculate_colour(self.amount[0] + i * self._step_size))
        else:
            self.cache = cache
            
    def __getitem__(self, n):
        """Read an item from the cache."""
        value_index = int((n - self.amount[0]) / self._step_size)
        if self.loop:
            if value_index != self._step_max:
                return self.cache[value_index % self._step_max]
        return self.cache[min(max(0, value_index), self._step_max)]
    
    def calculate_colour(self, n, as_int=True):
        """Calculate colour for given value."""
        offset = (n + self.offset - self.amount[0]) / self.amount_diff
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

def _parse_colour_text(colour_string):
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
    colour_string = colour_string.lower()

    current_mix = [[]]
    current_colour = {'Mod': [], 'Dup': 1}
    while colour_string:
        edited = False

        #Check for colours
        colour_selection = None
        for i in COLOURS_MAIN:
            if colour_string.startswith(i):
                colour_string = colour_string[len(i):]
                colour_selection = COLOURS_MAIN[i]
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
        raise ValueError('input colour map is not valid')

    #Merge colours together
    final_mix = []
    for colours in current_mix:
        
        result = colours[0]
        for colour in colours[1:]:
            result = [i + j for i, j in zip(result, colour)]
            
        num_colours = len(colours)
        final_mix.append(tuple(i / num_colours for i in result))
    return final_mix


class ColourMap(object):
    """Look up default colours or generate one if the set doesn't exist."""
    _MAPS = {
        'jet': ('BlackToDarkBlueToBlueToCyanBlueBlueBlueToCyanBlueTo'
                'CyanCyanCyanBlueToCyanCyanCyanYellowToCyanYellowTo'
                'CyanYellowYellowYellowToYellowToOrangeToRedOrangeToRed'), #heatmap
        'transparentjet': ('TransparentBlackToTranslucentTranslucentDarkBlueTo'
                           'TranslucentBlueToTranslucentCyanTranslucentBlueBlueBlueTo'
                           'CyanBlueToCyanCyanCyanBlueToCyanCyanCyanYellowToCyanYellow'
                           'ToCyanYellowYellowYellowToYellowToOrangeToRedOrangeToRed'), #heatmap
        'radiation': 'BlackToRedToYellowToWhiteToWhiteWhiteWhiteLightLightGrey', #heatmap
        'transparentradiation': ('TransparentBlackToTranslucentRedToYellowTo'
                                 'WhiteToWhiteWhiteWhiteLightLightGrey'), #heatmap
        'default': 'WhiteToBlack', #tracks
        'citrus': 'BlackToDarkDarkGreyToDarkGreenToYellow', #tracks
        'ice': 'BlackToDarkBlueToDarkBlueLightDarkCyanToLightBlueDarkCyanToWhite', #tracks
        'neon': 'BlackToPurpleToPinkToBlackToPink', #tracks
        'sunburst': 'DarkDarkGrayToOrangeToBlackToOrangeToYellow', #tracks
        'demon': 'WhiteToRedToBlackToWhite', #tracks
        'chalk': 'BlackToWhite', #tracks
        'lightning': 'DarkPurpleToLightMagentaToLightGrayToWhiteToWhite', #tracks
        'hazard': 'WhiteToBlackToYellow', #tracks
        'razer': 'BlackToDarkGreyToBlackToDarkGreenToGreenToBlack', #tracks
        'sketch': 'LightGreyToBlackToDarkPurpleToWhiteToLightGreyToBlackToBlue', #tracks
        'grape': 'WhiteToBlackToMagenta', #tracks
        'spiderman': 'RedToBlackToWhite', #tracks/keyboard
        'shroud': 'GreyToBlackToLightPurple', #tracks
        'blackwidow': 'PurpleToLightCyanWhiteToPurpleToBlack', #tracks
        'aqua': 'WhiteToWhiteWhiteLightCyanSkyToSkyToSkyBlue', #keyboard
        'fire': ('WhiteToWhiteWhiteYellowLightOrangeToWhiteYellowLightOrangeToWhiteYellowOrangeTo'
                 'WhiteLightYellowRedLightRedOrangeToYellowLightYellowRedDarkOrangeToRedDarkRedDarkRed'), #keyboard
        'fire3': ('WhiteToWhiteWhiteYellowLightOrangeToWhiteYellowLightOrangeToWhiteYellow'
                 'OrangeToLightRedOrangeOrangeToLightYellowRedDarkOrangeToRedDarkRedDarkRed'), #keyboard
        'fire2': ('WhiteToWhiteWhiteYellowLightOrangeToWhiteYellowLightOrangeToWhiteYellow'
                 'OrangeToLightRedOrangeOrangeToLightYellowRedRedDarkOrangeToDarkRed'), #keyboard
        'ivy': 'WhiteToBlueGreenGreenToBlack', #keyboard
        'matrix': ('BlackBlackBlackBlackDarkGreenDarkDarkGreyToBlackBlack'
                   'BlackBlackBlackGreyGreenToBlackBlackDarkGreyGreenToGreen'), #keyboard/tracks
        'nature': ('WhiteToWhiteLightYellowLightGreenLightLightGrey' #keyboard
                   'ToLightYellowGreenLightGreenToDarkGreen'), #keyboard
        'linearfire': 'WhiteToYellowLightOrangeToLightYellowOrangeRedDarkRedToDarkOrangeOrangeRedToBlackBlackOrangeRedDarkRedToRedDarkRedDarkRed',  #keyboard (linear) - need to make the process automatic
        'linearmatrix': 'BlackBlackBlackBlackBlackDarkGreenDarkDarkGreyToGreen',
        'linearnature': 'WhiteToDarkGreen'
    }
    def __getitem__(self, colour_profile):
        try:
            return _parse_colour_text(self._MAPS[colour_profile.lower()])
        except KeyError:
            generated_map = _parse_colour_text(colour_profile)
            if generated_map:
                if len(generated_map) < 2:
                    raise ValueError('not enough colours to generate colour map')
                return generated_map
            else:
                raise ValueError('unknown colour map')


def get_luminance(r, g, b, a=None):
    return (0.2126*r + 0.7152*g + 0.0722*b)

    
def _new_colour_map_data():
    return {'tracks': False, 'clicks': False, 'keyboard': False}

    
def parse_colour_file(path):
    with open(path, 'r') as f:
        data = f.read()
        
    colour_maps = {}
    for line in data.splitlines():
        var, value = [i.strip() for i in line.split('=', 1)]
        var_parts = var.split('.')[1:]
        map_name = var_parts[0].lower()
        var_type = var_parts[1]

        #Write values to dictionary
        if map_name not in colour_maps:
            colour_maps[map_name] = _new_colour_map_data()
        if var_type in ('tracks', 'clicks', 'keyboard'):
            value = True if value.lower() == 'true' else False
        colour_maps[map_name][var_type] = value

        #Link alternative names
        if var_type == 'map':
            alt_name = ''.join(var_parts[2:][::-1]).strip() + map_name
            if alt_name:
                colour_maps[alt_name] = colour_maps[map_name]

    return colour_maps
    
    
def hex_to_colour(h, _try_alt=True):
    """Convert a hex string to colour.
    Supports inputs as #RGB, #RGBA, #RRGGBB and #RRGGBBAA.
    If a longer string is invalid, it will try lower lengths.
    """
    if h.startswith('#'):
        h = h[:-1]
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
