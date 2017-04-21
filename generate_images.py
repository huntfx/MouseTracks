from __future__ import division
from PIL import Image
from scipy.ndimage.interpolation import zoom
from scipy.signal import resample
import numpy as np

from _track_files import load_program
from _track_functions import ColourRange

def merge_resolutions(main_data, smoothness=1):
    numpy_arrays = []
    highest_value = None
    lowest_value = None
    max_resolution = (int(1920 * smoothness), int(1080 * smoothness))
    resolutions = main_data.keys()
    
    if any(not isinstance(i, tuple) for i in resolutions) or any(len(i) != 2 for i in resolutions):
        raise ValueError('incorrect resolutions')

    i = 0
    for current_resolution in resolutions:
        i += 1
        print ('Interpolating {}x{} to {}x{}...'
               '({}/{})'.format(*(current_resolution + max_resolution + (i, len(resolutions)))))
        data = main_data[current_resolution]

        #Try find the highest and lowest value
        all_values = set(data.values())
        _lowest_value = min(all_values)
        if lowest_value is None or lowest_value > _lowest_value:
            lowest_value = _lowest_value
        _highest_value = max(all_values)
        if highest_value is None or highest_value < _highest_value:
            highest_value = _highest_value    

        #Build 2D array from data
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

        #Calculate the zoom level needed
        zoom_factor = (int(1080 * smoothness) / current_resolution[1],
                       int(1920 * smoothness) / current_resolution[0])
        
        numpy_arrays.append(zoom(np.array(new_data), zoom_factor, order=1))

    return (lowest_value, highest_value), numpy_arrays

def generate_tracks(value_range, numpy_arrays, colour_list=None):

    print 'Generating mouse tracks...'
    #Set up the list of colours
    if colour_list is None:
        colour_list = [[255, 255, 255], [0, 0, 0]]
    cr = ColourRange(value_range[1] - value_range[0], colour_list)
    
    height_range = range(len(numpy_arrays[0]))
    width_range = range(len(numpy_arrays[0][0]))
    new_data = [[]]
    for y in height_range:
        if new_data[-1]:
            new_data.append([])
        for x in width_range:
            new_data[-1].append(cr.get_colour(max(i[y][x] for i in numpy_arrays)))

    numpy_array = np.array(new_data, dtype=np.uint8)

    im = Image.fromarray(numpy_array)
    im = im.resize(desired_resolution, Image.ANTIALIAS)
    return im
    

#Options
desired_resolution = (2560, 1440)
smoothness = 2
colour_list = [
    [0, 0, 0],
    [255, 255, 255]
]


main_data = load_program('default')

print 'Desired resolution: {}x{}'.format(*desired_resolution)

value_range, numpy_arrays = merge_resolutions(main_data['Tracks'], smoothness)
im = generate_tracks(value_range, numpy_arrays)
im.save('Result/Recent Movement.png')

print 'Finished.'

'''
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
'''
