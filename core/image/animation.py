"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

class TrackHistory(object):
    def __init__(self, data):
        self.data = data
        raise NotImplementedError
    
    def forward(self):
        raise NotImplementedError

track_history = TrackHistory(data)

while True:
    if track_history.remaining:
        track_history.forward(5)
        RenderImage(track_history).tracks(file_name='history/image.{}.jpg'.format(track_history.index))


#Original working (but messy) way
'''
data = LoadData()
ticks = 0
new_data = LoadData('historytest')
resolutions = set()
for monitor_limit_group in data['HistoryAnimation']['Tracks']:
    monitor_limits = monitor_limit_group[0]
    movement = monitor_limit_group[1:]
    last_pos = None
    
    for coordinate in movement:
        ticks += 1
        
        if last_pos is None:
            mouse_coordinates = [coordinate]
        else:
            mouse_coordinates = [last_pos] + calculate_line(last_pos, coordinate) + [coordinate]
        last_pos = coordinate
            
        for (x, y) in mouse_coordinates:
            
            resolution, (x_offset, y_offset) = monitor_offset((x, y), monitor_limits)
            if resolution not in resolutions:
                resolutions.add(resolution)
                check_resolution(new_data, resolution)
                
            x -= x_offset
            y -= y_offset
            new_data['Resolution'][resolution]['Tracks'][y][x] = ticks
        
        if not ticks % 5:
            r = RenderImage(new_data)
            r.tracks(file_name = 'history/image.{}.jpg'.format(int(ticks / 5)))
            '''