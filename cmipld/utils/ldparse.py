from collections import OrderedDict
rmld = ['id', 'type', '@context']


def get_entry(data, entry='validation_key'):
    if isinstance(data, dict):
        if 'id' in data:
            return [data[entry]]
        else:
            data = list(data.values())
    return [i.get(entry) for i in data if entry in i]


def name_entry(data, value='description', key='validation_key'):
    if isinstance(data, list):
        return sortd({entry[key]: entry[value] for entry in data if key in entry})

    elif isinstance(data, dict):
        if 'id' in data:
            return sortd({data[key]: data[value]})
        else:
            return sortd({entry: data[entry][value] for entry in data})


def key_extract(data, keep_list):
    return sortd({k: data[k] for k in keep_list if k in data})

def multikey_extract(data, keep_list):
    return [dict(key_extract(d, keep_list)) for d in data]


def name_multikey_extract(data, keep_list,name_key='validation_key'):
    return {d[name_key]: dict(key_extract(d, keep_list)) for d in data 
            # if name_key in d
            }

def keypathstrip(data):
    return sortd({k.split('/')[-1]: v for k, v in data.items()})


def rmkeys(data, keys=rmld):
    for ky in keys:
        if ky in data:
            del data[ky]
        return data


def name_extract(data, fields=None, key='validation_key'):

    assert isinstance(data, list) or isinstance(
        data, dict), 'data must be a list or dict'
    if fields is None:
        fields = [i for i in data[0].keys() if i not in rmld]
    if isinstance(data, dict):
        if 'id' in data:
            return {data[key]: data}
        else:
            data = list(data.values())
    return sortd({entry[key]: {k: entry[k] for k in fields if k in entry} for entry in data if key in entry})


def sortd(d):
    return OrderedDict(sorted(d.items()))


def cvjson_validation_key (e):
    if not isinstance(e,list):
        e = [e]
    return [
            k.get('validation_key', e.get('@id') if isinstance(e, dict) else None)  # if k is a dict
            if isinstance(k, dict) 
            else str(k)  # if k is not a dict
            for k in e
            ]