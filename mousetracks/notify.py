"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Print text with different levels of importance
#A minimum level can be set to ignore less important text

from __future__ import absolute_import

from collections import defaultdict

from .utils.compatibility import iteritems
from .config.settings import CONFIG


class Notify(object):
    """Simple to use class for text with levels of importance.
    Each item is queued up until printed, where it is then deleted.

    Examples:
        >>> notify = Notify(message_level=0)
        
        #Inline print
        >>> print(notify('some sentence'))
        'some sentence'

        #Prioritise high level
        >>> notify('sentence1')
        >>> notify('sentence2')
        >>> notify('sentence3', level_override=3)
        >>> print(notify)
        'sentence3 | sentence2 | sentence1'

        >>> notify('sentence1')
        >>> notify('sentence2', level_override=2)
        >>> notify('sentence3', level_override=3)
        >>> notify.level = 2
        >>> print(notify)
        'sentence3 | sentence2'

    Things to watch out for:
        #Append to list (need to convert the output)
        >>> lst += list(notify)
        >>> lst.append(str(notify))
    """
    def __init__(self, message_level=None):
        super(self.__class__, self).__init__()
        self._level = message_level
        self._message_queue = defaultdict(list)

    def _combine(self, delete=True):
        """Create list of messages with most important first."""
        output = []
        for level in sorted(self._message_queue.keys())[::-1]:
            output += self._message_queue[level]
        if delete:
            self._message_queue = defaultdict(list)
        return output
        
    def __iter__(self, *args):
        """Iterate through each message."""
        return self._combine().__iter__(*args)

    def _add(self, string, level_override=None, **kwargs):
        """Base function for add/append.
        Will first treat the string as _ConfigItemStr but will fallback to a normal str.
        """
        if level_override is None or not isinstance(level_override, (int, float)):
            try:
                level = string.get('level', 0)
            except AttributeError:
                level = self.level
        else:
            level = level_override
        
        #Only process string if past the required message level
        if level >= self.level:
            try:
                formatted = string.format_custom(**kwargs)
            except AttributeError:
                formatted = str(string).format(**kwargs)
            
            #Capitalise string if it contains anything
            try:
                formatted = formatted[0].upper() + formatted[1:]
            except IndexError:
                pass
            else:
                self._message_queue[level].append(formatted)
        return self

    def __add__(self, string, level_override=None, **kwargs):
        """Add text to be displayed.
        Warning: If using Notify as a global variable,
        do not use += or Python will think it's a local variable.
        """
        return self._copy()._add(string=string, level_override=level_override, **kwargs)

    def __str__(self):
        return self.output(_delete=False)

    def _copy(self):
        """Make a copy of the class."""
        obj = Notify(message_level=self._level)
        for level, values in iteritems(self._message_queue):
            obj._message_queue[level] = list(values)
        return obj
    
    def __call__(self, string, level_override=None, **kwargs):
        """Add text to be displayed. 
        Recommended way of doing it.
        """
        self._add(string=string, level_override=level_override, **kwargs)
        return self
    
    def __bool__(self):
        return bool(self._message_queue)
    
    __nonzero__ = __bool__

    @property
    def level(self):
        """Get the minimum message level."""
        if self._level is not None:
            return self._level
        return CONFIG['Advanced']['MessageLevel']
    
    @level.setter
    def level(self, value):
        """Set a new minimum message level."""
        i = int(value)
        f = float(value)
        self._level = (f, i)[i == f]

    def put(self, queue):
        """Send across a queue or pipe."""
        if queue is None:
            return False
        output = self.output()
        if output:
            queue.put(output)
            return True
        return False

    def output(self, _delete=True):
        """Get the output and wipe the class.
        Use this instead of relying on __str__,
        as doing that can cause unintended issues.
        """
        return ' | '.join(self._combine(delete=_delete))

NOTIFY = Notify()