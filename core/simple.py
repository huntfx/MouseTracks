import sys


def get_items(d):
    """As Python 2 and 3 have different ways of getting items,
    any attempt should be wrapped in this function.
    """
    if sys.version_info.major == 2:
        return d.iteritems()
    else:
        return d.items()
        
        
def round_up(n):
    i = int(n)
    if float(n) - i:
        i += 1
    return i
