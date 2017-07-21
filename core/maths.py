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
        
        
def round_up(n):
    """Quick way to round numbers without importing the math library."""
    i = int(n)
    return i + 1 if i == n else i
    

def round_int(n):
    """Round a number to an integer.
    It saves having to use a ton of brackets in certain situations.
    """
    return int(round(n))
