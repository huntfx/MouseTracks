#This is very unfinished currently

from __future__ import division
from PIL import Image
from scipy.ndimage.interpolation import zoom
from scipy.signal import resample
import numpy as np

from _track_files import load_program
from _track_functions import ColourRange


smoothness = 2

max_brightness = 240
min_brightness = 0
brightness_range = max_brightness - min_brightness
colour_list = [
    [255, 255, 255],
    [0, 0, 0]
]

main_data = load_program('default')

desired_resolution = (2560, 1440)
print 'Desired resolution: {}x{}'.format(*desired_resolution)

numpy_arrays = []
highest_value = None
lowest_value = None
for current_resolution in main_data['Tracks'].keys():
    print 'Current resolution: {}x{}'.format(*current_resolution)
    data = main_data['Tracks'][current_resolution]

    all_values = set(data.values())
    _lowest_value = min(all_values)
    if lowest_value is None or lowest_value > _lowest_value:
        lowest_value = _lowest_value
    _highest_value = max(all_values)
    if highest_value is None or highest_value < _highest_value:
        highest_value = _highest_value    

    new_data = []
    width_range = range(current_resolution[0])
    height_range = range(current_resolution[1])
    for y in height_range:
        new_data.append([])
        for x in width_range:
            try:
                new_data[-1].append(data[(x, y)])
            except KeyError:
                new_data[-1].append(0)

    print 'Reformatted data'

    zoom_factor = (int(1080 * smoothness) / current_resolution[1],
                   int(1920 * smoothness) / current_resolution[0])

    numpy_arrays.append(zoom(np.array(new_data), zoom_factor, order=1))
    print 'Interpolated data to new resolution'

print 'Newest value: {}'.format(highest_value)
print 'Oldest value: {}'.format(lowest_value)
c = ColourRange(highest_value - lowest_value, colour_list)

print 'Generating image...'
height_range = range(int(1080 * smoothness))
width_range = range(int(1920 * smoothness))
new_data = [[]]
for y in height_range:
    if new_data[-1]:
        new_data.append([])
    for x in width_range:
        #new_data[-1].append(c.get_colour(numpy_image_data[y][x]))
        new_data[-1].append(c.get_colour(max(i[y][x] for i in numpy_arrays)))

numpy_array = np.array(new_data, dtype=np.uint8)

im = Image.fromarray(numpy_array)
im = im.resize(desired_resolution, Image.ANTIALIAS)
im.save('Result/Recent Movement.png')
print 'done'
