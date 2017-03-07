from __future__ import division
from PIL import Image
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage.filters import gaussian_filter
import os
import FileDialog
from mt_core import FILE, DataStore, ColourRange

def sort_by_value(d):
    return [(k, v) for i in sorted(set(d.values()))[::-1]
                   for k, v in d.iteritems()
            if v == i]

def plot(data, save_path, resolution):
    colors = [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0.75), (0, 1, 0), (0.75, 1, 0),
              (1, 1, 0), (1, 0.8, 0), (1, 0.7, 0), (1, 0, 0)]

    cm = LinearSegmentedColormap.from_list('sample', colors)
    plt.figure(figsize=(resolution[0] / resolution[1], 1))
    plt.imshow(data, cmap=cm)
    plt.xticks([])
    plt.yticks([])
    plt.xlabel('')
    plt.ylabel('')
    plt.tight_layout(0)
    plt.savefig(save_path, dpi=resolution[1])
    plt.close()

    
class SaveResult(object):
    def __init__(self, file_name, resolution=(1920, 1080)):
        self.file = file_name
        self.resolution = resolution
        self.reload_data()

    def reload_data(self):
        self.data = DataStore(self.file).data

    def merge_resolutions(self, name):
        new_data = {}
        for res, res_data in self.data.iteritems():
            if not isinstance(res, tuple):
                continue
            width_multiply = self.resolution[0] / res[0]
            height_multiply = self.resolution[1] / res[1]
            for coordinate, value in res_data[name].iteritems():
                new_coordinate = (int(round(coordinate[0] * width_multiply)),
                                  int(round(coordinate[1] * height_multiply)))
                try:
                    if name == 'Movement':
                        new_data[new_coordinate] = max(new_data[new_coordinate], value)
                    else:
                        new_data[new_coordinate] += value
                except KeyError:
                    new_data[new_coordinate] = value
        return new_data

    def movement(self, max_brightness=255, min_brightness=0):
        w, h = self.resolution
        new_data = self.merge_resolutions('Movement')

        all_values = set(v for k, v in new_data.iteritems())
        lowest_value = min(all_values)
        highest_value = max(all_values)
        current_range = highest_value - lowest_value
        brightness_range = max_brightness - min_brightness
        print 'Newest value: {}'.format(highest_value)
        print 'Oldest value: {}'.format(lowest_value)

        colour_list = [
            [255, 255, 255],
            [255, 128, 255],
            [128, 128, 255],
            [128, 255, 128],
            [255, 255, 0],
            [255, 64, 64],
            [64, 255, 255]
        ]
        
        colour_list = [
            [255, 0, 255],
            [128, 64, 255],
            [0, 0, 255],
            [0, 255, 0],
            [255, 255, 0],
            [255, 196, 0],
            [255, 0, 0]
        ]
        colour_list = [
            [255, 255, 255],
            [0, 0, 0]
        ]
        c = ColourRange(highest_value - lowest_value, colour_list)
        background = (255, 255, 255)
        #background = (0, 0, 0)
        
        #Convert into image array
        im = Image.new('RGB', self.resolution)
        px = im.load()
        
        height_range = range(h)
        width_range = range(w)
        for y in height_range:
            for x in width_range:
                
                try:
                    current_value = new_data[(x, y)]
                except KeyError:
                    px[x, y] = background
                else:
                    result = c.get_colour(current_value)
                    px[x, y] = result

        im.save('Result/Recent Movement.png')


    def location(self):
        w, h = self.resolution
        heatmap = np.zeros(h * w).reshape((h, w))
        new_data = self.merge_resolutions('Location')
        
        all_values = set(v for k, v in new_data.iteritems())
        lowest_value = min(all_values)
        highest_value = max(all_values)
        print 'Lowest value: {}'.format(lowest_value)
        print 'Highest value: {}'.format(highest_value)
        
        height_range = range(h)
        width_range = range(w)
        for x in width_range:
            for y in height_range:
                try:
                    heatmap[y][x] = new_data[(x, y)]
                except KeyError:
                    pass
        heatmap = gaussian_filter(heatmap, sigma=10)
        plot(heatmap, 'Result/Movement Heatmap.jpg', self.resolution)

    def clicks(self):
        w, h = self.resolution
        heatmap = np.zeros(h * w).reshape((h, w))
        new_data = self.merge_resolutions('Clicks')
        
        height_range = range(h)
        width_range = range(w)
        for x in width_range:
            for y in height_range:
                try:
                    heatmap[y][x] = new_data[(x, y)]
                except KeyError:
                    pass
        heatmap = gaussian_filter(heatmap, sigma=10)
        plot(heatmap, 'Result/Click Heatmap.jpg', self.resolution)

    def keys(self):
        
        spaces_needed = max(len(i) for i in self.data['Keys'].keys()) + 1
        output_string = []
        for key, count in sort_by_value(self.data['Keys']):
            output_string.append('{}{}{}'.format(key, ' ' * (spaces_needed - len(key)), count))

        with open('Result/Keystrokes.txt', 'w') as f:
            f.write('\r\n'.join(output_string))

if __name__ == '__main__':
    FILE = 'MouseTrack.data'
    print 'Loading file: {}'.format(FILE)
    output_resolution = (1920, 1080)
    save = SaveResult(FILE, output_resolution)
    try: 
        os.makedirs('Result')
    except OSError:
        if not os.path.isdir('Result'):
            raise
    print 'Calculating keystrokes...'
    save.keys()
    print 'Generating location image...'
    save.movement()
    print 'Generating location heatmap...'
    save.location()
    print 'Generating click heatmap...'
    save.clicks()
    print 'Done.'
