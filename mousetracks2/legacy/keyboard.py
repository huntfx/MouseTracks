"""Partial rewrite of `mousetracks.image.keyboard`.
It has been trimmed down and type checked, but a full rewrite is needed.
"""

from dataclasses import dataclass
from typing import Any, Literal, Iterator

from PIL import Image, ImageFont, ImageDraw

from .colours import COLOUR_FILE, ColourRange, calculate_colour_map, get_luminance, parse_colour_file, parse_colour_text
from ..constants import REPO_DIR, UPDATES_PER_SECOND
from ..gui.utils import format_ticks
from ..utils.math import calculate_circle


LANGUAGE_BASE_PATH = REPO_DIR / 'config' / 'language'

KEYBOARD_KEYS_FOLDER = LANGUAGE_BASE_PATH / 'keyboard' / 'keys'

KEYBOARD_LAYOUT_FOLDER = LANGUAGE_BASE_PATH / 'keyboard' / 'layout'

@dataclass
class TimeUnit:
    name: str
    """Name of the time unit."""
    length: int
    """How many seconds the unit is."""
    limit: int | None
    """What's the maximum value."""
    decimals: int | None
    """How many decimals to show."""

TIME_UNITS = [
    TimeUnit('second', 1, 60, 2),
    TimeUnit('minute', 60, 60, None),
    TimeUnit('hour', 3600, 24, None),
    TimeUnit('day', 3600 * 24, 7, None),
    TimeUnit('week', 3600 * 24 * 7, 52, None),
    TimeUnit('year', 3600 * 24 * 365, None, None)
]


def parse_keys() -> Iterator[tuple[int, str]]:
    """Get the key names."""
    with (KEYBOARD_KEYS_FOLDER / 'en_GB.ini').open('rb') as f:
        for i, line in enumerate(f):
            if not i:
                continue
            code, string = line.strip(b'\r\n').split(b' = ')
            yield int(code), string.decode('utf-8')


def keyboard_layout(extended: bool = True) -> list[list[tuple[str | None, float, float]]]:
    """Generate the keyboard layout."""
    result: list[list[tuple[str | None, float, float]]] = []

    # Read lines from file
    with (KEYBOARD_LAYOUT_FOLDER / 'en_US.txt').open('r', encoding='utf-8') as f:
        data = [line.strip() for line in f]

    try:
        gap = float(data[0])
    except (ValueError, IndexError):
        gap = 1
    else:
        del data[0]

    for row in data:
        result.append([])

        # Handle half rows
        row = row.strip()
        if not row:
            continue

        # Remove second half of keyboard if required
        if extended:
            row = row.replace(':', '')
        else:
            row = row.split(':', 1)[0]

        for key in row.split('+'):

            key_data = key.split('|')
            default_height = 1.0
            default_width = 1.0

            # Get key name if set, otherwise change the width
            try:
                name: str | None = str(key_data[0])
                if not name:
                    name = None
                    raise IndexError
            except IndexError:
                default_width = gap

            # Set width and height
            try:
                width = float(key_data[1])
            except (IndexError, ValueError):
                width = default_width
            else:
                width = max(0.0, width)
            try:
                height = float(key_data[2])
            except (IndexError, ValueError):
                height = default_height
            else:
                height = max(0.0, height)

            result[-1].append((name, width, height))

    return result


@dataclass
class _KeyboardGlobals:
    """Store and edit global variables.

    This is needed because the legacy code actually used global vars,
    but the newer code needs to be able to modify them at runtime.
    This will be removed once the keyboard rendering code has been
    rewritten.
    """

    multiplier: int = 1

    colour_map: str = 'Aqua'

    data_set: str = 'count'  # 'time' or 'count'

    DROP_SHADOW_X = 1.25

    DROP_SHADOW_Y = 1.5

    FONT_SIZE_MAIN = 17.0

    FONT_SIZE_STATS = 13.0

    FONT_LINE_SPACING = 5.0

    FONT_OFFSET_X = 5.0

    FONT_OFFSET_Y = 5.0

    IMAGE_PADDING = 16.0

    KEY_BORDER = 0.6

    KEY_CORNER_RADIUS = 3.0

    KEY_PADDING = 8.0

    KEY_SIZE = 65.0

    @property
    def font_size_main(self) -> int:
        return round(self.FONT_SIZE_MAIN * self.multiplier)

    @property
    def font_size_stats(self) -> int:
        return round(self.FONT_SIZE_STATS * self.multiplier)

    @property
    def font_line_spacing(self) -> int:
        return round(self.FONT_LINE_SPACING * self.multiplier)

    @property
    def font_offset_x(self) -> int:
        return round(self.FONT_OFFSET_X * self.multiplier)

    @property
    def font_offset_y(self) -> int:
        return round(self.FONT_OFFSET_Y * self.multiplier)

    @property
    def image_padding(self) -> int:
        return round(self.IMAGE_PADDING * self.multiplier)

    @property
    def key_size(self) -> int:
        return round(self.KEY_SIZE * self.multiplier)

    @property
    def key_padding(self) -> int:
        return round(self.KEY_PADDING * self.multiplier)

    @property
    def key_corner_radius(self) -> int:
        return round(self.KEY_CORNER_RADIUS * self.multiplier)

    @property
    def key_border(self) -> int:
        return round(self.KEY_BORDER * self.multiplier)

    @property
    def drop_shadow_x(self) -> int:
        return round(self.DROP_SHADOW_X * self.multiplier)

    @property
    def drop_shadow_y(self) -> int:
        return round(self.DROP_SHADOW_Y * self.multiplier)

    def circle(self) -> dict[str, tuple[set[tuple[int, int]], set[tuple[int, int]]]]:
        """Calculate the coordinates of a circle."""
        return {
            'TopRight': calculate_circle(self.key_corner_radius, (True, False, False, False)),
            'TopLeft': calculate_circle(self.key_corner_radius, (False, False, False, True)),
            'BottomRight': calculate_circle(self.key_corner_radius, (False, True, False, False)),
            'BottomLeft': calculate_circle(self.key_corner_radius, (False, False, True, False)),
        }


GLOBALS = _KeyboardGlobals()


class KeyboardButton(object):
    def __init__(self, x: int, y: int, x_len: int, y_len: int | None = None) -> None:
        if y_len is None:
            y_len = x_len
        self.x = x
        self.y = y
        self.x_len = x_len
        self.y_len = y_len
        x_range = tuple(range(x, x + x_len))
        y_range = tuple(range(y, y + y_len))

        # Cache range (and fix error with radius of 0)
        i_start = round(GLOBALS.key_corner_radius + 1)
        i_end = round(-GLOBALS.key_corner_radius) or max(x + x_len, y + y_len)
        self.cache = {'x': x_range[i_start:i_end],
                      'y': y_range[i_start:i_end],
                      'x_start': x_range[1:i_start],
                      'y_start': y_range[1:i_start],
                      'x_end': x_range[i_end:],
                      'y_end': y_range[i_end:]}

    def _circle_offset(self, x: int, y: int, direction: str) -> tuple[int, int]:
        match direction:
            case 'TopLeft':
                return (self.x + x + GLOBALS.key_corner_radius, self.y + y + GLOBALS.key_corner_radius)
            case 'TopRight':
                return (self.x + x + self.x_len - GLOBALS.key_corner_radius, self.y + y + GLOBALS.key_corner_radius)
            case 'BottomLeft':
                return (self.x + x + GLOBALS.key_corner_radius, self.y + y + self.y_len - GLOBALS.key_corner_radius)
            case 'BottomRight':
                return (self.x + x + self.x_len - GLOBALS.key_corner_radius, self.y + y + self.y_len - GLOBALS.key_corner_radius)
        raise NotImplementedError(direction)

    def outline(self) -> list[tuple[int, int]]:
        coordinates: list[tuple[int, int]] = []
        if not GLOBALS.key_border:
            return coordinates

        # Rounded corners
        circle = GLOBALS.circle()
        top_left = [self._circle_offset(x, y, 'TopLeft') for x, y in circle['TopLeft'][0]]
        top_right = [self._circle_offset(x, y, 'TopRight') for x, y in circle['TopRight'][0]]
        bottom_left = [self._circle_offset(x, y, 'BottomLeft') for x, y in circle['BottomLeft'][0]]
        bottom_right = [self._circle_offset(x, y, 'BottomRight') for x, y in circle['BottomRight'][0]]

        # Rounded corner thickness
        # This is a little brute force but everything else I tried didn't work
        r = tuple(range(GLOBALS.key_border))
        for x, y in top_left:
            coordinates += [(x-i, y-j) for i in r for j in r]
        for x, y in top_right:
            coordinates += [(x+i, y-j) for i in r for j in r]
        for x, y in bottom_left:
            coordinates += [(x-i, y+j) for i in r for j in r]
        for x, y in bottom_right:
            coordinates += [(x+i, y+j) for i in r for j in r]

        # Straight lines
        for i in r:
            coordinates += [(_x, self.y - i) for _x in self.cache['x']]
            coordinates += [(_x, self.y + self.y_len + i) for _x in self.cache['x']]
            coordinates += [(self.x - i, _y) for _y in self.cache['y']]
            coordinates += [(self.x + self.x_len + i, _y) for _y in self.cache['y']]

        return coordinates

    def fill(self) -> list[tuple[int, int]]:
        coordinates: list[tuple[int, int]] = []

        # Squares
        coordinates += [(x, y) for y in self.cache['y'] for x in self.cache['x']]
        coordinates += [(x, y) for y in self.cache['y'] for x in self.cache['x_start']]
        coordinates += [(x, y) for y in self.cache['y'] for x in self.cache['x_end']]
        coordinates += [(x, y) for y in self.cache['y_start'] for x in self.cache['x']]
        coordinates += [(x, y) for y in self.cache['y_end'] for x in self.cache['x']]

        # Corners
        circle = GLOBALS.circle()
        coordinates += [self._circle_offset(x, y, 'TopLeft') for x, y in circle['TopLeft'][1]]
        coordinates += [self._circle_offset(x, y, 'TopRight') for x, y in circle['TopRight'][1]]
        coordinates += [self._circle_offset(x, y, 'BottomLeft') for x, y in circle['BottomLeft'][1]]
        coordinates += [self._circle_offset(x, y, 'BottomRight') for x, y in circle['BottomRight'][1]]

        return coordinates


class KeyboardGrid(object):

    FILL_COLOUR = (170, 170, 170)
    OUTLINE_COLOUR = (0, 0, 0)

    def __init__(self, pressed_keys: dict[int, int], held_keys: dict[int, int]) -> None:
        self.grid: list[list[dict[str, Any]]] = []
        self.pressed_keys = pressed_keys
        self.held_keys = held_keys
        parsed = parse_colour_file(COLOUR_FILE)
        self.colours = parsed['Colours']
        self.maps = parsed['Maps']

    def new_row(self) -> None:
        self.row: list[dict[str, Any]] = []
        self.grid.append(self.row)

    def add_key(self, name: str | None, width: float | None = None, height: float | None = None,
                hide_border: bool = False, custom_colour: tuple[int, ...] | Literal[False] | None = None) -> None:
        if width is None:
            width = 1.0
        if height is None:
            height = 1.0
        _width = round(GLOBALS.key_size * width + GLOBALS.key_padding * max(0.0, width - 1))
        _height = round(GLOBALS.key_size * height + GLOBALS.key_padding * max(0.0, height - 1))
        _values: dict[str, Any] = {'Dimensions': (_width, _height),
                                   'DimensionMultipliers': (width, height),
                                   'Name': name,
                                   'CustomColour': custom_colour,
                                   'HideBorder': hide_border}
        self.row.append(_values)

    def generate_coordinates(self) -> tuple[tuple[int, int], dict[str, Any]]:
        image: dict[str, Any] = {'Fill': {}, 'Outline': [], 'Text': []}
        max_offset: dict[str, int] = {'X': 0, 'Y': 0}

        # Setup the colour range
        if GLOBALS.data_set == 'time':
            data = self.pressed_keys.values()
        elif GLOBALS.data_set == 'count':
            data = self.held_keys.values()
        else:
            raise ValueError('invalid dataset')

        pools = sorted(set(data))
        max_range = len(pools) + 1
        lookup = {v: i + 1 for i, v in enumerate(pools)}
        lookup[0] = 0

        try:
            colour_map_data = calculate_colour_map(GLOBALS.colour_map)
        except Exception:  # Old code - just fallback to tranparent
            colour_map_data = [(0, 0, 0, 0)]
        colour_range = ColourRange(0, max_range, colour_map_data)

        # Decide on background colour
        try:
            colour_map = self.maps[GLOBALS.colour_map.lower()]['Background']['keyboard']
        except KeyError:
            colour_map = None
        if colour_map is None:
            image['Background'] = colour_map_data[0]
        else:
            image['Background'] = parse_colour_text(colour_map)[0]
        image['Shadow'] = colour_map_data[-1]

        y_offset = GLOBALS.image_padding
        y_current = 0
        keys = dict(parse_keys())
        for row in self.grid:
            x_offset = GLOBALS.image_padding

            for values in row:

                x, y = values['Dimensions']
                hide_background = False

                # Convert the key number to a name and get stats
                if values['Name'] is not None:
                    if values['Name'].isdigit():
                        key_name = int(values['Name'])

                        # Get press/time count
                        count_time = self.held_keys.get(key_name, 0)
                        count_press = self.pressed_keys.get(key_name, 0)
                        if GLOBALS.data_set == 'time':
                            key_count = count_press
                        elif GLOBALS.data_set == 'count':
                            key_count = count_time
                        else:
                            key_count = 0

                    else:
                        key_name = values['Name']
                        key_count = 0

                    # Get key name
                    display_name = keys.get(key_name, key_name)
                    button_coordinates = KeyboardButton(x_offset, y_offset, x, y)

                    # Calculate colour for key
                    fill_colour: tuple[int, ...]
                    if values['CustomColour'] is None:
                        fill_colour = colour_range[lookup[key_count]]
                    else:
                        if values['CustomColour'] is False:
                            hide_background = True
                            fill_colour = image['Background']
                        else:
                            fill_colour = values['CustomColour']

                    # Calculate colour for border
                    if get_luminance(*fill_colour) > 128:
                        text_colour = self.colours['black']['Colour']
                    else:
                        text_colour = self.colours['white']['Colour']

                    #S tore values
                    _values = {'Offset': (x_offset, y_offset),
                               'KeyName': display_name,
                               'Counts': {'count': count_press, 'time': count_time},
                               'Colour': text_colour,
                               'Dimensions': values['DimensionMultipliers']}
                    image['Text'].append(_values)

                    if not values['HideBorder']:
                        image['Outline'] += button_coordinates.outline()
                    if not hide_background:
                        try:
                            image['Fill'][fill_colour] += button_coordinates.fill()
                        except KeyError:
                            image['Fill'][fill_colour] = button_coordinates.fill()

                x_offset += GLOBALS.key_padding + x
                y_current = max(y_current, GLOBALS.key_size, y - GLOBALS.key_padding)

            # Decrease size of empty row
            if row:
                y_offset += GLOBALS.key_size + GLOBALS.key_padding
            else:
                y_offset += (GLOBALS.key_size + GLOBALS.key_padding) // 2

            max_offset['X'] = max(max_offset['X'], x_offset)
            max_offset['Y'] = max(max_offset['Y'], y_offset)
            y_current -= GLOBALS.key_size

        # Calculate total size of image
        width = max_offset['X'] + GLOBALS.image_padding - GLOBALS.key_padding + 1
        height = max_offset['Y'] + GLOBALS.image_padding + y_current - GLOBALS.key_padding + GLOBALS.drop_shadow_y + 1
        return ((width, height), image)


def shorten_number(n: float, limit: int = 5, sig_figures: int | None = None, decimal_units: bool = True) -> str:
    """Set a number over a certain length to something shorter.
    For example, 2000000 can be shortened to 2m.
    The numbers will be kept as long as possible,
    so "2000k" will override "2m" at a length of 5.
    Set a minimum length to ensure it has a certain number of digits.
    Disable decimal_units if you do not want this enforced on units (such as 15.000000).
    """
    if sig_figures is None:
        sig_figures = limit - 1
    limits: list[str] = [''] + list('kmbtq')
    i = 0
    str_n = str(int(n))
    max_length = max(limit, 4)

    try:
        # Reduce the number until it fits in the required space
        while True:
            prefix = limits[i]
            if len(str_n) < max_length or not prefix and len(str_n) <= max_length:
                break
            i += 1
            str_n = str_n[:-3]
        result = n / 10 ** (i * 3)

        # Return whole number if decimal units are disabled
        if not decimal_units and not prefix:
            return str(int(result))

        # Convert to string if result is too large for a float
        overflow = 'e+' in str(result)
        if overflow:
            result = f'{int(result)}.0'

        # Format the decimals based on required significant figures
        if overflow:
            int_length = len(result)
        else:
            int_length = len(str(int(result)))

        # Set maximum (and minimum) number of decimal points)
        max_decimals = max(0, sig_figures - int_length - bool(prefix))
        if sig_figures and max_decimals:
            result_parts = str(result).split('.')
            decimal = str(round(float('0.{result_parts[1]}'), max_decimals))[2:]
            extra_zeroes = max_decimals - len(decimal)
            result = f'{result_parts[0]}.{decimal}{"0" * extra_zeroes}'
        else:
            if overflow:
                result = result.split('.')[0]
            else:
                result = int(result)
        return f'{result}{prefix}'

    # If the number goes out of limits, return that it's infinite
    except IndexError:
        return 'inf'


def ticks_to_seconds(amount: float, tick_rate: int = 1, output_length: int = 2,
                     allow_decimals: bool = True, short: bool = False) -> str:
    """Simple function to convert ticks to a readable time for use in sentences."""
    current: float | int
    output = []
    time_elapsed = amount / tick_rate
    for time_unit in TIME_UNITS[::-1]:
        current = round(time_elapsed / time_unit.length, time_unit.decimals if allow_decimals else None)

        if time_unit.limit is not None:
            current %= time_unit.limit
            if isinstance(current, float):
                current = round(current, time_unit.decimals)  # Handle floating point errors

        if current:
            if short:
                output.append(f'{current}{time_unit.name[0]}')
            else:
                output.append(f'{current} {time_unit.name}{"" if current == 1 else "s"}')
            if len(output) == output_length:
                break

    if not output:
        if short:
            output.append(f'{current}{time_unit.name[0]}')
        else:
            output.append(f'{current} {time_unit.name}s')

    if len(output) > 1:
        return ' and '.join((', '.join(output[:-1]), output[-1]))
    return output[-1]


class DrawKeyboard(object):
    def __init__(self, profile_name: str, ticks: int, pressed_keys: dict[int, int],
                 held_keys: dict[int, int]) -> None:
        self.name = profile_name

        self.ticks = ticks
        self.pressed_keys = pressed_keys
        self.held_keys = held_keys

        self.grid = self._create_grid()

    def _create_grid(self) -> KeyboardGrid:
        print('Building keyboard from layout...')
        grid = KeyboardGrid(self.pressed_keys, self.held_keys)
        for row in keyboard_layout():
            grid.new_row()
            for name, width, height in row:
                custom_colour: Literal[False] | None
                if name == '__STATS__':
                    hide_border = True
                    custom_colour = False
                else:
                    hide_border = False
                    custom_colour = None
                grid.add_key(name, width, height, hide_border=hide_border, custom_colour=custom_colour)
        return grid

    def calculate(self) -> dict[str, Any]:
        print('Generating coordinates...')
        (width, height), coordinate_dict = self.grid.generate_coordinates()
        return {'Width': width,
                'Height': height,
                'Coordinates': coordinate_dict}

    def draw_image(self, font: str = 'arial.ttf') -> Image.Image:
        data = self.calculate()

        # Create image object
        image = Image.new('RGB', (data['Width'], data['Height']))
        image.paste(data['Coordinates']['Background'], (0, 0, data['Width'], data['Height']))
        pixels = image.load()
        assert pixels is not None

        # Add drop shadow
        shadow = (64, 64, 64)
        if (GLOBALS.drop_shadow_x or GLOBALS.drop_shadow_y) and data['Coordinates']['Background'][:3] == (255, 255, 255):
            print('Adding drop shadow...')
            for colour in data['Coordinates']['Fill']:
                for x, y in data['Coordinates']['Fill'][colour]:
                    pixels[GLOBALS.drop_shadow_x + x, GLOBALS.drop_shadow_y + y] = shadow

        # Fill colours
        print('Colouring keys...')
        for colour in data['Coordinates']['Fill']:
            for x, y in data['Coordinates']['Fill'][colour]:
                pixels[x, y] = colour

        # Draw border
        print('Drawing outlines...')
        border = tuple(255 - i for i in data['Coordinates']['Background'])
        for x, y in data['Coordinates']['Outline']:
            pixels[x, y] = border

        # Draw text
        print('Writing text...')
        draw = ImageDraw.Draw(image)
        font_key = ImageFont.truetype(font, size=GLOBALS.font_size_main)
        font_amount = ImageFont.truetype(font, size=GLOBALS.font_size_stats)

        # Generate stats
        elapsed_time = ticks_to_seconds(self.ticks, 60)
        stats = [f'Time elapsed: {elapsed_time}']
        if GLOBALS.data_set == 'count':
            total_presses = shorten_number(sum(self.pressed_keys.values()), limit=25, decimal_units=False)
            stats.append(f'Total key presses: {total_presses}')
            stats.append('Colour based on how long keys were pressed for.')
        elif GLOBALS.data_set == 'time':
            total_time = format_ticks(sum(self.pressed_keys.values()))
            stats.append(f'Total press time: {total_time}')
            stats.append('Colour based on number of key presses.')
        stats_text = [f'{self.name}:', '\n'.join(stats)]

        # Write text to image
        for values in data['Coordinates']['Text']:
            x, y = values['Offset']
            text = values['KeyName']
            text_colour = values['Colour']

            # Override for stats text
            if text == '__STATS__':
                draw.text((x, y), stats_text[0], font=font_key, fill=text_colour)
                y += GLOBALS.font_size_main + GLOBALS.font_line_spacing
                draw.text((x, y), stats_text[1], font=font_amount, fill=text_colour)
                continue

            height_multiplier = max(0, values['Dimensions'][1] - 1)
            x += GLOBALS.font_offset_x
            if not height_multiplier:
                y += GLOBALS.font_offset_y
            y += (GLOBALS.key_size - GLOBALS.font_size_main + GLOBALS.font_offset_y) * height_multiplier

            # Ensure each key is at least at a constant height
            text = text.replace('\\n', '\n')
            if '\n' not in text:
                text += '\n'

            draw.text((x, y), text, font=font_key, fill=text_colour)

            # Correctly place count at bottom of key
            if height_multiplier:
                y = values['Offset'][1] + (GLOBALS.key_size + GLOBALS.key_padding) * height_multiplier + GLOBALS.font_offset_y

            y += (GLOBALS.font_size_main + GLOBALS.font_line_spacing) * (1 + text.count('\n'))

            amount = values['Counts'][GLOBALS.data_set]
            if GLOBALS.data_set == 'time':
                text = format_ticks(amount, accuracy=(amount < UPDATES_PER_SECOND) + 1, length=1)
            else:
                max_width = int(10 * values['Dimensions'][0] - 3)
                text = f'x{shorten_number(amount, limit=max_width, sig_figures=max_width - 1, decimal_units=False)}'
            draw.text((x, y), text, font=font_amount, fill=text_colour)

        return image
