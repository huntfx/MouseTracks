"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from core.compatibility import iteritems, range
from core.os import create_folder


def _get_priority_order(values, key='__priority__', default=None):
    """Use the __priority__ key to build a sorted list of config values.

    The list starts from the lowest value, and by default,
    the first gap will be filled with anything without a value.
    Changing default will instead assign all those values
    to a particular priority
    """
    #Build dict of values grouped by priority
    priorities = {}
    for k, v in iteritems(values):
        if not k.startswith('_'):
            priority = v.get(key, default)
            try:
                priorities[priority].append(k)
            except KeyError:
                priorities[priority] = [k]
                
    #Build list of sorted values
    try:
        current = min(i for i in priorities if i is not None)
    except ValueError:
        current = 0
    order = []
    while priorities:
        try:
            order += sorted(priorities.pop(current))
        except KeyError:
            try:
                order += sorted(priorities.pop(None))
            except KeyError:
                pass
        current += 1
    return order


class _ConfigItem(object):
    """Base class for values in the config file.
    All types inhert off this, which means they can be locked if needed.
    """
    @property
    def default(self):
        """Get the default value set by the config."""
        return self._data['default']
    
    @property
    def lock(self):
        """Lock the variable from being modified."""
        return self._data.get('lock', False)
    
    @lock.setter
    def lock(self, value):
        """Change the lock state."""
        self._data['lock'] = value
    
    @property
    def value(self):
        """Return the actual value."""
        return self._data['value']

    @property
    def level(self):
        """Return the value level.
        Can be used for things like a text system with priority.
        """
        return self._data.get('level', -1)


class _ConfigItemNumber(_ConfigItem):
    """Base class for floats and integerss.
    Inherits from _ConfigItem.
    """
    def validate(self, value):
        """Return a validated number or None."""
        try:
            value = self._data['type'](value)
        except ValueError:
            return None
        min_value = self._data.get('min', None)
        if min_value is not None:
            value = max(value, min_value)
        max_value = self._data.get('max', None)
        if max_value is not None:
            value = min(value, max_value)
        return value
            
    @property
    def min(self):
        return self._data.get('min', None)
        
    @property
    def max(self):
        return self._data.get('max', None)

        
class _ConfigItemStr(str, _ConfigItem):
    """Add controls to strings."""
    def __new__(cls, config_dict):
        obj = str.__new__(cls, config_dict['value'])
        obj._data = config_dict
        return obj
    
    def validate(self, value):
        """Return a validated string or None."""
        value = str(value)#.strip()
        if not value:
            if self._data.get('allow_empty', False):
                return value
            else:
                return None
        case_sensitive = self._data.get('case_sensitive', False)
        valid_list = self._data.get('valid', None)
        if valid_list is not None:
            if not case_sensitive:
                valid_list = [i.lower() for i in valid_list]
                value = value.lower()
            if value not in valid_list:
                return None
        return value

    def format_custom(self, **kwargs):
        """Custom format to work with square brackets.
        Converts underscores to hyphens in the variable names.
        Does not throw errors so is safe to use with user input.

        eg. "Sentence with [CUSTOM-VAR]" can be formatted with ".format_custom(CUSTOM_VAR=var)"
        """
        value = self._data['value']
        for search, replacement in iteritems(kwargs):
            value = value.replace('[{}]'.format(search.replace('_', '-')), str(replacement))
        return value
    
    @property
    def valid(self):
        """Return tuple of all valid options, or None if not set."""
        return self._data.get('valid', None)
    
    @property
    def type(self):
        return str

    @property
    def allow_empty(self):
        return self._data.get('allow_empty', False)

        
class _ConfigItemInt(int, _ConfigItemNumber):
    """Add controls to integers."""
    def __new__(cls, config_dict):
        obj = int.__new__(cls, config_dict['value'])
        obj._data = config_dict
        return obj
        
    @property
    def type(self):
        return int
    
        
class _ConfigItemFloat(float, _ConfigItemNumber):
    """Add controls to floats."""
    def __new__(cls, config_dict):
        obj = float.__new__(cls, config_dict['value'])
        obj._data = config_dict
        return obj
    
    @property
    def type(self):
        return float

        
class _ConfigItemBool(int, _ConfigItem):
    """Add controls to booleans.
    
    Due to a limitation with Python not allowing bool inheritance,
    the values are actually stored as integers.
    """
    def __new__(cls, config_dict):
        obj = int.__new__(cls, config_dict['value'])
        obj._data = config_dict
        obj._data['default'] = int(config_dict['default'])
        return obj
    
    def validate(self, value):
        if isinstance(value, str):
            if value.lower() in ('0', 'f', 'false', 'no', 'null', 'n'):
                return False
            else:
                return True
        return bool(value)
    
    @property
    def type(self):
        return bool


def create_config_item(config_dict, item_type=None):
    """Convert a normal variable into a config item."""
    config_items = {str: _ConfigItemStr, int: _ConfigItemInt, float: _ConfigItemFloat, bool: _ConfigItemBool}
    return config_items[item_type or config_dict['type']](config_dict)   

    
class _ConfigDict(dict):
    """Handle the variables inside the config.
    
    #TODO: Catch KeyErrors on invalid keys
    """
    def __init__(self, config_dict, show_hidden=False):
        self._data = config_dict
        super(_ConfigDict, self).__init__(self._data)
        self.hidden = not show_hidden

    def __repr__(self):
        return dict(self.__iter__()).__repr__()
        
    def __iter__(self):
        for k, v in iteritems(self):
            if self.hidden and k.startswith('_'):
                continue
            yield k, v['value']

    def __getitem__(self, item):
        """Return a config item instance."""
        return create_config_item(self._data[item])

    def __setitem__(self, item, value):
        """Set a new value and make sure it follows any set limits."""
        info = self._data[item]

        if info.get('lock', False):
            return
        
        validated = create_config_item(self._data[item]).validate(value)
        if validated is not None:
            self._data[item]['value'] = validated


class Config(dict):
    """Store all the variables used within the config file.
    
    Inheritance:
        Config
            _ConfigDict
                _ConfigItem
                    _ConfigItemStr
                    _ConfigItemNumber
                        _ConfigItemInt
                        _ConfigItemFloat
                    _ConfigItemBool
    
        Example:
            >>> c = Config
            >>> type(c)
            <class '__main__.Config'>
            >>> type(c['Main'])
            <class '__main__._ConfigDict'>
            >>> type(c['Main']['Language'])
            <class '__main__._ConfigItemStr'>
    """

    _DEFAULT_VALUES = {int: 0, float: 0.0, str: '', bool: False}
    
    def __init__(self, defaults, show_hidden=False, default_settings=None):
        """Initialise config with the default values.
        Can also provide default settings to apply to everything, such as {'type': int, 'min': 0}.
        """
        self._data = {}
        self._backup = {}
        self._default = defaults
        self._default_settings = default_settings
        self._load_from_dict(defaults)
        self.hidden = not show_hidden
        self.is_new = False
        super(Config, self).__init__(self._data)

    def __repr__(self):
        """Convert to dict and use __repr__ from that."""
        return dict(self.__iter__()).__repr__()

    def __iter__(self):
        """Show only values when converting to dict."""
        for k, v in iteritems(self):
            yield k, _ConfigDict(v)
                
    def __getitem__(self, item):
        """Return all values under a heading."""
        return _ConfigDict(self._data[item], show_hidden=not self.hidden)

    def _load_from_dict(self, config_dict):
        """Read data from the default dictionary."""
        for heading, var_data in iteritems(config_dict):
            self._data[heading] = {}
            self._backup[heading] = {}
            
            for var, info in iteritems(var_data):
                if isinstance(info, (str, int, float, bool)):
                    info = {'value': info}
                elif not isinstance(info, dict):
                    continue
                else:
                    info = dict(info)
                
                #Fill from default settings
                if self._default_settings is not None:
                    for option_name, option_value in iteritems(self._default_settings):
                        if option_name not in info:
                            info[option_name] = option_value
                            
                #Fill in type or value if not set
                if 'type' not in info:
                    info['type'] = type(info['value'])
                elif 'value' not in info:
                    info['value'] = self._DEFAULT_VALUES[info['type']]
                info['default'] = info['value']

                self._data[heading][var] = info
                self._backup[heading][var] = info['value']

    def _update_from_file(self, file_name):
        """Replace all the default values with one from a file."""
            
        with open(file_name, 'r') as f:
            config_lines = [i.strip() for i in f.readlines()]
        for line in config_lines:
            line = line.split('//')[0].strip()
            if not line:
                continue

            if line[0] == '[' and line[-1] == ']':
                header = line[1:-1]
            else:
                variable, value = (i.strip() for i in line.split('='))

                #Make sure it's a valid config item
                try:
                    self[header][variable] = value
                except KeyError:
                    pass
                
    def _build_for_file(self):
        """Generate lines for a config file."""
        output = []
        for heading in _get_priority_order(self._default):
            #Add heading
            output.append('[{}]'.format(heading))

            #Add heading help if set
            try:
                header_info = self._default[heading]['__info__']
            except KeyError:
                pass
            else:
                for line in header_info.split('\n'):
                    output.append('// {}'.format(line))

            #Add each variable
            for variable in _get_priority_order(self._default[heading]):
                value_type = self._default[heading][variable]['type']
                value = self._default[heading][variable].get('value', self._DEFAULT_VALUES[value_type])
                output.append('{} = {}'.format(variable, value))
                try:
                    output[-1] += '\t\t// {}'.format(self._default[heading][variable]['__info__'])
                except KeyError:
                    pass
            output.append('')
        return '\n'.join(output[:-1])

    def load(self, config_file, default_file=None):
        """Load first from the default file, then from the main file."""
        if default_file is not None:
            try:
                self._update_from_file(default_file)
            except IOError:
                pass
        try:
            self._update_from_file(config_file)
        except IOError:
            self.is_new = True
        return self

    def save(self, file_name):
        """Save the config to a file."""
        output = self._build_for_file()
        create_folder(file_name)
        with open(file_name, 'w') as f:
            f.write(output)
        return self

    def reload(self):
        """Reload and forget any changes.
        The dict is modified, so self._backup is needed to get the original string.
        """
        for header in self._backup:
            for variable in self._backup[header]:
                self[header][variable] = self._backup[header][variable]


def config_to_dict(conf):
    """Convert the config class to a dictionary."""
    new_dict = {}
    for header, variables in iteritems(conf):
        new_dict[header] = {}
        for variable, info in iteritems(variables):
            new_dict[header][variable] = info['type'](info['value'])
    return new_dict