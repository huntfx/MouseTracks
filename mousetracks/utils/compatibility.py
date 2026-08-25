"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Handle inbuilt functions that differ between different python versions
#Overwrite any of the below functions in other files with ones from this file

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
        value = str(value)
        try:
            v_num = int(value)
        except ValueError:
            # Compare as tuple since otherwise 3.2 > 3.11
            a = [int(x) for x in str(self).split('.')]
            b = [int(x) for x in value.split('.')]
            return a, b
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
    import Queue as queue
    from cStringIO import StringIO
    BytesIO = StringIO
    input = raw_input
    range = xrange
    unicode = unicode
    bytes = str
    callable = callable
    ModuleNotFoundError = ImportError
else:
    import pickle
    import queue
    from io import StringIO, BytesIO
    input = input
    range = range
    unicode = str
    bytes = bytes
    ModuleNotFoundError = ModuleNotFoundError

    if PYTHON_VERSION <= 3.2:
        from collections import _callable_type
        callable = lambda var: isinstance(var, _callable_type)
    else:
        callable = callable


def iteritems(d, use_custom=True):
    """Override the iteritems to work with multiple Python versions and the ini class."""
    if use_custom:
        try:
            return d._iteritems_override()
        except AttributeError:
            pass
    if PYTHON_VERSION < 3:
        return d.iteritems()
    else:
        return d.items()

        
class MessageWithQueue(object):
    """Print all messages with an optional queue to send them to.
    Message(text) may be used instsead in the case of no queue.
    """
    def __init__(self, queue=None):
        self.queue = queue
    
    def send(self, text='', join=', '):
        """Send everything here to print, so that tweaks can be made if needed."""
        try:
            #Join text
            if isinstance(text, (tuple, list)):
                text = unicode(join).join(str(i).decode('utf-8','ignore').encode("utf-8") for i in text)
            else:
                text = text.replace('\\n', '\n')

            #Split by line
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
                try:
                    self.queue.put(text)
                except AssertionError:
                    pass
                
#Alternative non queue option
Message = MessageWithQueue().send