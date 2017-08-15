from __future__ import absolute_import, print_function
import sys


def get_items(d):
    """As Python 2 and 3 have different ways of getting items,
    any attempt should be wrapped in this function.
    """
    if PYTHON_VERSION < 3:
        return d.iteritems()
    else:
        return d.items()


def _print(text):
    """Send everything here to print, so that tweaks can be made if needed."""
    for line in text.replace('\\n', '\n').split('\n'):
        try:
            print(line)
        except (UnicodeEncodeError, UnicodeDecodeError):
            print(line.encode('utf-8').strip())


class PythonVersion(object):
    
    MAJOR = sys.version_info.major
    MINOR = sys.version_info.minor
    MICRO = sys.version_info.micro
    
    def __init__(self):
        pass
    
    def __float__(self):
        return float('{}.{}'.format(self.MAJOR, self.MINOR))
    
    def __int__(self):
        return int(self.MAJOR)
    
    def __str__(self):
        return '{}.{}.{}'.format(self.MAJOR, self.MINOR, self.MICRO)
    
    def _compare(self, value):
        try:
            v_num = int(value)
        except ValueError:
            try:
                v_num = float(value)
            except ValueError:
                return str(self), value
            return float(self), v_num
        return int(self), v_num
    
    def __eq__(self, value):
        v1, v2 = self._compare(value)
        return v1 == v2
    
    def __ne__(self, value):
        v1, v2 = self._compare(value)
        return v1 != v2
    
    def __gt__(self, value):
        v1, v2 = self._compare(value)
        return v1 > v2
    
    def __ge__(self, value):
        v1, v2 = self._compare(value)
        return v1 >= v2
    
    def __lt__(self, value):
        v1, v2 = self._compare(value)
        return v1 < v2
    
    def __le__(self, value):
        v1, v2 = self._compare(value)
        return v1 <= v2


PYTHON_VERSION = PythonVersion

if PYTHON_VERSION < 3:
    input = raw_input
    range = xrange
else:
    input = input
    range = range
