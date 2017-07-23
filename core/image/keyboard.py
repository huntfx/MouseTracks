from __future__ import division
from PIL import Image, ImageFont, ImageDraw

from core.colours import ColourRange, ColourMap, get_luminance
from core.compatibility import get_items
from core.config import CONFIG
from core.language import Language
from core.files import load_program
from core.maths import round_int, calculate_circle


MULTIPLIER = CONFIG['GenerateKeyboard']['SizeMultiplier']

KEY_SIZE = round_int(CONFIG['GenerateKeyboard']['KeySize'] * MULTIPLIER)

KEY_CORNER_RADIUS = round_int(CONFIG['GenerateKeyboard']['KeyCornerRadius'] * MULTIPLIER)

KEY_PADDING = round_int(CONFIG['GenerateKeyboard']['KeyPadding'] * MULTIPLIER)

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
        self._c_range = {'x': x_range[i_start:i_end],
                         'y': y_range[i_start:i_end],
                         'x_start': x_range[:i_start],
                         'y_start': y_range[:i_start],
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
            
    def outline(self):
        coordinates = []
        
        #Rounded corners
        coordinates += [self._circle_offset(x, y, 'TopLeft') for x, y in _CIRCLE['TopLeft']['Outline']]
        coordinates += [self._circle_offset(x, y, 'TopRight') for x, y in _CIRCLE['TopRight']['Outline']]
        coordinates += [self._circle_offset(x, y, 'BottomLeft') for x, y in _CIRCLE['BottomLeft']['Outline']]
        coordinates += [self._circle_offset(x, y, 'BottomRight') for x, y in _CIRCLE['BottomRight']['Outline']]
        
        #Straight lines
        coordinates += [(_x, self.y) for _x in self._c_range['x']]
        coordinates += [(_x, self.y + self.y_len) for _x in self._c_range['x']]
        coordinates += [(self.x, _y) for _y in self._c_range['y']]
        coordinates += [(self.x + self.x_len, _y) for _y in self._c_range['y']]

        return coordinates
    
    def fill(self):
        coordinates = []
        
        #Squares
        coordinates += [(x, y) for y in self._c_range['y'] for x in self._c_range['x']]
        coordinates += [(x, y) for y in self._c_range['y'] for x in self._c_range['x_start']]
        coordinates += [(x, y) for y in self._c_range['y'] for x in self._c_range['x_end']]
        coordinates += [(x, y) for y in self._c_range['y_start'] for x in self._c_range['x']]
        coordinates += [(x, y) for y in self._c_range['y_end'] for x in self._c_range['x']]
                
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
        self.row.append([name, (_width, _height), hide_border, custom_colour])

    def generate_coordinates(self, key_names={}):
        image = {'Fill': {}, 'Outline': [], 'Text': []}
        max_offset = {'X': 0, 'Y': 0}
        
        use_linear = CONFIG['GenerateKeyboard']['LinearScale']
        colours = ColourMap()[CONFIG['GenerateKeyboard']['ColourProfile']]
        
        use_time = CONFIG['GenerateKeyboard']['DataSet'] == 'time'
        use_count = CONFIG['GenerateKeyboard']['DataSet'] == 'count'
        
        if use_linear:
            exponential = CONFIG['GenerateKeyboard']['LinearExponential']
            
            if use_time:
                colour_range = ColourRange(0, max(self.count_time.values()) ** exponential, colours)
            elif use_count:
                colour_range = ColourRange(0, max(self.count_press.values()) ** exponential, colours)

        else:
            pools = sorted(set(self.count_time.values()))
            colour_range = ColourRange(0, len(pools) + 1, colours)
            lookup = {v: i for i, v in enumerate(pools)}
            lookup[0] = 0
        
        if get_luminance(*colours[0]) > 128:
            image['Background'] = (255, 255, 255)
        else:
            image['Background'] = (0, 0, 0)
        
        y_offset = IMAGE_PADDING
        y_current = 0
        for i, row in enumerate(self.grid):
            x_offset = IMAGE_PADDING
            for name, (x, y), hide_border, custom_colour in row:
            
                hide_background = False
                
                if name is not None:
                    count_press = self.count_press.get(name, 0)
                    count_time = self.count_time.get(name, 0)
                    display_name = key_names.get(name, name)

                    button_coordinates = KeyboardButton(x_offset, y_offset, x, y)
                    
                    #Calculate colour for key
                    if custom_colour is None:
                        if use_linear:
                            fill_colour = colour_range[count_time ** exponential]
                        else:
                            fill_colour = colour_range[lookup[count_time]]
                    else:
                        if custom_colour == False:
                            hide_background = True
                        else:
                            fill_colour = custom_colour
                    
                    #Calculate colour for border
                    if get_luminance(*fill_colour) > 128:
                        text_colour = (0, 0, 0)
                    else:
                        text_colour = (255, 255, 255)
                    
                    #Store values
                    image['Text'].append(((x_offset, y_offset), display_name, count_press, count_time, text_colour))
                    if not hide_border:
                        image['Outline'] += button_coordinates.outline()
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
        height = max_offset['Y'] + IMAGE_PADDING + y_current - KEY_PADDING + 1
        return ((width, height), image)


        
profile_name = 'Default'
p = load_program(profile_name)
key_counts = p['Keys']['All']

background = (255, 255, 255)




keyboard_layout = Language().get_keyboard_layout()
keyboard = KeyboardGrid(key_counts, _new_row=False)
for row in keyboard_layout:
    keyboard.new_row()
    for name, width, height in row:
        hide_border = name == '__STATS__'
        custom_colour = False if name == '__STATS__' else None
        keyboard.add_key(name, width, height, hide_border=hide_border, custom_colour=custom_colour)

key_names = {}
all_strings = Language().get_strings()
for k, v in get_items(all_strings):
    if k.startswith('K_'):
        key_names[k.replace('K_', '')] = v.replace('\\n', '\n')
#key_names = {}
(width, height), coordinate_dict = keyboard.generate_coordinates(key_names)


#Create image object
im = Image.new('RGB', (width, height))
im.paste(background, (0, 0, width, height))
px = im.load()

for colour in coordinate_dict['Fill']:
    if colour != background:
        for x, y in coordinate_dict['Fill'][colour]:
            px[x, y] = colour

border = tuple(255 - i for i in background)
for x, y in coordinate_dict['Outline']:
    #px[x, y] = border
    px[x, y] = border
    
font = 'arial.ttf'
    
draw = ImageDraw.Draw(im)
font_key = ImageFont.truetype(font, size=FONT_SIZE_MAIN)
font_amount = ImageFont.truetype(font, size=FONT_SIZE_STATS)
for (x, y), text, amount_press, amount_time, text_colour in coordinate_dict['Text']:
    if text == '__STATS__':
        text = '{}:'.format(profile_name)
        draw.text((x, y), text, font=font_key, fill=text_colour)
        y += (FONT_SIZE_MAIN + FONT_LINE_SPACING)
        text = 'Time played: 2 hours and 45 minutes (made up)\nTotal key presses: {}\nColour based on how long keys were pressed for.'.format(sum(key_counts['Pressed'].values()))
        draw.text((x, y), text, font=font_amount, fill=text_colour)
    else:
        x += FONT_OFFSET_X
        y += FONT_OFFSET_Y
        
        #Ensure each key is at least at a constant height
        if '\n' not in text:
            text += '\n'
            
        draw.text((x, y), text, font=font_key, fill=text_colour)   
        y += (FONT_SIZE_MAIN + FONT_LINE_SPACING) * (1 + text.count('\n'))
        
        #Here either do count or percent, but not both as it won't fit
        if amount_press > 99999:
            amount_press /= 1000
            amount_press = '{}k'.format(round(amount_press, 1))
        draw.text((x, y), ' x{}'.format(amount_press), font=font_amount, fill=text_colour)

im.save('testimage.png', 'PNG')
#im.show()
print 'done'

