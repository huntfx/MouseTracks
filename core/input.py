from __future__ import absolute_import


def value_select(selection, default, start=0):
    """Convert a list of numbers into a range of True/False.
    If no input is given, default will be returned,
    otherwise all values not given will be False.
    """
    result = []
    if selection:
        for i, default_value in enumerate(default):
            result.append(i + start in selection)
        return result
    return list(default)
