"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Simple calculation based functions

from __future__ import division


def find_distance(p1, p2=None, decimal=False):
    """Find the distance between two (x, y) coordinates."""
    if p2 is None:
        return (0, 0.0)[decimal]
    distance = ((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2) ** 0.5
    if decimal:
        return distance
    return int(round(distance))


def calculate_line(start, end):
    """Calculates path in terms of pixels between two points.
    Does not include the start and end point.
    """
    result = []
    start = (round_int(start[0]), round_int(start[1]))
    end = (round_int(end[0]), round_int(end[1]))
    
    #Return nothing if the two points are the same
    if start == end:
        return result

    difference = (end[0] - start[0], end[1] - start[1])
    
    #Check if the points are on the same axis
    if not difference[0]:
        if difference[1] > 1:
            for i in range(1, difference[1]):
                result.append((start[0], start[1] + i))
        elif difference[1] < -1:
            for i in range(1, -difference[1]):
                result.append((start[0], start[1] - i))
        return result
    if not difference[1]:
        if difference[0] > 1:
            for i in range(1, difference[0]):
                result.append((start[0] + i, start[1]))
        elif difference[0] < -1:
            for i in range(1, -difference[0]):
                result.append((start[0] - i, start[1]))
        return result
    
    #Step along line by pixel until end is reached
    slope = difference[1] / difference[0]
    count = slope
    x, y = start
    x_neg = -1 if difference[0] < 0 else 1
    y_neg = -1 if difference[1] < 0 else 1
    i = 0
    while True:
        i += 1
        
        #Stop if it appears to be an infinite loop
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

            
def calculate_circle(radius, segments=(True, True, True, True)):
    """Get the area and outline of a circle as pixels.
    Optionally pass in which segment is needed, as a tuple or number.
    
    Modified the bresenham complete circle algorithm from
    daniweb.com/programming/software-development/threads/321181
    """

    if isinstance(segments, int):
        segments = [i == segments for i in range(4)]
        
    #Parse text input
    elif isinstance(segments, str):
        option = segments.lower()
        count = [0, 0, 0, 0]
        if 'top' in option:
            count[0] += 1
            count[3] += 1
        if 'bottom' in option:
            count[1] += 1
            count[2] += 1
        if 'left' in option:
            count[2] += 1
            count[3] += 1
        if 'right' in option:
            count[0] += 1
            count[1] += 1
        count_max = max(count)
        segments = [i == count_max for i in count]
    
    #Calculate the circle
    switch = 3 - (2 * radius)
    outline = set()
    area = set()
    x = 0
    y = radius
    last_y = None
    last_x = None
    while x <= y:
        
        #Calculate outline
        if segments[0]:
            outline.add((x, -y))
            outline.add((y, -x))
        if segments[1]:
            outline.add((y, x))
            outline.add((x, y))
        if segments[2]:
            outline.add((-x, y))
            outline.add((-y, x))
        if segments[3]:
            outline.add((-y, -x))
            outline.add((-x, -y))
        
        #Add to area
        if y != last_y:
            last_y = y
            if segments[0]:
                for i in range(0, x):
                    area.add((i, -y))
            if segments[1]:
                for i in range(0, x):
                    area.add((i, y))
            if segments[2]:
                for i in range(1-x, 1):
                    area.add((i, y))
            if segments[3]:
                for i in range(1-x, 1):
                    area.add((i, -y))
                    
        if x != last_x:
            last_x = x
            if segments[0]:
                for i in range(0, y):
                    area.add((i, -x))
            if segments[1]:
                for i in range(0, y):
                    area.add((i, x))
            if segments[2]:
                for i in range(1-y, 1):
                    area.add((i, x))
            if segments[3]:
                for i in range(1-y, 1):
                    area.add((i, -x))

        if switch < 0:
            switch += 4 * x + 6
        else:
            switch += 4 * (x - y) + 10
            y = y - 1
        x = x + 1
        
    return {'Outline': outline, 'Area': area}
    
        
def round_up(n):
    """Quick way to round up numbers without importing the math library."""
    i = int(n)
    return i if i == n else i + 1


def round_int(n, min_value=None, max_value=None):
    """Round a number to an integer.
    It saves having to use a ton of brackets in certain situations.
    """
    if not isinstance(n, int):
        try:
            n = int(round(float(n)))
        except TypeError:
            raise TypeError('value is not a valid number: {}'.format(n))
    if min_value is not None:
        n = max(n, min_value)
    if max_value is not None:
        n = min(n, max_value)
    return n