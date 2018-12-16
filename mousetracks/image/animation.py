"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Use track history to make an image sequence

from __future__ import division

from .main import RenderImage
from ..utils.compatibility import range
from ..files import LoadData
from ..utils.maths import calculate_line
from ..track.background import check_resolution, monitor_offset


class TrackHistory(object):
    """Turn track history into an image sequence for animation.

    TODO: Improve render options:
        Get filename from config
        Auto select sequence number
        Ask for colour profile
        Auto select output resolution (since it can change)
    """
    _CACHE = {'Steps': {}}
    def __init__(self, data):
        self.data = data
        self._track_history = [tuple(i) for i in self.data['HistoryAnimation']['Tracks']]
        self._counts = [len(i)-1 for i in self.data['HistoryAnimation']['Tracks']]
        self._total = sum(self._counts)
        self.reset()
    
    def _step_range(self, steps):
        try:
            return self._CACHE['Steps'][steps]
        except KeyError:
            self._CACHE['Steps'][steps] = list(range(steps))
            return self._CACHE['Steps'][steps]

    def _next_resolution(self):
        try:
            self._index += 1
        except AttributeError:
            self._index = 0
        self._current = 0

        try:
            new_resolution = self._track_history[self._index][0]
        except IndexError:
            return False
        
        self._resolution['Current'] = new_resolution
        return True

    def _step(self):
        """Step forward a single frame."""
        coordinate = self._track_history[self._index][self._current + 1]

        #Calculate line between points
        if self._last_pos is None:
            mouse_coordinates = [coordinate]
        else:
            mouse_coordinates = [self._last_pos] + calculate_line(self._last_pos, coordinate) + [coordinate]
        self._last_pos = coordinate

        #Add to data
        for (x, y) in mouse_coordinates:
            
            try:
                try:
                    resolution, (x_offset, y_offset) = monitor_offset((x, y), self._resolution['Current'])
                except ValueError:
                    #TODO: Application resolution requires [var[0]], the other types don't, need to edit all of stored history to fix
                    resolution, (x_offset, y_offset) = monitor_offset((x, y), [self._resolution['Current'][0]])
            
            #Mouse outside bounds
            except TypeError:
                continue

            if resolution not in self._resolution['All']:
                self._resolution['All'].add(resolution)
                check_resolution(self._data, resolution)
                
            self._data['Resolution'][resolution]['Tracks'][y-y_offset][x-x_offset] = self._count
        
        self._current += 1
        self._count += 1

    def step(self, steps, render_file=False):
        """Step forward any number of steps.
        Uses recursion to handle overflow if too many steps.
        """
        print('Current history index: {}/{}'.format(self._count, self._total))
        distance_to_resolution = self._counts[self._index] - self._current

        #All steps are within the current resolution
        if distance_to_resolution > steps:
            for step in self._step_range(steps):
                self._step()
        
        #Resolution changes at some point
        else:
            steps, remaining_steps = distance_to_resolution, steps - distance_to_resolution
            for step in self._step_range(steps):
                self._step()
            if self._next_resolution():
                self.step(remaining_steps)
        
        #Render image
        if render_file:
            self._render('{}.{}.jpg'.format(render_file, int(self._count//steps)))

    def reset(self):
        """Set the animation back to frame 1 and reset any variables."""
        self._data = LoadData(empty=True)
        self._current = self._count = 0
        self._last_pos = None
        self._resolution = {'All': set(),
                            'Current': None}
        self._next_resolution()
    
    def _render(self, file_name):
        #TODO: Ask user for colour map, automatically do filename.[n].[filetype] from config, divide or multiply [n]
        RenderImage(self._data).tracks(file_name=file_name)

    @property
    def remaining(self):
        """How many steps are remaining until completion.
        Can be used in a while loop.
        """
        return self._total - self._count


#Example use
if __name__ == '__main__' or True:
    data = LoadData()
    track_history = TrackHistory(data)

    from ..config.settings import CONFIG
    if not CONFIG['GenerateTracks']['ColourProfile']:
        CONFIG['GenerateTracks']['ColourProfile'] = 'Citrus'

    while track_history.remaining:
        track_history.step(50, render_file='D:/Peter/Documents/Github/MouseTracks/history/image')