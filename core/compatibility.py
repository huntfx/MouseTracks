"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import, print_function

import sys
        

class PythonVersion(object):
    """Get easy information about the current python version.
    Supports inputs as integers, floats or strings.
    
    Examples if the version is 2.7.0:
    >>> PythonVersion() == 2:
    True
    >>> PythonVersion() == 3:
    False
    >>> PythonVersion() >= 2.7:
    True
    >>> PythonVersion() < "2.7.0":
    False
    >>> PythonVersion() <= "2.7.0":
    True
    """
    
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
        """Match the input with the version in preparation for comparing."""
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


PYTHON_VERSION = PythonVersion()

if PYTHON_VERSION < 3:
    import cPickle as pickle
    from cStringIO import StringIO
    BytesIO = StringIO
    input = raw_input
    range = xrange
    unicode = unicode
else:
    import pickle
    from io import StringIO, BytesIO
    input = input
    range = range
    unicode = str


def get_items(d):
    """Iterate through the keys and values of a dictionary.
    As Python 2 and 3 have different ways of getting items,
    any attempt should be wrapped in this function.
    """
    if PYTHON_VERSION < 3:
        return d.iteritems()
    else:
        return d.items()

        
class Message(object):
    def __init__(self, queue=None):
        self.queue = queue
    
    def send(self, text, join=', '):
        """Send everything here to print, so that tweaks can be made if needed."""
        try:
            if isinstance(text, (tuple, list)):
                text = unicode(join).join(str(i).decode('utf-8','ignore').encode("utf-8") for i in text)
            else:
                text = text.replace('\\n', '\n')
            for line in text.split('\n'):
                try:
                    print(line)
                except (UnicodeEncodeError, UnicodeDecodeError):
                    line = line.encode('utf-8').strip()
                    print(line)
                if self.queue is not None:
                    self.queue.put(line)
        except AttributeError:
            print(text)
            if self.queue is not None:
                self.queue.put(text)

            
def _print(text, join=', '):
    """Send everything here to print, so that tweaks can be made if needed.
    TODO: Replaced with Message, this needs removing from all the code.
    """
    try:
        if isinstance(text, (tuple, list)):
            text = unicode(join).join(str(i).decode('utf-8','ignore').encode("utf-8") for i in text)
        else:
            text = text.replace('\\n', '\n')
        for line in text.split('\n'):
            try:
                print(line)
            except (UnicodeEncodeError, UnicodeDecodeError):
                print(line.encode('utf-8').strip())
    except AttributeError:
        print(text)