from __future__ import absolute_import

try:
    import urllib2
except ImportError:
    import urllib.request as urllib2

    
def get_url_contents(url):
    """Get data from a URL."""
    try:
        return urllib2.urlopen(url)
    except (urllib2.URLError, urllib2.HTTPError):
        return None
