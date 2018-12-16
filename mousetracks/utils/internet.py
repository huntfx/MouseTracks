"""This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""
#Any functions that use requests (required for the API), or require access to the internet

from __future__ import absolute_import

import json
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

from .compatibility import bytes
from ..config.language import LANGUAGE
from ..notify import NOTIFY

    
def send_request(url, timeout=None, output=False):
    """Send URL request."""
    if output:
        NOTIFY(LANGUAGE.strings['Internet']['Request'], URL=url)
    try:
        return urllib2.urlopen(url, timeout=timeout)
    except (urllib2.URLError, urllib2.HTTPError):
        return None


def get_url_contents(url, timeout=None, _json=False):
    """Get data from a URL."""
    request = send_request(url, timeout=timeout)
    if request is not None:
        return (bytes, json.loads)[_json](request.read())


def get_url_json(url, timeout=None):
    """Return JSON URL contents as a dictionary."""
    return get_url_contents(url, timeout=timeout, _json=True)