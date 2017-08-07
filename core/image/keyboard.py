from __future__ import division
from PIL import Image, ImageFont, ImageDraw

from core.colours import ColourRange, ColourMap, get_luminance, COLOURS_MAIN
from core.compatibility import get_items
from core.config import CONFIG
from core.language import Language
from core.files import load_program
from core.maths import round_int, calculate_circle
from core.messages import ticks_to_seconds


MULTIPLIER = CONFIG['GenerateKeyboard']['SizeMultiplier']

KEY_SIZE = round_int(CONFIG['GenerateKeyboard']['KeySize'] * MULTIPLIER)

KEY_CORNER_RADIUS = round_int(CONFIG['GenerateKeyboard']['KeyCornerRadius'] * MULTIPLIER)

KEY_PADDING = round_int(CONFIG['GenerateKeyboard']['KeyPadding'] * MULTIPLIER)

KEY_BORDER = round_int(CONFIG['GenerateKeyboard']['KeyBorder'] * MULTIPLIER)

DROP_SHADOW_X = round_int(CONFIG['GenerateKeyboard']['DropShadowX'] * MULTIPLIER)

DROP_SHADOW_Y = round_int(CONFIG['GenerateKeyboard']['DropShadowY'] * MULTIPLIER)

IMAGE_PADDING = round_int(CONFIG['GenerateKeyboard']['ImagePadding'] * MULTIPLIER)

FONT_SIZE_MAIN = round_int(CONFIG['GenerateKeyboard']['FontSizeMain'] * MULTIPLIER)

FONT_SIZE_STATS = round_int(CONFIG['GenerateKeyboard']['FontSizeStats'] * MULTIPLIER)

FONT_OFFSET_X = round_int(CONFIG['GenerateKeyboard']['FontWidthOffset'] * MULTIPLIER)

FONT_OFFSET_Y = round_int(CONFIG['GenerateKeyboard']['FontHeightOffset'] * MULTIPLIER)

FONT_LINE_SPACING = round_int(CONFIG['GenerateKeyboard']['FontSpacing'] * MULTIPLIER)

_CIRCLE = {
    'TopRight': calculate_circle(KEY_CORNER_RADIUS, 'TopRight'),
    'TopLeft': calculate_circle(KEY_CORNER_RADIUS, 'TopLeft'),
    'BottomRight': calculate_circle(KEY_CORNER_RADIUS, 'BottomRight'),
    'BottomLeft': calculate_circle(KEY_CORNER_RADIUS, 'BottomLeft'),
}


class KeyboardButton(object):
    def __init__(self, x, y, x_len, y_len=None):
        if y_len is None:
            y_len = x_len
        self.x = x
        self.y = y
        self.x_len = x_len
        self.y_len = y_len
        x_range = range(x, x + x_len)
        y_range = range(y, y + y_len)
        
        #Cache range (and fix error with radius of 0)
        i_start = KEY_CORNER_RADIUS + 1
        i_end = -KEY_CORNER_RADIUS or max(x + x_len, y + y_len)
        self.cache = {'x': x_range[i_start:i_end],
                      'y': y_range[i_start:i_end],
                      'x_start': x_range[1:i_start],
                      'y_start': y_range[1:i_start],
                      'x_end': x_range[i_end:],
                      'y_end': y_range[i_end:]}
    
    def _circle_offset(self, x, y, direction):
        if direction == 'TopLeft':
            return (self.x + x + KEY_CORNER_RADIUS, self.y + y + KEY_CORNER_RADIUS)
        if direction == 'TopRight':
            return (self.x + x + self.x_len - KEY_CORNER_RADIUS, self.y + y + KEY_CORNER_RADIUS) 
        if direction == 'BottomLeft':
            return (self.x + x + KEY_CORNER_RADIUS, self.y + y + self.y_len - KEY_CORNER_RADIUS)
        if direction == 'BottomRight':
            return (self.x + x + self.x_len - KEY_CORNER_RADIUS, self.y + y + self.y_len - KEY_CORNER_RADIUS)
            
    def outline(self, border=0, drop_shadow=1):
        coordinates = []
        if not border:
            return coordinates
        
        #Rounded corners
        top_left = [self._circle_offset(x, y, 'TopLeft') for x, y in _CIRCLE['TopLeft']['Outline']]
        top_right = [self._circle_offset(x, y, 'TopRight') for x, y in _CIRCLE['TopRight']['Outline']]
        bottom_left = [self._circle_offset(x, y, 'BottomLeft') for x, y in _CIRCLE['BottomLeft']['Outline']]
        bottom_right = [self._circle_offset(x, y, 'BottomRight') for x, y in _CIRCLE['BottomRight']['Outline']]
        
        #Rounded corner thickness
        #This is a little brute force but everything else I tried didn't work
        r = range(border)
        for x, y in top_left:
            coordinates += [(x-i, y-j) for i in r for j in r]
        for x, y in top_right:
            coordinates += [(x+i, y-j) for i in r for j in r]
        for x, y in bottom_left:
            coordinates += [(x-i, y+j) for i in r for j in r]
        for x, y in bottom_right:
            coordinates += [(x+i, y+j) for i in r for j in r]
            
        #Straight lines
        for i in r:
            coordinates += [(_x, self.y - i) for _x in self.cache['x']]
            coordinates += [(_x, self.y + self.y_len + i) for _x in self.cache['x']]
            coordinates += [(self.x - i, _y) for _y in self.cache['y']]
            coordinates += [(self.x + self.x_len + i, _y) for _y in self.cache['y']]
                
        return coordinates
    
    def fill(self):
        coordinates = []
        
        #Squares
        coordinates += [(x, y) for y in self.cache['y'] for x in self.cache['x']]
        coordinates += [(x, y) for y in self.cache['y'] for x in self.cache['x_start']]
        coordinates += [(x, y) for y in self.cache['y'] for x in self.cache['x_end']]
        coordinates += [(x, y) for y in self.cache['y_start'] for x in self.cache['x']]
        coordinates += [(x, y) for y in self.cache['y_end'] for x in self.cache['x']]
                
        #Corners
        coordinates += [self._circle_offset(x, y, 'TopLeft') for x, y in _CIRCLE['TopLeft']['Area']]
        coordinates += [self._circle_offset(x, y, 'TopRight') for x, y in _CIRCLE['TopRight']['Area']]
        coordinates += [self._circle_offset(x, y, 'BottomLeft') for x, y in _CIRCLE['BottomLeft']['Area']]
        coordinates += [self._circle_offset(x, y, 'BottomRight') for x, y in _CIRCLE['BottomRight']['Area']]
        
        return coordinates


class KeyboardGrid(object):
    FILL_COLOUR = (170, 170, 170)
    OUTLINE_COLOUR = (0, 0, 0)
    def __init__(self, keys_pressed=None, empty_width=None, _new_row=True):
        self.grid = []
        self.empty_width = empty_width
        if _new_row:
            self.new_row()
        self.count_press = keys_pressed['Pressed']
        self.count_time = keys_pressed['Held']
        
    def new_row(self):
        self.grid.append([])
        self.row = self.grid[-1]
        
    def add_key(self, name, width=None, height=None, hide_border=False, custom_colour=None):
        if width is None:
            if name is None and self.empty_width is not None:
                width = self.empty_width
            else:
                width = 1
        if height is None:
            height = 1
        pos_x = IMAGE_PADDING
        _width = int(round(KEY_SIZE * width + KEY_PADDING * max(0, width - 1)))
        _height = int(round(KEY_SIZE * height + KEY_PADDING * max(0, height - 1)))
        _values = {'Dimensions': (_width, _height),
                   'DimensionMultipliers': (width, height),
                   'Name': name,
                   'CustomColour': custom_colour,
                   'HideBorder': hide_border}
        self.row.append(_values)
        #self.row.append([name, (_width, _height), hide_border, custom_colour])

    def generate_coordinates(self, key_names={}):
        image = {'Fill': {}, 'Outline': [], 'Text': []}
        max_offset = {'X': 0, 'Y': 0}
        
        use_linear = CONFIG['GenerateKeyboard']['LinearScale']
        
        use_time = CONFIG['GenerateKeyboard']['DataSet'].lower() == 'time'
        use_count = CONFIG['GenerateKeyboard']['DataSet'].lower() == 'count'
        
        #Setup the colour range
        if use_time:
            values = self.count_time.values()
        elif use_count:
            values = self.count_press.values()
            
        if use_linear:
            exponential = CONFIG['GenerateKeyboard']['LinearExponential']
            max_range = pow(max(values), exponential)
        else:
            pools = sorted(set(values))
            max_range = len(pools) + 1
            lookup = {v: i + 1 for i, v in enumerate(pools)}
            lookup[0] = 0
        
        colours = ColourMap()[CONFIG['GenerateKeyboard']['ColourProfile']]
        colour_range = ColourRange(0, max_range, colours)
        
        #Decide on background colour
        #For now the options are black or while
        if any(i > 128 for i in colours[0]):
            image['Background'] = COLOURS_MAIN['white']
            image['Shadow'] = COLOURS_MAIN['black']
        else:
            image['Background'] = COLOURS_MAIN['black']
            image['Shadow'] = COLOURS_MAIN['white']
        
        y_offset = IMAGE_PADDING
        y_current = 0
        for i, row in enumerate(self.grid):
            x_offset = IMAGE_PADDING
            
            for values in row:
            
                x, y = values['Dimensions']
                hide_background = False
                
                if values['Name'] is not None:
                    count_time = self.count_time.get(values['Name'], 0)
                    count_press = self.count_press.get(values['Name'], 0)
                    if use_time:
                        key_count = count_time
                    elif use_count:
                        key_count = count_press
                    display_name = key_names.get(values['Name'], values['Name'])

                    button_coordinates = KeyboardButton(x_offset, y_offset, x, y)
                    
                    #Calculate colour for key
                    if values['CustomColour'] is None:
                        if use_linear:
                            fill_colour = colour_range[key_count ** exponential]
                        else:
                            fill_colour = colour_range[lookup[key_count]]
                    else:
                        if values['CustomColour'] == False:
                            hide_background = True
                            fill_colour = image['Background']
                        else:
                            fill_colour = values['CustomColour']
                    
                    #Calculate colour for border
                    if get_luminance(*fill_colour) > 128:
                        text_colour = COLOURS_MAIN['black']
                    else:
                        text_colour = COLOURS_MAIN['white']
                    
                    #Store values
                    _values = {'Offset': (x_offset, y_offset),
                               'KeyName': display_name,
                               'Counts': {'press': count_press, 'time': count_time},
                               'Colour': text_colour,
                               'Dimensions': values['DimensionMultipliers']}
                    image['Text'].append(_values)

                    if not values['HideBorder']:
                        image['Outline'] += button_coordinates.outline(KEY_BORDER)
                    if not hide_background:
                        try:
                            image['Fill'][fill_colour] += button_coordinates.fill()
                        except KeyError:
                            image['Fill'][fill_colour] = button_coordinates.fill()
                
                x_offset += KEY_PADDING + x
                y_current = max(y_current, y)

            #Decrease size of empty row
            if row:
                y_offset += KEY_SIZE + KEY_PADDING
            else:
                y_offset += (KEY_SIZE + KEY_PADDING) // 2
            
            max_offset['X'] = max(max_offset['X'], x_offset)
            max_offset['Y'] = max(max_offset['Y'], y_offset)
            y_current -= KEY_SIZE
        
        width = max_offset['X'] + IMAGE_PADDING - KEY_PADDING + 1
        height = max_offset['Y'] + IMAGE_PADDING + y_current - KEY_PADDING * 2 + 1 + DROP_SHADOW_Y
        return ((width, height), image)


def format_amount(value, value_type, max_length=5, min_length=None, decimal_units=False):
    """Format the count for something that will fit on a key."""
    if value_type == 'press':
        return shorten_number(value, limit=max_length, sig_figures=min_length, decimal_units=decimal_units)
    elif value_type == 'time':
        return ticks_to_seconds(value, 60, output_length=1, allow_decimals=False, short=True)

        
def shorten_number(n, limit=5, sig_figures=None, decimal_units=True):
    """Set a number over a certain length to something shorter.
    For example, 2000000 can be shortened to 2m.
    The numbers will be kept as long as possible, 
    so "2000k" will override "2m" at a length of 5.
    Set a minimum length to ensure it has a certain number of digits.
    Disable decimal_units if you do not want this enforced on units (such as 15.000000).
    """
    if sig_figures is None:
        sig_figures = limit - 1
    limits = [''] + list('kmbtq')
    i = 0
    str_n = str(int(n))
    max_length = max(limit, 4)
    
    try:
        #Reduce the number until it fits in the required space
        while True:
            prefix = limits[i]
            num_length = len(str_n)
            if num_length < max_length or not prefix and num_length <= max_length:
                break
            i += 1
            str_n = str_n[:-3]
        result = n / 10 ** (i*3)
        
        #Return whole number if decimal units are disabled
        if not decimal_units and not prefix:
            return str(int(result))
        
        #Convert to string if result is too large for a float
        overflow = 'e+' in str(result)
        if overflow:
            result = str(int(result)) + '.0'
            
        #Format the decimals based on required significant figures
        if overflow:
            int_length = len(result)
        else:
            int_length = len(str(int(result)))
        
        #Set maximum (and minimum) number of decimal points)
        max_decimals = max(0, sig_figures - int_length - bool(prefix))
        if sig_figures and max_decimals:
            result_parts = str(result).split('.')
            decimal = str(round(float('0.{}'.format(result_parts[1])), max_decimals))[2:]
            extra_zeroes = max_decimals - len(decimal)
            result = '{}.{}{}'.format(result_parts[0], decimal, '0' * extra_zeroes)
        else:
            if overflow:
                result = result.split('.')[0]
            else:
                result = int(result)
        return '{}{}'.format(result, prefix)
    
    #If the number goes out of limits, return that it's infinite
    except IndexError:
        return 'inf'

        
class DrawKeyboard(object):
    def __init__(self, profile_name):
        self.name = profile_name
        print 'Loading profile...'
        self.reload()
    
    def reload(self):
        profile = load_program(self.name)
        self.key_counts = profile['Keys']['All']
        self.ticks = profile['Ticks']['Total']
        self.keys = self._get_key_names()
        self.grid = self._create_grid()
    
    def _create_grid(self):
        print 'Building keyboard from layout...'
        grid = KeyboardGrid(self.key_counts, _new_row=False)
        layout = Language().get_keyboard_layout()
        for row in layout:
            grid.new_row()
            for name, width, height in row:
                if name == '__STATS__':
                    hide_border = True
                    custom_colour = False
                else:
                    hide_border = False
                    custom_colour = None
                grid.add_key(name, width, height, hide_border=hide_border, custom_colour=custom_colour)
        return grid
    
    def _get_key_names(self):
        all_strings = Language().get_strings(_new=True)
        return all_strings['keyboard']['key']
    
    def calculate(self):
        print 'Calculating pixels...'
        (width, height), coordinate_dict = self.grid.generate_coordinates(self.keys)
        return {'Width': width,
                'Height': height,
                'Coordinates': coordinate_dict}
    
    def draw_image(self, file_path, font='arial.ttf'):
        data = self.calculate()
        
        #Create image object
        image = Image.new('RGB', (data['Width'], data['Height']))
        image.paste(data['Coordinates']['Background'], (0, 0, data['Width'], data['Height']))
        pixels = image.load()

        #Add drop shadow
        shadow = (64, 64, 64)
        if (DROP_SHADOW_X or DROP_SHADOW_Y) and data['Coordinates']['Background'] == (255, 255, 255, 255):
            print 'Adding shadow...'
            shadow_colour = tuple(int(pow(i + 30, 0.9625)) for i in data['Coordinates']['Shadow'])
            for colour in data['Coordinates']['Fill']:
                for x, y in data['Coordinates']['Fill'][colour]:
                    pixels[DROP_SHADOW_X+x, DROP_SHADOW_Y+y] = shadow
    
        #Fill colours
        print 'Colouring keys...'
        for colour in data['Coordinates']['Fill']:
            for x, y in data['Coordinates']['Fill'][colour]:
                pixels[x, y] = colour

        #Draw border
        print 'Drawing outlines...'
        border = tuple(255 - i for i in data['Coordinates']['Background'])
        for x, y in data['Coordinates']['Outline']:
            pixels[x, y] = border
    
        #Draw text
        print 'Adding text...'
        draw = ImageDraw.Draw(image)
        font_key = ImageFont.truetype(font, size=FONT_SIZE_MAIN)
        font_amount = ImageFont.truetype(font, size=FONT_SIZE_STATS)
        
        #Generate stats
        stats = ['Time elapsed: {}'.format(ticks_to_seconds(self.ticks, 60))]
        total_presses = format_amount(sum(self.key_counts['Pressed'].values()), 'press', 
                                      max_length=25, decimal_units=False)
        stats.append('Total key presses: {}'.format(total_presses))
        if CONFIG['GenerateKeyboard']['DataSet'].lower() == 'time':
            stats.append('Colour based on how long keys were pressed for.')
        elif CONFIG['GenerateKeyboard']['DataSet'].lower() == 'count':
            stats.append('Colour based on number of key presses.')
        stats_text = ['{}:'.format(self.name), '\n'.join(stats)]
        
        #Write text to image
        for values in data['Coordinates']['Text']:
            x, y = values['Offset']
            text = values['KeyName']
            text_colour = values['Colour']
            
            #Override for stats text
            if text == '__STATS__':
                draw.text((x, y), stats_text[0], font=font_key, fill=text_colour)
                y += (FONT_SIZE_MAIN + FONT_LINE_SPACING)
                draw.text((x, y), stats_text[1], font=font_amount, fill=text_colour)
                continue
            
            height_multiplier = max(0, values['Dimensions'][1] - 1)
            x += FONT_OFFSET_X
            if not height_multiplier:
                y += FONT_OFFSET_Y
            y += (KEY_SIZE - FONT_SIZE_MAIN + FONT_OFFSET_Y) * height_multiplier
            
            #Ensure each key is at least at a constant height
            if '\n' not in text:
                text += '\n'
                
            draw.text((x, y), text, font=font_key, fill=text_colour)
        
            #Correctly place count at bottom of key
            if height_multiplier:
                y = values['Offset'][1] + (KEY_SIZE + KEY_PADDING) * height_multiplier + FONT_OFFSET_Y

            y += (FONT_SIZE_MAIN + FONT_LINE_SPACING) * (1 + text.count('\n'))
            
            #Here either do count or percent, but not both as it won't fit
            output_type = 'press' #press or time
            max_width = int(10 * values['Dimensions'][0] - 3)
                
            text = format_amount(values['Counts'][output_type], output_type,
                                 max_length=max_width, min_length=max_width-1, decimal_units=False)
            draw.text((x, y), 'x{}'.format(text), font=font_amount, fill=text_colour)

        image.save(file_path, 'PNG')
        print 'Saved image.'
            
            
DrawKeyboard('Default').draw_image('testimage.png')
