"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Wrapper for the xinput library, to allow it to be used without events

from __future__ import absolute_import, division
from itertools import count
from operator import itemgetter
import ctypes

#Temporary fix for non-windows machines
try:
    from .xinput import XInputJoystick, get_bit_values, XINPUT_GAMEPAD
    
except AttributeError:

    #Disable gamepad tracking
    from ...utils.config import CONFIG
    CONFIG['Main']['_TrackGamepads'] = False
    
    class Gamepad(object):
        pass
        
else:
    class Gamepad(XInputJoystick):
        """Wrapper for the XInputJoystick class to avoid using events."""
        
        def __init__(self, *args, **kwargs):
            try:
                device_number = args[0].device_number
            except (IndexError, AttributeError):
                raise ValueError('use Gamepad.list_gamepads() to initialize the class objects')
            super(self.__class__, self).__init__(device_number, *args[1:], **kwargs)

        @classmethod
        def list_gamepads(self):
            """Return a list of gamepad objects."""
            return [self(gamepad) for gamepad in self.enumerate_devices()]

        def __enter__(self):
            """Get the current state."""
            self._state = self.get_state()
            self.connected = self._state is not None
            return self

        def __exit__(self, *args):
            """Record the last state."""
            self._last_state = self._state
        
        def get_axis(self, dead_zone=1024, printable=None):
            """Return a dictionary of any axis based inputs."""
            result = {}
            axis_fields = dict(XINPUT_GAMEPAD._fields_)
            axis_fields.pop('buttons')
            for axis, type in list(axis_fields.items()):
                old_val = getattr(self._last_state.gamepad, axis)
                new_val = getattr(self._state.gamepad, axis)
                data_size = ctypes.sizeof(type)
                old_val = int(self.translate(old_val, data_size) * 65535)
                new_val = int(self.translate(new_val, data_size) * 65535)

                #Detect when to send update
                if printable is not None:
                    movement = old_val != new_val and abs(old_val - new_val) > 1
                    is_trigger = axis.endswith('trigger')
                    in_dead_zone = abs(new_val) < dead_zone
                    if movement and (not in_dead_zone or new_val == 0):
                        printable[axis] = new_val
                result[axis] = new_val
                
            return result
            
        def get_button(self):
            """Return a dictionary of any button inputs."""
            if self._state is None:
                return None
            changed = self._state.gamepad.buttons ^ self._last_state.gamepad.buttons
            changed = get_bit_values(changed, 16)
            buttons_state = get_bit_values(self._state.gamepad.buttons, 16)
            changed.reverse()
            buttons_state.reverse()
            button_numbers = count(1)
            changed_buttons = list(filter(itemgetter(0), list(zip(changed, button_numbers, buttons_state))))
            
            result = {}
            for changed, number, pressed in changed_buttons:
                result[number] = pressed
            return result


    if __name__ == '__main__':
        import time

        #Example usage
        gamepads = Gamepad.list_gamepads()
        while True:
            for gamepad in gamepads:
                with gamepad as gamepad_input:
                    for axis, amount in gamepad_input.get_button().iteritems():
                        print('{}, {}'.format(axis, amount))
                    for button, state in gamepad_input.get_axis().iteritems():
                        print('{}, {}'.format(button, state))
            time.sleep(1/60)
