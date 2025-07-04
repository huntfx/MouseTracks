"""Partial rewrite of `mousetracks.image.colours`.
It has been trimmed down and type checked, but a full rewrite is needed.
"""

import re
from pathlib import Path
from typing import Any

from ..constants import REPO_DIR


COLOUR_FILE = REPO_DIR / 'config' / 'colours.txt'

MODIFIERS: dict[str, dict[str, int]] = {
    'light': {'ColourOffset': 128,
              'ColourShift': 1},
    'dark': {'ColourShift': 1},
    'transparent': {'AlphaShift': 8},
    'translucent': {'AlphaShift': 1},
    'opaque': {'AlphaShift': -1}
}

DUPLICATES: dict[str, int] = {
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

SEPERATORS: list[str] = ['to', 'then']


def to_lower(value: str, extra_chars: str = '') -> str:
    return re.sub('[^A-Za-z0-9{}]+'.format(extra_chars), '', value).lower()


class ColourRange(object):
    """Make a transition between colours.
    All possible colours within the range are cached for quick access.
    """

    def __init__(self, min_amount: int, max_amount: int, colours: list[tuple[int, ...]], offset: int = 0,
                 colour_steps: int = 256, loop: bool = False, background: tuple[int, ...] | None = None) -> None:
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

        self.cache: list[tuple[int, ...]]
        self.cache = [self._calculate_colour(round(self.min + i * self._step_size))
                      for i in range(self.steps + 1)]

    def __getitem__(self, n: int) -> tuple[int, ...]:
        """Read an item from the cache."""
        if self.background is not None and not n:
            return self.background

        value_index = round((n - self.min) / self._step_size)

        if self.loop:
            if value_index != self.steps:
                return self.cache[value_index % self.steps]
        return self.cache[min(max(0, value_index), self.steps)]

    def _calculate_colour(self, n: int) -> tuple[int, ...]:
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

        return tuple(int(i * mix_ratio_r + j * mix_ratio)
                     for i, j in zip(base_colour, mix_colour))


def parse_colour_text(colours: str) -> list[tuple[int, ...]]:
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

    colour_string = to_lower(colours, '#')
    colour_data = parse_colour_file()['Colours']

    current_mix: list[list[tuple[int, ...]]] = [[]]
    current_colour: dict[str, Any] = {'Mod': [], 'Dup': 1}
    while colour_string:
        edited = False

        #Check for colours
        colour_selection = None
        for colour, data in colour_data.items():
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
    for mix_colours in current_mix:

        result = list(mix_colours[0])
        for mix_colour in mix_colours[1:]:
            result = [i + j for i, j in zip(result, mix_colour)]

        num_colours = len(mix_colours)
        final_mix.append(tuple(i // num_colours for i in result))
    return final_mix


def calculate_colour_map(colour_map: str) -> list[tuple[int, ...]]:
    if not colour_map:
        raise ValueError('not enough colours to generate colour map')
    try:
        return parse_colour_text(parse_colour_file()['Maps'][to_lower(colour_map)]['Colour'])
    except KeyError:
        generated_map = parse_colour_text(colour_map)
        if generated_map:
            if len(generated_map) < 2:
                raise ValueError('not enough colours to generate colour map')
            return generated_map
        else:
            raise ValueError('unknown colour map')


def get_luminance(r: int, g: int, b: int, a: int | None = None) -> float:
    """Get the luminance of a colour."""
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def parse_colour_file(path: str | Path = COLOUR_FILE) -> dict[str, Any]:
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
    colours: dict[str, dict[str, Any]] = {}
    colour_maps: dict[str, dict[str, Any]] = {}

    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            var, value = [i.strip() for i in line.split('=', 1)]
            var_parts = var.split('.')

            # Parse colour part
            if var_parts[0] == 'colour':
                if len(var_parts) < 2:
                    continue

                colour = hex_to_colour(value)
                if colour[1] is None:
                    continue
                rgb = tuple(colour[1])
                if rgb is not None:
                    colours[to_lower(var_parts[1])] = {'Uppercase': var_parts[1], 'Colour': rgb}

            # Parse colour map part
            elif var_parts[0] == 'map':
                if len(var_parts) < 3:
                    continue

                map_name = var_parts[1]
                map_name_l = to_lower(map_name)
                var_type = var_parts[2].lower()

                if map_name_l not in colour_maps:
                    colour_maps[map_name_l] = {'Colour': None, 'UpperCase': map_name,
                                               'Type': {'tracks': False, 'clicks': False, 'keyboard': False},
                                               'Background': {'tracks': None, 'clicks': None, 'keyboard': None}}

                if var_type == 'colour':

                    #Check if it is an alternative map, and if so, link to the main one
                    map_name_ext = ''.join(var_parts[3:][::-1]) + map_name
                    map_name_ext_l = to_lower(map_name_ext)
                    if map_name_l != map_name_ext_l:
                        colour_maps[map_name_ext_l] = {'Colour': value, 'UpperCase': map_name_ext,
                                                    'Type': colour_maps[map_name_l]['Type']}
                    else:
                        colour_maps[map_name_ext_l]['Colour'] = value

                elif var_type in ('clicks', 'tracks', 'keyboard'):
                    if len(var_parts) > 3 and var_parts[3].lower() == 'background':
                        colour_maps[map_name_l]['Background'][var_type] = value

                    elif value.lower().startswith('t') or value.lower().startswith('y'):
                        colour_maps[map_name_l]['Type'][var_type] = True

    return {'Colours': colours, 'Maps': colour_maps}


def get_map_matches(tracks: bool = False, clicks: bool = False,
                    keyboard: bool = False, linear: bool = False) -> list[str]:
    """Get colour maps for particular map types.

    Includes an optional linear argument to use the alternate linear colour variants.
    This should be used when LinearMapping is set for the keyboard colours.
    """
    colour_maps = parse_colour_file()['Maps']

    # Get valid maps for selection
    result: set[str] = set()
    linear_dups: set[str] = set()
    for map_data in colour_maps.values():
        if tracks and map_data['Type'].get('tracks', False) or clicks and map_data['Type'].get('clicks', False) or keyboard and map_data['Type'].get('keyboard', False):
            result.add(map_data['UpperCase'])

            # Find if item is a "linear" variant
            if map_data['UpperCase'].startswith('Linear'):
                no_linear = map_data['UpperCase'][6:]
                linear_dups.add(no_linear)

    # Delete linear/non linear variants
    for linear_item in linear_dups:
        if not linear:
            linear_item = 'Linear' + linear_item
        result.discard(linear_item)

    return list(sorted(result))


def hex_to_colour(value: str) -> tuple[int, list[int] | None]:
    """Convert a hex string to colour.
    Supports inputs as #RGB, #RGBA, #RRGGBB and #RRGGBBAA.
    If a longer string is invalid, it will try lower lengths.
    """
    if value.startswith('#'):
        value = value[1:]
    value_len = len(value)
    if value_len >= 8:
        try:
            return (8, [int(value[i*2:i*2+2], 16) for i in range(4)])
        except ValueError:
            return hex_to_colour(value[:6])
    elif value_len >= 6:
        try:
            return (6, [int(value[i*2:i*2+2], 16) for i in range(3)] + [255])
        except ValueError:
            return hex_to_colour(value[:4])
    elif value_len >= 4:
        try:
            return (3, [16*j+j for j in (int(value[i:i+1], 16) for i in range(4))])
        except ValueError:
            return hex_to_colour(value[:3])
    elif value_len >= 3:
        try:
            return (3, [16*j+j for j in (int(value[i:i+1], 16) for i in range(3))] + [255])
        except ValueError:
            pass
    return (0, None)
