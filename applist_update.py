"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Manually update AppList.txt with an online version

from __future__ import absolute_import

from core.applications import AppList
from core.compatibility import input
from core.config import CONFIG
from core.constants import APP_LIST_FILE
from core.input import yes_or_no


if __name__ == '__main__':

    if not CONFIG['Internet']['Enable']:
        if yes_or_no('Internet access is disabled. Would you like to update from the online {}?'.format(APP_LIST_FILE)):
            CONFIG['Internet']['Enable'] = True
            
    applist = AppList()
    while True:
        if applist.update():
            applist.save()
            input('Finished, press enter to quit.')
            break
        else:
            if not yes_or_no('Failed to update. Would you like to retry?'):
                break