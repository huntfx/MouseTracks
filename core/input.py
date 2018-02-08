"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from core.compatibility import input, range


def value_select(selection, default, start=0):
    """Convert a list of numbers into a range of True/False.
    If no input is given, default will be returned,
    otherwise all values not given will be False.
    """
    result = []
    if selection:
        for i in range(len(default)):
            result.append(i + start in selection)
        return result
    return list(default)
    
    
def yes_or_no(message, default=False):
    """Request a y/n input from a question.
    Will check for variants such as "true", "yep", "nope", "i think not", etc.
    """
    result = input('{} (y/n) '.format(message)).lower()
    if not result:
        return default
    elif result[0] in ('y', 't', '1'):
        return True
    elif result[0] in ('n', 'f', '0'):
        return False
    elif 'n' in result:
        return False
    elif 'y' in result:
        return True
    return default