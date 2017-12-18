from __future__ import absolute_import

from core.compatibility import Message, input

options = [
    ('get_focused_application_name', 'Get name, executable and resolution of currently focused application'),
    ('get_key_press', 'Get character codes of pressed keys'),
    ('client_connect', 'Connect a client to the main script (receives messages only)')
]

Message('Here is a list of possible options.')
Message('Once you select an option, it will continue running until you close it.')
Message('')
for i, (name, description) in enumerate(options):
    Message('{}: {}'.format(i + 1, description))

selection = input('Choose an option to run: ')

__import__('debug.{}'.format(options[int(selection) - 1][0]))
