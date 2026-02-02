# -*- coding: utf-8 -*-
"""
CMIP-LD Location Mappings

This module provides URL mappings between CMIP-LD prefixes and various URL formats:
- GitHub Pages URLs (e.g., https://wcrp.mipcvs.dev/)
- GitHub Repository URLs (e.g., https://github.com/WCRP-CMIP/WCRP-universe/)
- GitHub Raw Content URLs (e.g., https://raw.githubusercontent.com/...)

Each mapping type has forward (prefix -> URL) and reverse (URL -> prefix) lookups,
plus utility functions for resolving, compacting, and prefixifying URLs.
"""

import json
import os
import re

# =============================================================================
# CONFIGURATION LOADING
# =============================================================================

def _load_prefix_mappings():
    """Load prefix mappings from JSON file."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(current_dir, 'prefix_mappings.json')
    with open(json_path, 'r') as f:
        return json.load(f)


def _generate_mapping(url_template):
    """Generate mapping dictionary using a URL template."""
    result = {}
    for prefix, data in _prefix_data.items():
        owner = data['owner']
        repo = data['repo']
        result[prefix] = url_template.format(owner=owner, repo=repo, prefix=prefix)
    # Sort by key length for consistent prefix matching
    return dict(sorted(result.items(), key=lambda item: len(item[0])))


# Load prefix data at module import
_prefix_data = _load_prefix_mappings()

# Regex for matching any known prefix (e.g., "wcrp:", "cmip6plus:")
# Defined after mappings are created below
matches = None  # Initialized after mapping is created

# =============================================================================
# GITHUB PAGES MAPPINGS (mipcvs.dev)
# =============================================================================
# Maps prefixes to GitHub Pages URLs
# Example: 'wcrp' -> 'https://wcrp.mipcvs.dev/'

mapping = _generate_mapping('https://{prefix}.mipcvs.dev/')
reverse_mapping = {v: k for k, v in mapping.items()}

# Initialize prefix matching regex now that mapping exists
matches = re.compile(f"({'|'.join([i+':' for i in mapping.keys()])})")


def get_github_pages_url(prefix):
    """Get GitHub Pages URL for a prefix."""
    return mapping.get(prefix)


def resolve_url(url):
    """Resolve URL using GitHub Pages mappings."""
    if url.startswith('http') and url.count(':') > 2:
        return mapping.get(url, url)
    return url


def compact_url(url):
    """Compact URL using GitHub Pages mappings."""
    if url.startswith('http') and url.count(':') > 2:
        for k, v in mapping.items():
            if url.startswith(v):
                return url.replace(v, k + ':')
    return url


def prefix_url(url):
    """Prefix URL using GitHub Pages mappings (normalizes to https)."""
    url = url.replace('http:', 'https:')
    if url.startswith('http'):
        for k, v in mapping.items():
            if url.startswith(v):
                return url.replace(v, k + ':')
    return url


# =============================================================================
# GITHUB REPOSITORY MAPPINGS (github.com)
# =============================================================================
# Maps prefixes to GitHub repository URLs
# Example: 'wcrp' -> 'https://github.com/WCRP-CMIP/WCRP-universe/'

direct = _generate_mapping('https://github.com/{owner}/{repo}/')
reverse_direct = {v: k for k, v in direct.items()}


def get_github_repo_url(prefix):
    """Get GitHub repository URL for a prefix."""
    return direct.get(prefix)


def resolve_direct_url(url):
    """Resolve URL using GitHub repository mappings."""
    if url.startswith('http') and url.count(':') > 2:
        return direct.get(url, url)
    return url


def compact_direct_url(url):
    """Compact URL using GitHub repository mappings."""
    if url.startswith('http') and url.count(':') > 2:
        for k, v in direct.items():
            if url.startswith(v):
                return url.replace(v, k + ':')
    return url


def prefix_direct_url(url):
    """Prefix URL using GitHub repository mappings (normalizes to https)."""
    url = url.replace('http:', 'https:')
    if url.startswith('http'):
        for k, v in direct.items():
            if url.startswith(v):
                return url.replace(v, k + ':')
    return url

'''
# =============================================================================
# GITHUB RAW CONTENT MAPPINGS (raw.githubusercontent.com)
# =============================================================================
# Maps prefixes to GitHub raw content URLs
# Example: 'wcrp' -> 'https://raw.githubusercontent.com/WCRP-CMIP/WCRP-universe/main/'

io = _generate_mapping('https://raw.githubusercontent.com/{owner}/{repo}/main/')
reverse_io = {v: k for k, v in io.items()}


def get_github_raw_url(prefix):
    """Get GitHub raw content URL for a prefix."""
    return io.get(prefix)


def resolve_io_url(url):
    """Resolve URL using GitHub raw content mappings."""
    if url.startswith('http') and url.count(':') > 2:
        return io.get(url, url)
    return url


def compact_io_url(url):
    """Compact URL using GitHub raw content mappings."""
    if url.startswith('http') and url.count(':') > 2:
        for k, v in io.items():
            if url.startswith(v):
                return url.replace(v, k + ':')
    return url


def prefix_io_url(url):
    """Prefix URL using GitHub raw content mappings (normalizes to https)."""
    url = url.replace('http:', 'https:')
    if url.startswith('http'):
        for k, v in io.items():
            if url.startswith(v):
                return url.replace(v, k + ':')
    return url

'''

# =============================================================================
# GENERAL UTILITIES
# =============================================================================

def get_repo_info(prefix):
    """Get repository owner and repo name for a prefix."""
    return _prefix_data.get(prefix, {})


def resolve_prefix(query, mapping_type='default'):
    """
    Resolve prefix in query string to full URL.
    
    Args:
        query: The query string to resolve (e.g., "wcrp:activity")
        mapping_type: Type of mapping to use ('default', 'direct', 'io')
    
    Returns:
        Resolved URL string
    """
    # Select the appropriate mapping
    if mapping_type == 'direct':
        current_mapping = direct
    elif mapping_type == 'io':
        current_mapping = io
    else:
        current_mapping = mapping
    
    if isinstance(query, str) and not query.startswith('http'):
        m = matches.search(query + ':')
        if m:
            match = m.group()
            if len(match) - 1 == len(query):
                # Bare prefix (e.g., "wcrp") -> add graph.jsonld
                query = f"{current_mapping[match[:-1]]}graph.jsonld"
            else:
                # Prefixed path (e.g., "wcrp:activity") -> expand prefix
                query = query.replace(match, current_mapping[match[:-1]])
            print('Substituting prefix:')
            print(match, query)
    return query


def prefixify(data):
    """
    Convert all URLs in data to prefixed form.
    
    Args:
        data: dict or string containing URLs to prefixify
        
    Returns:
        Data with URLs replaced by prefixed versions
    """
    # Convert dict to JSON string for batch replacement
    if isinstance(data, dict):
        quick_compact = json.dumps(data)
    else:
        quick_compact = str(data)
    
    # Batch find and replace all known mappings
    for prefix, url in mapping.items():
        quick_compact = re.sub(re.escape(url), prefix + ':', quick_compact)
    
    # Convert back to dict if we started with one
    if isinstance(data, dict):
        return json.loads(quick_compact)
    return quick_compact
