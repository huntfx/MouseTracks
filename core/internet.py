"""
This is part of the Mouse Tracks Python application.
Source: https://github.com/Peter92/MouseTracks
"""

from __future__ import absolute_import

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

    
def get_url_contents(url):
    """Get data from a URL."""
    try:
        return str(urllib2.urlopen(url).read())
    except (urllib2.URLError, urllib2.HTTPError):
        return None