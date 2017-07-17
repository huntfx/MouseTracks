from PIL import Image, ImageFont, ImageDraw

from core.colours import ColourRange, ColourMap


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
    def __init__(self, size, padding, edge, press_count={}):
        self.size = size
        self.padding = padding
        self.edge = edge
        self.grid = []
        self.new_row()
        self.count = press_count
        
    def new_row(self):
        self.grid.append([])
        self.row = self.grid[-1]
        
    def add_button(self, display_name, key_name, width=1, custom_colour=None):
        pos_x = self.edge
        _width = int(round(self.size * width))
        _height = self.size
        self.row.append([display_name, key_name, (_width, _height), custom_colour])

    def generate_coordinates(self):
        image = {'Fill': {}, 'Outline': [], 'Text': []}

        m = max(self.count.values())
        c = ColourRange(0, m, ColourMap()['RedToGreen'])
        
        y_offset = self.edge
        for i, row in enumerate(self.grid):
            x_offset = self.edge
            for j, (display_name, key_name, (x, y), custom_colour) in enumerate(row):

                image['Text'].append(((x_offset, y_offset), display_name))
                
                button_coordinates = KeyboardButton(x_offset, y_offset, x, y)
                image['Outline'] += button_coordinates.outline()

                if custom_colour is not None:
                    fill_colour = custom_colour
                else:
                    try:
                        fill_colour = c[self.count[key_name]]
                    except KeyError:
                        fill_colour = c[0]
                try:
                    image['Fill'][fill_colour] += button_coordinates.fill()
                except KeyError:
                    image['Fill'][fill_colour] = button_coordinates.fill()
                
                x_offset += self.padding + x

            #Decrease size of empty row
            if row:
                y_offset += self.size + self.padding
            else:
                y_offset += (self.size + self.padding) / 2

        return ((x_offset + self.edge, y_offset + self.edge), image)

keys={'A': 50, 'TAB': 2, 'Q': 35, 'S': 15}

k = KeyboardGrid(57, 5, 13, press_count=keys)
k.add_button('tab', 'TAB', 1.5)
k.add_button('q', 'Q', 1)
k.add_button('w', 'W', 1)
k.new_row()
k.new_row()
k.add_button('caps lock', 'CAPSLOCK', 1.6)
k.add_button('a', 'A', 1)
k.add_button('s', 'S', 1)
(width, height), coordinate_dict = k.generate_coordinates()

#Create image object
im = Image.new('RGB', (width, height))
px = im.load()

for colour in coordinate_dict['Fill']:
    for x, y in coordinate_dict['Fill'][colour]:
        px[x, y] = colour
for x, y in coordinate_dict['Outline']:
    px[x, y] = (0, 0, 0)

draw = ImageDraw.Draw(im)
font = ImageFont.truetype('arial.ttf', size=12)
for (x, y), text in coordinate_dict['Text']:
    x += 5
    y += 5
    draw.text((x, y), text, font=font)

im.save('testimage.png', 'PNG')
