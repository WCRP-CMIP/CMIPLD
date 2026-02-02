# -*- coding: utf-8 -*-
from .locations import *
from . import utils
from jsonld_recursive import LdrClient
import os
import time


_redirect_mapping = {}

# Add prefix mappings (e.g., universal:* -> https://wcrp-cmip.github.io/WCRP-universe/${rest})
for k,v in mapping.items():
    _redirect_mapping[f'{k}:*'] = v+'${rest}'

# Add mipcvs.dev domain mappings (e.g., https://universal.mipcvs.dev/* -> https://wcrp-cmip.github.io/WCRP-universe/${rest})
for k,v in mapping.items():
    _redirect_mapping[f'https://{k}.mipcvs.dev/*'] = v+'${rest}'

print("Initializing LDR client...", flush=True)

# print(f"Mappings to set: {_redirect_mapping}", flush=True)

client = LdrClient(
                auto_start_server=True,
                timeout=10, max_retries=3,
                mappings=_redirect_mapping
                )

# Verify mappings were set
try:
    current_mappings = client.get_mappings()
    print(f"Current server mappings: {current_mappings}", flush=True)
except Exception as e:
    print(f"Warning: Could not verify mappings: {e}", flush=True)

print("LDR client initialized.", flush=True)

if not client._is_server_running():
    raise RuntimeError("There was a problem starting the JSON-LD Recursive server.")

def get(url, depth=3):
    return client.compact(url, depth=depth)

def expand(url, depth=1):   
    return client.expand(url, depth=depth)

def resolve(url):
    """Test how a URL gets resolved/mapped."""
    return client.resolve(url)

def test_load(url):
    """Test loading a document without processing."""
    return client.test_load(url)

def debug(url):
    """Print detailed debug info about a URL."""
    return client.debug_url(url)
    
def map_current(prefix,path=None):
    '''Local mapping for current repo using given prefix'''
    if path is None:path = os.getcwd()+'/'
    # get all mappings
    mappings = client.get_mappings()
    # use the existing mapping for the prefix to create a new mapping
    url = mappings[f'{prefix}:*'].replace('${rest}', '')
    mappings[f'{url}*'] = os.path + '${rest}'
    # update mappings
    client.set_mappings(mappings)
    print(f"Added mapping: {url} -> {path}")
    
    
def prefix():
    myurl = utils.git.get_repo_url()
    return reverse_direct.get(myurl,myurl)    
    


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

