from collections import OrderedDict
rmld = ['@id', '@type', '@context']


def get_entry(data, entry='validation_key'):
    """Extract entry values from nested or flat structures"""
    if isinstance(data, dict):
        if '@id' in data:
            # Single entry case
            return [data.get(entry)]
        else:
            # Nested dict case - extract from nested values
            result = []
            for value in data.values():
                if isinstance(value, dict) and entry in value:
                    result.append(value[entry])
            return result
    elif isinstance(data, list):
        # List case
        return [i.get(entry) for i in data if isinstance(i, dict) and entry in i]
    return []


def name_entry(data, value='description', key='validation_key'):
    """Create a dict mapping key to value from nested or flat structures"""
    if isinstance(data, list):
        return sortd({entry[key]: entry[value] for entry in data if isinstance(entry, dict) and key in entry})
    elif isinstance(data, dict):
        if '@id' in data:
            # Single entry
            return sortd({data[key]: data[value]})
        else:
            # Nested dict - iterate over nested entries
            return sortd({entry_key: entry_data[value] 
                         for entry_key, entry_data in data.items() 
                         if isinstance(entry_data, dict) and value in entry_data})
    return {}


def key_extract(data, keep_list):
    """Extract only specified keys from a dict"""
    return sortd({k: data[k] for k in keep_list if k in data})


def multikey_extract(data, keep_list):
    """Extract specified keys from each item in a list"""
    if isinstance(data, list):
        return [dict(key_extract(d, keep_list)) for d in data if isinstance(d, dict)]
    elif isinstance(data, dict):
        # Handle nested dict case
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
            # Single entry
            return {data[name_key]: dict(key_extract(data, keep_list))}
        else:
            # Nested dict case - use dict keys or validation_key
            result = {}
            for entry_key, entry_data in data.items():
                if isinstance(entry_data, dict):
                    # Use validation_key if present, otherwise use the dict key
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
            # Single entry case
            if fields is None:
                fields = [i for i in data.keys() if i not in rmld]
            return {data[key]: {k: data[k] for k in fields if k in data}}
        else:
            # Nested dict case
            result = {}
            for entry_key, entry_data in data.items():
                if isinstance(entry_data, dict):
                    if fields is None:
                        fields = [i for i in entry_data.keys() if i not in rmld]
                    if key in entry_data:
                        result[entry_data[key]] = {k: entry_data[k] for k in fields if k in entry_data}
            return sortd(result)
    elif isinstance(data, list):
        # List case
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
            # Try validation_key first, then @id
            val_key = k.get('validation_key')
            if val_key is None:
                val_key = k.get('@id')
            result.append(val_key)
        else:
            # Not a dict, convert to string
            result.append(str(k) if k is not None else None)
    
    return result