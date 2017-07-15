import sys


PYTHON_VERSION = sys.version_info.major


def get_items(d):
    """As Python 2 and 3 have different ways of getting items,
    any attempt should be wrapped in this function.
    """
    if PYTHON_VERSION < 3:
        return d.iteritems()
    else:
        return d.items()


if PYTHON_VERSION < 3:
    input = raw_input
    range = xrange
else:
    input = input
    range = range
