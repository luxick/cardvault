from urllib import request
from urllib.error import URLError, HTTPError
from mtgsdk import Set


def net_load_sets():
    try:
        sets = Set.all()
    except:
        return ""
    return sets
