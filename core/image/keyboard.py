from PIL import Image, ImageFont, ImageDraw

from core.colours import ColourRange, ColourMap

KB_KEY_SIZE = 65
KB_KEY_PADDING = 8
KB_PADDING = 13
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
    def __init__(self, press_count={}):
        self.grid = []
        self.new_row()
        self.count = press_count
        
    def new_row(self):
        self.grid.append([])
        self.row = self.grid[-1]
        
    def add_button(self, name, width=1, custom_colour=None):
        pos_x = KB_PADDING
        _width = int(round(KB_KEY_SIZE * width))
        _height = KB_KEY_SIZE
        self.row.append([name, (_width, _height), custom_colour])

    def generate_coordinates(self, key_names={}):
        image = {'Fill': {}, 'Outline': [], 'Text': []}
        max_offset = {'X': 0, 'Y': 0}

        m = max(self.count.values())
        c = ColourRange(0, m, ColourMap()['WhiteToGreen'])
        
        y_offset = KB_PADDING
        for i, row in enumerate(self.grid):
            x_offset = KB_PADDING
            for j, (name, (x, y), custom_colour) in enumerate(row):

                amount = self.count.get(name, 0)
                display_name = key_names.get(name, name)
                
                image['Text'].append(((x_offset, y_offset), display_name, amount))
                
                button_coordinates = KeyboardButton(x_offset, y_offset, x, y)
                image['Outline'] += button_coordinates.outline()

                if custom_colour is not None:
                    fill_colour = custom_colour
                else:
                    fill_colour = c[amount]
                try:
                    image['Fill'][fill_colour] += button_coordinates.fill()
                except KeyError:
                    image['Fill'][fill_colour] = button_coordinates.fill()
                
                x_offset += KB_KEY_PADDING + x

            #Decrease size of empty row
            if row:
                y_offset += KB_KEY_SIZE + KB_KEY_PADDING
            else:
                y_offset += (KB_KEY_SIZE + KB_KEY_PADDING) / 2
                
            max_offset['X'] = max(max_offset['X'], x_offset)
            max_offset['Y'] = max(max_offset['Y'], y_offset)

        return ((max_offset['X'] + KB_PADDING, max_offset['Y'] + KB_PADDING), image)

keys={'A': 50, 'TAB': 2, 'Q': 35, 'S': 15, 'L': 100}
key_names = {
    'CAPSLOCK': 'Caps Lock',
    'COMMA': ',',
    'FULLSTOP': '.',
    'FORWARDSLASH': '/',
    'BACKSLASH': '\\'
}

k = KeyboardGrid(keys)
k.add_button('Tab', 1.7)
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
k.add_button('m', 1)
k.add_button('m', 1)
k.new_row()
k.add_button('CAPSLOCK', 2.3)
k.add_button('A', 1)
k.add_button('S', 1)
k.add_button('D', 1)
k.add_button('F', 1)
k.add_button('G', 1)
k.add_button('H', 1)
k.add_button('J', 1)
k.add_button('K', 1)
k.add_button('L', 1)
k.new_row()
k.add_button('LSHIFT', 1.5)
k.add_button('BACKSLASH', 1)
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
(width, height), coordinate_dict = k.generate_coordinates(key_names)

#Create image object
im = Image.new('RGB', (width, height))
im.paste((255, 255, 255), (0, 0, width, height))
px = im.load()

for colour in coordinate_dict['Fill']:
    for x, y in coordinate_dict['Fill'][colour]:
        px[x, y] = colour
for x, y in coordinate_dict['Outline']:
    px[x, y] = (0, 0, 0)
    
draw = ImageDraw.Draw(im)
font_key = ImageFont.truetype('arial.ttf', size=KB_TEXT_SIZE_KEY)
font_amount = ImageFont.truetype('arial.ttf', size=KB_TEXT_SIZE_AMOUNT)
for (x, y), text, amount in coordinate_dict['Text']:
    x += KB_TEXT_OFFSET
    y += KB_TEXT_OFFSET
    draw.text((x, y), text, font=font_key, fill=(0, 0, 0))
    y += KB_TEXT_SIZE_KEY + KB_TEXT_HEIGHT
    draw.text((x, y), ' x{}'.format(amount), font=font_amount, fill=(0, 0, 0))

im.save('testimage.png', 'PNG')
