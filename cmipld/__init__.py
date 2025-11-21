# -*- coding: utf-8 -*-
from .locations import *
from jsonld_recursive import LdrClient
import os
import time


_redirect_mapping = {}
for k,v in mapping.items():
    _redirect_mapping[f'{k}:*'] = v+'${rest}'

print("Initializing LDR client...", flush=True)

client = LdrClient(
                auto_start_server=True,
                timeout=10, max_retries=5,
                mappings=_redirect_mapping
                )

print("LDR client initialized.", flush=True)

if not client._is_server_running():
    raise RuntimeError("There was a problem starting the JSON-LD Recursive server.")

def get(url, depth=3):
    return client.compact(url, depth=depth)

def expand(url, depth=1):   
    return client.expand(url, depth=depth)

def local_mapping_using_prefix(prefix,path):
    # get all mappings
    mappings = client.get_mappings()
    # use the existing mapping for the prefix to create a new mapping
    url = mappings[f'{prefix}:*'].replace('${rest}', '')
    mappings[f'{url}*'] = path + '${rest}'
    # update mappings
    client.set_mappings(mappings)
    print(f"Added mapping: {url} -> {path}")
    
    
def map_current(prefix):
    cwd = os.getcwd()
    local_mapping_using_prefix(prefix, cwd+'/')

# # from pyld import jsonld

# # from .utils.server_tools.offline import LD_server

# # remap the requests links using prefixe mapping
# from .utils.server_tools.monkeypatch_requests import RequestRedirector
# redir = RequestRedirector({}, mapping)


# from .utils.server_tools.loader import Loader
# # Don't import everything from utils to avoid circular dependencies
# # Import specific items as needed
# from .utils.io import *
# from .utils.write06 import *
# from .utils.jsontools import *
# from .utils import git 
# from .utils.extract import *


# loader = Loader(tries=3)



# def reload(module=None):
#     # nowork
#     import sys
#     if not module:
#         module = sys.modules[__name__]

#     import importlib
#     del sys.modules[module.__name__]
#     importlib.invalidate_caches()
#     module = importlib.import_module(module.__name__)
#     importlib.reload(module)
#     print('Reloaded', module)

