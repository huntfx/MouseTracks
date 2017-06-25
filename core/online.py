import urllib2

def get_url_contents(url):
    try:
        return urllib2.urlopen(url)
    except urllib2.URLError:
        return None
