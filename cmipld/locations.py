# from .utils import DotAccessibleDict
import re

# Registered locations
mapping = {
    # 'wcrp':'https://wcrp-cmip.github.io/',
    'universal': 'https://wcrp-cmip.github.io/WCRP-universe/',
    'vr': 'https://wcrp-cmip.github.io/Variable-Registry/',
    'cmip6plus': 'https://wcrp-cmip.github.io/CMIP6Plus_CVs/',
    'cmip7': 'https://wcrp-cmip.github.io/CMIP7-CVs/',
    'cf': 'https://wcrp-cmip.github.io/CF/',
    'obs4mips': 'https://wolfiex.github.io/obs4MIPs-cmor-tables-ld/'
}

# sort
mapping = dict(sorted(mapping.items(), key=lambda item: len(item[0])))


# # a dot accessible dict of the mapping
# latest = DotAccessibleDict(dict([i, j + 'graph'] for i, j in mapping.items()))


def reverse_mapping():
    return {v: k for k, v in mapping.items()}


def fetch_all(subset=None):
    from pyld import jsonld
    from tqdm import tqdm

    if subset:
        subset = {k: mapping[k] for k in subset}
    else:
        subset = latest

    expanded = []

    for url in tqdm(subset.values()):
        try:
            expanded.extend(jsonld.expand(url+'graph.jsonld'))
        except Exception as e:
            print('error expanding', url, e)

    return expanded


# regex matching if these exist
matches = re.compile(f"({'|'.join([i+':' for i in mapping.keys()])})")


def resolve_url(url):
    if url.startswith('http') and url.count(':') > 2:
        return mapping.get(url, url)
    else:
        return url


def compact_url(url):
    if url.startswith('http') and url.count(':') > 2:
        for k, v in mapping.items():
            if url.startswith(v):
                return url.replace(v, k+':')
        return url
    else:
        return url

def prefix_url(url):
    url = url.replace('http:','https:')
    if url.startswith('http') :
        for k, v in mapping.items():
            if url.startswith(v):
                return url.replace(v, k+':')
        return url
    else:
        return url
    
    
def resolve_prefix(query):
    if isinstance(query, str) and not query.startswith('http'):
        m = matches.search(query+':')
        if m:
            match = m.group()
            if len(match)-1 == len(query):
                query = f"{mapping[match]}graph.jsonld"
            else:
                query = query.replace(match, mapping[match[:-1]])
            print('Substituting prefix:')
            print(match, query)
    return query