from __future__ import division
from threading import Thread
import multiprocessing
#Thread = multiprocessing.Process #swap to multi processing
import cPickle
import base64
import time
import os

SAVE = False

FILE = 'MouseTrack.data'

class DataStore(object):
    """Load and save the file/data."""
    def __init__(self, file_name):
        self.file = file_name
        self.reload()
        
    def reload(self):
        """Replace the current data with the data from the file."""
        try:
            with open(self.file, 'r') as f:
                data = f.read()
            self.data = cPickle.loads(base64.b64decode(data))
        except (IOError, TypeError, EOFError):
            self.data = {}
            
    def save(self, join=False):
        if SAVE:
            return
        
        t = Thread(target=self._save)
        t.start()
        if join:
            t.join()
            
    def _save(self):
        """Copy the temporary dictionary to the actual dictionary and
        save the file.
        As this could take a long time, and the script should stay
        running, this is run in a background thread.
        """
        print 'Writing recent data to main dictionary (sorry, could take a while)...'
        SAVE = True
        '''
        data_copy = {k: v for k, v in self.data.iteritems()}
        self.data = {}
        for res, data in data_copy.iteritems():
            for name, coordinates in data.iteritems():
                for coordinate in coordinates.keys():
                    count = coordinates[coordinate]
                    try:
                        if name == 'Movement':
                            current_value = self._data[res][name][coordinate]
                            self._data[res][name][coordinate] = max(current_value, count)
                        else:
                            self._data[res][name][coordinate] += count
                    except KeyError:
                        try:
                            self._data[res][name][coordinate] = count
                        except KeyError:
                            try:
                                self._data[res][name] = {coordinate: count}
                            except KeyError:
                                self._data[res] = {name: {coordinate: count}}
        '''
        print 'Serialising data...'
        writeable_data = base64.b64encode(cPickle.dumps(self.data))
        current_time = int(time.time())
        print 'Saving file...'
        temp_name = '{}.{}'.format(self.file, current_time)
        old_name = '{}.old'.format(self.file)
        try:
            with open(temp_name, 'w') as f:
                f.write(writeable_data)
            try:
                os.remove(old_name)
            except WindowsError:
                pass
            try:
                os.rename(FILE, old_name)
            except WindowsError:
                pass
            try:
                os.rename(temp_name, FILE)
            except WindowsError:
                print 'Failed to save file.'
                try:
                    os.remove(temp_name)
                except WindowsError:
                    pass
            else:
                print 'Finished saving.'
        except IOError:
            print 'Unable to save file, make sure this has the correct permissions.'
        SAVE = False
        
    def read(self):
        return {k: v for k, v in self.data.iteritems()}


class RefreshRateLimiter(object):
    def __init__(self, min_time):
        self.time = time.time()
        self.frame_time = min_time

    def __enter__(self):
        return self

    def __exit__(self, *args):
        time.sleep(max(0, self.frame_time - time.time() + self.time))


def calculate_line(start, end):
    """Calculates path in terms of pixels between two points.
    Does not include the start and end point.
    """
    result = []
    
    #Return nothing if the two points are the same
    if start == end:
        return result

    difference = (end[0] - start[0], end[1] - start[1])
    
    #Check if the points are on the same axis
    if not difference[0]:
        if difference[1] > 1:
            for i in xrange(1, difference[1]):
                result.append((start[0], start[1] + i))
        elif difference[1] < -1:
            for i in xrange(1, -difference[1]):
                result.append((start[0], start[1] - i))
        return result
    if not difference[1]:
        if difference[0] > 1:
            for i in xrange(1, difference[0]):
                result.append((start[0] + i, start[1]))
        elif difference[0] < -1:
            for i in xrange(1, -difference[0]):
                result.append((start[0] - i, start[1]))
        return result
    
    slope = difference[1] / difference[0]
    
    count = slope
    x, y = start
    x_neg = -1 if difference[0] < 0 else 1
    y_neg = -1 if difference[1] < 0 else 1
    i = 0
    while True:
        i += 1
        if i > 100000:
            raise ValueError('failed to find path between {}, {}'.format(start, end))
        
        #If y > x and both pos or both neg
        if slope >= 1 or slope <= 1:
            if count >= 1:
                y += y_neg
                count -= 1
            elif count <= -1:
                y += y_neg
                count += 1
            else:
                x += x_neg
                count += slope
                
        # If y < x and both pos or both neg
        elif slope:
            if count >= 1:
                y += y_neg
                count -= 1
            elif count <= -1:
                y += y_neg
                count += 1
            if -1 <= count <= 1:
                x += x_neg
            count += slope
            
        coordinate = (x, y)
        if coordinate == end:
            return result
        result.append(coordinate)
        
        #Quick fix since values such as x(-57, -53) y(-22, -94) are one off
        #and I can't figure out how to make it work
        if end[0] in (x-1, x, x+1) and end[1] in (y-1, y, y+1):
            return result

class ColourRange(object):
    def __init__(self, amount, colours):
        self.amount = amount - 1
        self.colours = colours
        self._colour_len = len(colours) - 1
        if isinstance(colours, (tuple, list)):
            if all(isinstance(i, (tuple, list)) for i in colours):
                if len(set(len(i) for i in colours)) == 1:
                    return
        raise TypeError('invalid list of colours')

    def get_colour(self, n, as_int=True):
        n = min(self.amount, max(n, 0))
        
        value = (n * self._colour_len) / self.amount
        base_value = int(value)

        base_colour = self.colours[base_value]
        try:
            mix_colour = self.colours[base_value + 1]
        except IndexError:
            mix_colour = base_colour

        difference = value - base_value
        difference_reverse = 1 - difference
        base_colour = [i * difference_reverse for i in base_colour]
        mix_colour = [i * difference for i in mix_colour]
        if as_int:
            return tuple(int(i + j) for i, j in zip(base_colour, mix_colour))
        else:
            return tuple(i + j for i, j in zip(base_colour, mix_colour))
