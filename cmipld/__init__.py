# -*- coding: utf-8 -*-
from .version import __version__, version
from .locations import *
from jsonld_recursive import LdrClient
import os
import time


_redirect_mapping = {}

# Add prefix mappings
for k,v in mapping.items():
    _redirect_mapping[f'{k}:*'] = v+'${rest}'

# Add mipcvs.dev domain mappings (redirect to github.io)
for k,v in mapping.items():
    _redirect_mapping[f'https://{k}.mipcvs.dev/*'] = v+'${rest}'

_client = None

def _get_client():
    """Lazily initialise the LDR client on first use."""
    global _client
    if _client is None:
        print("Initializing LDR client...", flush=True)
        _client = LdrClient(
            auto_start_server=True,
            timeout=10, max_retries=3,
            mappings=_redirect_mapping
        )
        try:
            _client.get_mappings()
        except Exception as e:
            print(f"Warning: Could not verify mappings: {e}", flush=True)
        if not _client._is_server_running():
            raise RuntimeError("There was a problem starting the JSON-LD Recursive server.")
        print("LDR client initialized.", flush=True)
    return _client

# Keep `client` as a property-like accessor for backwards compat
class _ClientProxy:
    def __getattr__(self, name):
        return getattr(_get_client(), name)

client = _ClientProxy()

# Import utils AFTER client is initialized to avoid circular import
from . import utils

def get(url, depth=3):
    return client.compact(url, depth=depth)

def getall(url, depth=3):
    ''' 
    Get the full contents of a URL, including all nested contents up to the specified depth.
    If the URL ends with a slash, append '_graph' to get the graph representation.
    '''
    if url[-1]=='/':
        url += '_graph'
        
    data = client.compact(url, depth=depth)
    
    if 'contents' in data:
        return data['contents']
    else:
        return data

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
    
def map_current(prefix_name, path=None):
    '''Temporarily map prefix to local path on the LDR server.

    Returns a cleanup callable that removes the local mapping and restores
    the original so subsequent callers (e.g. new_issue) use the remote URL.
    Also usable as a context manager:

        with cmipld.map_current("emd"):
            ...
    '''
    if path is None:
        path = os.getcwd() + '/'

    mappings = client.get_mappings()
    prefix_key = f'{prefix_name}:*'
    if prefix_key not in mappings:
        raise KeyError(f"map_current: prefix '{prefix_name}' not found in server mappings. "
                       f"Known prefixes: {list(mappings.keys())[:10]}")
    url = mappings[prefix_key].replace('${rest}', '')
    local_key = f'{url}*'

    # Remember what was there before (usually nothing)
    original_value = mappings.get(local_key)

    mappings[local_key] = path + '${rest}'
    client.set_mappings(mappings)
    print(f"Added mapping: {url} -> {path}")

    class _Cleanup:
        """Returned by map_current — call or use as context manager to restore."""
        def remove(self):
            m = client.get_mappings()
            if original_value is not None:
                m[local_key] = original_value
            elif local_key in m:
                del m[local_key]
            client.set_mappings(m)
            print(f"Removed local mapping: {url}")

        # context manager support
        def __enter__(self):
            return self

        def __exit__(self, *_):
            self.remove()

        # callable support: cleanup()
        def __call__(self):
            self.remove()

    return _Cleanup()
    
    
def prefix():
    """Get the prefix for the current repository."""
    return utils.git.get_prefix()


class ensure_remote:
    """
    Context manager that temporarily removes any local-path URL mappings
    from the LDR server for the duration of the block, ensuring all prefix
    resolution uses the canonical remote URLs.

    Use whenever fetching data that must come from the remote (e.g. in
    similarity/report_builder, graph_loader) to avoid stale mappings left
    behind by graphify or map_current.

    Usage::

        with cmipld.ensure_remote():
            data = cmipld.get("emd:horizontal_grid_cell/_graph.json")
    """

    def __init__(self):
        self._suspended = {}   # key -> original_value for restored mappings

    def __enter__(self):
        try:
            all_mappings = client.get_mappings()
        except Exception:
            return self
        suspended = {}
        filtered = {}
        for k, v in all_mappings.items():
            # Local mappings point to filesystem paths (start with / or file://)
            is_local = (
                isinstance(v, str) and (
                    v.startswith('/') or
                    v.startswith('file://') or
                    (len(v) > 1 and v[1] == ':')  # Windows C:\...
                )
            )
            if is_local:
                suspended[k] = v   # remember it
            else:
                filtered[k] = v
        if suspended:
            client.set_mappings(filtered)
            self._suspended = suspended
        return self

    def __exit__(self, *_):
        if self._suspended:
            try:
                current = client.get_mappings()
                current.update(self._suspended)
                client.set_mappings(current)
            except Exception:
                pass
        self._suspended = {}
