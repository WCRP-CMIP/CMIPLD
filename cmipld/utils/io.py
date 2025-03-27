
import os
import json


import json
import glob
import pprint
import os
from .git_core import toplevel

def jr(file):
    """JSON read"""
    return json.load(open(file, 'r'))

def jw(data, file):
    """JSON write"""
    return json.dump(data, open(file, 'w'), indent=4)

def getfile(fileend):
    """Get files with specific ending"""
    return glob.glob(f'*{fileend}.json')

def pp(js):
    """Pretty print"""
    pprint.pprint(js)

def ldpath(path=''):
    """Get location path"""
    loc = os.path.abspath(f"{toplevel()}/src-data/{path}/")
    if loc[-1] != '/':
        loc += '/'
    return loc


def read_jsn(f):
    return json.load(open(f, 'r'))


rjsn = read_jsn


def read_url(url):
    import urllib
    import urllib.request
    try:
        with urllib.request.urlopen(url) as response:
            data = response.read().decode('utf-8')
            json_data = json.loads(data)
            return json_data
    except urllib.error.HTTPError as e:
        err = f"Error: {e.code} - {e.reason}"
        # print(err)
        return None
    except urllib.error.URLError as e:
        err = f"Error: {e.reason}"
        # print(err)
        return None


def wjsn(data, f):
    with open(f, 'w') as file:
        json.dump(data, file, indent=4)


# git reset --hard miptables/jsonld && git clean -fd
