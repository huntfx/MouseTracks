from PIL import Image, ImageFont, ImageDraw


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
    def __init__(self, size, padding, edge):
        self.size = size
        self.padding = padding
        self.edge = edge
        self.grid = []
        self.new_row()
    def new_row(self):
        self.grid.append([])
        self.row = self.grid[-1]
    def add_button(self, name, amount, width=1, custom_colour=None):
        pos_x = self.edge
        self.row.append([name, amount, (int(round(self.size * width)), self.size), custom_colour])

    def generate_coordinates(self):
        image = {'Fill': {}, 'Outline': [], 'Text': []}
        
        y_offset = self.edge
        for i, row in enumerate(self.grid):
            x_offset = self.edge
            for j, (name, amount, (x, y), custom_colour) in enumerate(row):

                image['Text'].append(((x_offset, y_offset), name))
                
                button_coordinates = KeyboardButton(x_offset, y_offset, x, y)
                image['Outline'] += button_coordinates.outline()

                fill_colour = custom_colour if custom_colour is not None else self.FILL_COLOUR
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
            
k = KeyboardGrid(57, 5, 13)
k.add_button('tab', 5, 1.5)
k.add_button('q', 5, 1, (255, 150, 150))
k.add_button('w', 5, 1)
k.new_row()
k.new_row()
k.add_button('caps lock', 5, 1.6)
k.add_button('a', 5, 1)
k.add_button('s', 5, 1)
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
