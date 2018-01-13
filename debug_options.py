"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from core.compatibility import Message, input

def debug_options():
    options = [
        ('get_focused_application_name', 'Get name, executable and resolution of currently focused application'),
        ('get_key_press', 'Get character codes of pressed keys'),
        ('client_connect', 'Connect a client to the main script (receives messages only)'),
        ('fix_poe_mine_issue', 'Fix an issue caused by playing a mine build in Path of Exile')
    ]

    Message('Here is a list of possible options.')
    Message('Once you select an option, you must reload this file to pick a different one.')
    Message()
    for i, (name, description) in enumerate(options):
        Message('{}: {}'.format(i + 1, description))

    selection = input('Choose an option to run: ')
    Message()

    __import__('debug.{}'.format(options[int(selection) - 1][0]))


if __name__ == '__main__':
    debug_options()