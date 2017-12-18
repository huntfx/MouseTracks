"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

from core.applications import AppList
from core.compatibility import input
from core.config import CONFIG
from core.constants import APP_LIST_FILE


if __name__ == '__main__':

    if not CONFIG['Internet']['Enable']:
        choice = input('Internet access is disabled. Would you like to update from the online {}? (y/n) '.format(APP_LIST_FILE))
        if choice.lower().startswith('y'):
            CONFIG['Internet']['Enable'] = True
    CONFIG['SavedSettings']['AppListUpdate'] = 0

    AppList().save()
    input('Finished, press enter to quit.')