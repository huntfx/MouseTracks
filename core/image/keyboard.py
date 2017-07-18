from __future__ import division
from PIL import Image, ImageFont, ImageDraw

from core.colours import ColourRange, ColourMap

KB_KEY_SIZE = 65
KB_KEY_PADDING = 8
KB_PADDING = 16
KB_TEXT_SIZE_KEY = 17
KB_TEXT_SIZE_AMOUNT = 12
KB_TEXT_OFFSET = 5
KB_TEXT_HEIGHT = 3

class KeyboardButton(object):
    def __init__(self, x, y, x_len, y_len=None):
        if y_len is None:
            y_len = x_len
        self.x = x
        self.y = y
        self.x_len = x_len
        self.y_len = y_len
        self.x_range = range(x, x + x_len)
        self.y_range = range(y, y + y_len)
        
    def outline(self, trim_corners=True):
        coordinates = [
            (self.x + trim_corners, self.y + trim_corners),
            (self.x + trim_corners, self.y + self.y_len - trim_corners),
            (self.x + self.x_len - trim_corners, self.y + trim_corners),
            (self.x + self.x_len - trim_corners, self.y + self.y_len - trim_corners)
        ]
        coordinates += [(_x, self.y) for _x in self.x_range[1:]]
        coordinates += [(_x, self.y + self.y_len) for _x in self.x_range[1:]]
        coordinates += [(self.x, _y) for _y in self.y_range[1:]]
        coordinates += [(self.x + self.x_len, _y) for _y in self.y_range[1:]]
        return coordinates
    
    def fill(self):
        coordinates = []
        for x in self.x_range[1:]:
            for y in self.y_range[1:]:
                coordinates.append((x, y))
        return coordinates


class KeyboardGrid(object):
    FILL_COLOUR = (170, 170, 170)
    OUTLINE_COLOUR = (0, 0, 0)
    def __init__(self, keys_pressed=None, empty_width=None):
        self.grid = []
        self.empty_width = empty_width
        self.new_row()
        self.count_press = keys_pressed['Pressed']
        self.count_time = keys_pressed['Held']
        
    def new_row(self):
        self.grid.append([])
        self.row = self.grid[-1]
        
    def add_button(self, name, width=None, height=None, hide_border=False):
        if width is None:
            if name is None and self.empty_width is not None:
                width = self.empty_width
            else:
                width = 1
        if height is None:
            height = 1
        pos_x = KB_PADDING
        _width = int(round(KB_KEY_SIZE * width + KB_KEY_PADDING * max(0, width - 1)))
        _height = int(round(KB_KEY_SIZE * height + KB_KEY_PADDING * max(0, height - 1)))
        self.row.append([name, (_width, _height), hide_border])

    def generate_coordinates(self, key_names={}):
        image = {'Fill': {}, 'Outline': [], 'Text': []}
        max_offset = {'X': 0, 'Y': 0}

        m_time = max(self.count_time.values())
        m_press = max(self.count_press.values())
        '''
        single:
        WhiteToYellowLightOrangeToOrangeToOrangeRedToRedDarkRed
        '''
        maps = 'WhiteToBlue', 'WhiteToGreen'
        #maps = 'WhiteToBlue', 'WhiteToYellow'
        
        c_time = ColourRange(0, m_time, ColourMap()[maps[0]])
        c_press = ColourRange(0, m_press, ColourMap()[maps[1]])
        
        y_offset = KB_PADDING
        for i, row in enumerate(self.grid):
            x_offset = KB_PADDING
            for name, (x, y), hide_border in row:


                if name is not None:
                    count_press = self.count_press.get(name, 0)
                    count_time = self.count_time.get(name, 0)
                    display_name = key_names.get(name, name)

                    image['Text'].append(((x_offset, y_offset), display_name, count_press))
                    
                    button_coordinates = KeyboardButton(x_offset, y_offset, x, y)
                    if not hide_border:
                        image['Outline'] += button_coordinates.outline()

                    #fill_colour = c_press[count_press]
                    fill_colour = c_time[count_time]
                    fill_colour = tuple(int(round((i + j) / 2)) for i, j in zip(c_press[count_press], c_time[count_time]))
                    #fill_colour = tuple(i * j // 255 for i, j in zip(c_press[count_press], c_time[count_time]))
                    try:
                        image['Fill'][fill_colour] += button_coordinates.fill()
                    except KeyError:
                        image['Fill'][fill_colour] = button_coordinates.fill()
                
                x_offset += KB_KEY_PADDING + x

            #Decrease size of empty row
            if row:
                y_offset += KB_KEY_SIZE + KB_KEY_PADDING
            else:
                y_offset += (KB_KEY_SIZE + KB_KEY_PADDING) // 2
                
            max_offset['X'] = max(max_offset['X'], x_offset)
            max_offset['Y'] = max(max_offset['Y'], y_offset)

        return ((max_offset['X'] + KB_PADDING, max_offset['Y'] + KB_PADDING), image)

keys={'A': 50, 'TAB': 2, 'Q': 35, 'S': 15, 'L': 100}
key_names = {
    'CAPSLOCK': 'Caps Lock',
    'COMMA': '<\n,',
    'FULLSTOP': '>\n.',
    'FORWARDSLASH': '?\n/',
    'BACKSLASH': '\\',
    'PRINTSCREEN': 'Print\nScreen',
    'SCROLLLOCK': 'Scroll\nLock',
    'PAUSE': 'Pause\nBreak'
}

from core.files import load_program
profile_name = 'Default'
p = load_program(profile_name)

k = KeyboardGrid(p['Keys']['All'], empty_width=0.624)
k.add_button('ESC')
k.add_button(None)
k.add_button('F1')
k.add_button('F2')
k.add_button('F3')
k.add_button('F4')
k.add_button(None)
k.add_button('F5')
k.add_button('F6')
k.add_button('F7')
k.add_button('F8')
k.add_button(None)
k.add_button('F9')
k.add_button('F10')
k.add_button('F11')
k.add_button('F12', 0.99)
k.add_button(None)
k.add_button('PRINTSCREEN')
k.add_button('SCROLLLOCK')
k.add_button('PAUSE')
k.add_button(None)
k.add_button('__STATS__', 4, 1.25, hide_border=True)
k.new_row()
k.new_row()
k.add_button('TILDE')
k.add_button('1')
k.add_button('2')
k.add_button('3')
k.add_button('4')
k.add_button('5')
k.add_button('6')
k.add_button('7')
k.add_button('8')
k.add_button('9')
k.add_button('0')
k.add_button('MINUS')
k.add_button('EQUALS')
k.add_button('BACKSPACE', 2)
k.add_button(None)
k.add_button('INSERT')
k.add_button('HOME')
k.add_button('PAGEUP')
k.add_button(None)
k.add_button('NUMLOCK')
k.add_button('/')
k.add_button('*')
k.add_button('-')
k.new_row()
k.add_button('Tab', 1.5)
k.add_button('Q', 1)
k.add_button('W', 1)
k.add_button('E', 1)
k.add_button('R', 1)
k.add_button('T', 1)
k.add_button('Y', 1)
k.add_button('U', 1)
k.add_button('I', 1)
k.add_button('O', 1)
k.add_button('P', 1)
k.add_button('[', 1)
k.add_button(']', 1)
k.add_button('BACKSLASH', 1.49)
k.add_button(None)
k.add_button('DELETE')
k.add_button('END')
k.add_button('PAGEDOWN')
k.add_button(None)
k.add_button('7')
k.add_button('8')
k.add_button('9')
k.add_button('+', 1, 2)
k.new_row()
k.add_button('CAPSLOCK', 2)
k.add_button('A', 1)
k.add_button('S', 1)
k.add_button('D', 1)
k.add_button('F', 1)
k.add_button('G', 1)
k.add_button('H', 1)
k.add_button('J', 1)
k.add_button('K', 1)
k.add_button('L', 1)
k.add_button(':', 1)
k.add_button('\'', 1)
k.add_button('ENTER', 2)
k.add_button(None)
k.add_button(None, 1)
k.add_button(None, 1)
k.add_button(None, 1)
k.add_button(None)
k.add_button('4')
k.add_button('5')
k.add_button('6')
k.add_button(None, 1)
k.new_row()
k.add_button('LSHIFT', 2.4)
k.add_button('Z', 1)
k.add_button('X', 1)
k.add_button('C', 1)
k.add_button('V', 1)
k.add_button('B', 1)
k.add_button('N', 1)
k.add_button('M', 1)
k.add_button('COMMA', 1)
k.add_button('FULLSTOP', 1)
k.add_button('FORWARDSLASH', 1)
k.add_button('RSHIFT', 2.6)
k.add_button(None)
k.add_button(None, 1)
k.add_button('UP', 1)
k.add_button(None, 1)
k.add_button(None)
k.add_button('1')
k.add_button('2')
k.add_button('3')
k.add_button('ENTER', 1, 2)
k.new_row()
k.add_button('LCTRL', 1.3)
k.add_button('LWIN', 1.3)
k.add_button('LALT', 1.3)
k.add_button('SPACE', 5.89)
k.add_button('RALT', 1.3)
k.add_button('RWIN', 1.3)
k.add_button('MENU', 1.3)
k.add_button('RCTRL', 1.3)
k.add_button(None)
k.add_button('LEFT', 1)
k.add_button('DOWN', 1)
k.add_button('RIGHT', 1)
k.add_button(None)
k.add_button('INSERT', 2)
k.add_button('DELETE')
(width, height), coordinate_dict = k.generate_coordinates(key_names)

#Create image object
im = Image.new('RGB', (width, height))
im.paste((255, 255, 255), (0, 0, width, height))
px = im.load()

for colour in coordinate_dict['Fill']:
    for x, y in coordinate_dict['Fill'][colour]:
        px[x, y] = colour

colour = (0, 0, 0)
for x, y in coordinate_dict['Outline']:
    px[x, y] = colour
    
draw = ImageDraw.Draw(im)
font_key = ImageFont.truetype('arial.ttf', size=KB_TEXT_SIZE_KEY)
font_amount = ImageFont.truetype('arial.ttf', size=KB_TEXT_SIZE_AMOUNT)
for (x, y), text, amount in coordinate_dict['Text']:
    if text == '__STATS__':
        text = '{}:'.format(profile_name)
        draw.text((x, y), text, font=font_key, fill=colour)
        y += (KB_TEXT_SIZE_KEY + KB_TEXT_HEIGHT)
        text = 'Time played: 2 hours and 45 minutes (made up)\nTotal key presses: {}\nColour based on how long keys were pressed for.'.format(sum(p['Keys']['All']['Pressed'].values()))
        draw.text((x, y), text, font=font_amount, fill=colour)
    else:
        x += KB_TEXT_OFFSET
        y += KB_TEXT_OFFSET
        draw.text((x, y), text, font=font_key, fill=colour)   
        y += (KB_TEXT_SIZE_KEY + KB_TEXT_HEIGHT) * (1 + text.count('\n'))
        draw.text((x, y), ' x{}'.format(amount), font=font_amount, fill=colour)

im.save('testimage.png', 'PNG')
