from collections import OrderedDict
rmld = ['@id', '@type', '@context']


def graph_entry(url, entry='validation_key', depth=2, pretty=False):
    """
    Fetch a _graph.json and extract entry values from its contents.
    
    Args:
        url: The graph URL (e.g., 'constants:grid_type/_graph.json')
        entry: The field to extract (default: 'validation_key')
        depth: Fetch depth (default: 2)
        pretty: If True, make values presentable (replace _/- with space, title case)
    
    Returns:
        List of entry values from the graph contents
    """
    import cmipld
    data = cmipld.get(url, depth=depth)
    result = get_entry(data.get('contents', []), entry)
    if pretty:
        result = [v.replace('_', ' ').replace('-', ' ').title() if v else v for v in result]
    return result


def get_entry(data, entry='validation_key'):
    """Extract entry values from nested or flat structures"""
    if isinstance(data, dict):
        if '@id' in data:
            return [data.get(entry)]
        else:
            result = []
            for value in data.values():
                if isinstance(value, dict) and entry in value:
                    result.append(value[entry])
            return result
    elif isinstance(data, list):
        return [i.get(entry) for i in data if isinstance(i, dict) and entry in i]
    return []


def name_entry(data, value='ui-label', key='validation_key'):
    """Create a dict mapping key to value from nested or flat structures"""
    if isinstance(data, list):
        return sortd({entry[key]: entry[value] for entry in data if isinstance(entry, dict) and key in entry and value in entry})
    elif isinstance(data, dict):
        if '@id' in data:
            return sortd({data[key]: data[value]})
        else:
            return sortd({entry_data[key]: entry_data[value] 
                         for entry_key, entry_data in data.items() 
                         if isinstance(entry_data, dict) and value in entry_data and key in entry_data})
    return {}


def key_extract(data, keep_list):
    """Extract only specified keys from a dict"""
    return sortd({k: data[k] for k in keep_list if k in data})


def multikey_extract(data, keep_list):
    """Extract specified keys from each item in a list"""
    if isinstance(data, list):
        return [dict(key_extract(d, keep_list)) for d in data if isinstance(d, dict)]
    elif isinstance(data, dict):
        if '@id' in data:
            return [dict(key_extract(data, keep_list))]
        else:
            return [dict(key_extract(v, keep_list)) for v in data.values() if isinstance(v, dict)]
    return []


def name_multikey_extract(data, keep_list, name_key='validation_key'):
    """Extract specified keys from each item and use name_key as dict keys"""
    if isinstance(data, list):
        return {d[name_key]: dict(key_extract(d, keep_list)) 
                for d in data if isinstance(d, dict) and name_key in d}
    elif isinstance(data, dict):
        if '@id' in data:
            return {data[name_key]: dict(key_extract(data, keep_list))}
        else:
            result = {}
            for entry_key, entry_data in data.items():
                if isinstance(entry_data, dict):
                    key_to_use = entry_data.get(name_key, entry_key)
                    result[key_to_use] = dict(key_extract(entry_data, keep_list))
            return result
    return {}


def keypathstrip(data):
    """Strip path from keys, keeping only the last part after '/'"""
    return sortd({k.split('/')[-1]: v for k, v in data.items()})


def rmkeys(data, keys=rmld):
    """Remove specified keys from a dict"""
    result = data.copy() if isinstance(data, dict) else data
    for ky in keys:
        if ky in result:
            del result[ky]
    return result


def name_extract(data, fields=None, key='validation_key'):
    """Extract specified fields from entries, keyed by validation_key"""
    if isinstance(data, dict):
        if '@id' in data:
            if fields is None:
                fields = [i for i in data.keys() if i not in rmld]
            return {data[key]: {k: data[k] for k in fields if k in data}}
        else:
            result = {}
            for entry_key, entry_data in data.items():
                if isinstance(entry_data, dict):
                    if fields is None:
                        fields = [i for i in entry_data.keys() if i not in rmld]
                    if key in entry_data:
                        result[entry_data[key]] = {k: entry_data[k] for k in fields if k in entry_data}
            return sortd(result)
    elif isinstance(data, list):
        if fields is None and len(data) > 0:
            fields = [i for i in data[0].keys() if i not in rmld]
        return sortd({entry[key]: {k: entry[k] for k in fields if k in entry} 
                     for entry in data if isinstance(entry, dict) and key in entry})
    return {}


def sortd(d):
    """Sort a dictionary by keys"""
    return OrderedDict(sorted(d.items()))


def cvjson_validation_key(e):
    """Extract validation_key from various data structures"""
    if not isinstance(e, list):
        e = [e]
    
    result = []
    for k in e:
        if isinstance(k, dict):
            val_key = k.get('validation_key')
            if val_key is None:
                val_key = k.get('@id')
            result.append(val_key)
        else:
            result.append(str(k) if k is not None else None)
    
    return result
