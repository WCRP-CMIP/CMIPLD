
import os
import json


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
