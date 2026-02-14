#!/usr/bin/env python3
"""
Styling utilities for CMIP-LD visualization and output.

Provides functions for extracting colors from CSS, URI shortening,
and other styling-related utilities used across visualization tools.
"""

import re
import os
from pathlib import Path
from typing import Dict, Optional, Any

# Default color palette (Material Design Blue)
DEFAULT_COLORS = {
    'primary': '#2196f3',
    'primary_light': '#bbdefb',
    'primary_dark': '#1976d2',
    'secondary': '#ff9800',
    'secondary_light': '#ffe0b2',
    'secondary_dark': '#f57c00',
    'success': '#4caf50',
    'warning': '#ff9800',
    'error': '#f44336',
    'grey': '#808080',
    'grey_light': '#e0e0e0',
    'grey_dark': '#424242',
}


def get_colors_from_css(
    css_path: str = 'docs/stylesheets/custom.css',
    prefix: str = 'emd',
    defaults: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Extract color variables from a CSS file.
    
    Looks for CSS custom properties (variables) matching the pattern:
    --{prefix}-{color-name}: {value};
    
    Args:
        css_path: Path to the CSS file
        prefix: Prefix for CSS variables (e.g., 'emd' for --emd-primary)
        defaults: Default colors to use if CSS extraction fails
        
    Returns:
        Dictionary of color names to hex values
        
    Example:
        >>> colors = get_colors_from_css('docs/stylesheets/custom.css', 'emd')
        >>> print(colors['primary'])
        '#2196f3'
    """
    colors = dict(defaults or DEFAULT_COLORS)
    
    try:
        with open(css_path, 'r') as f:
            css = f.read()
        
        # Extract all color variables with the given prefix
        pattern = rf'--{prefix}-([a-z0-9-]+):\s*([^;]+);'
        for match in re.finditer(pattern, css, re.IGNORECASE):
            key = match.group(1).replace('-', '_')
            value = match.group(2).strip()
            colors[key] = value
            
    except (FileNotFoundError, IOError):
        pass
    
    return colors


def get_project_colors(base_dir: Optional[Path] = None) -> Dict[str, str]:
    """
    Get colors for the current project by detecting the project type.
    
    Tries multiple common CSS locations and prefixes.
    
    Args:
        base_dir: Base directory to search from (default: current directory)
        
    Returns:
        Dictionary of color names to hex values
    """
    if base_dir is None:
        base_dir = Path.cwd()
    
    # Common CSS locations
    css_paths = [
        'docs/stylesheets/custom.css',
        'docs/css/custom.css',
        'docs/assets/css/custom.css',
        'static/css/custom.css',
        '_static/css/custom.css',
    ]
    
    # Try to detect prefix from repository name
    try:
        import cmipld
        prefix = cmipld.prefix()
    except:
        prefix = 'emd'  # Default prefix
    
    # Try each CSS path
    for css_path in css_paths:
        full_path = base_dir / css_path
        if full_path.exists():
            return get_colors_from_css(str(full_path), prefix)
    
    return dict(DEFAULT_COLORS)


def shorten_uri(uri: Any, mappings: Optional[Dict[str, str]] = None) -> str:
    """
    Shorten a URI using prefix mappings.
    
    Args:
        uri: URI to shorten (can be string or URIRef)
        mappings: Dictionary of prefix -> namespace URL mappings
                  If None, tries to use cmipld.mapping
        
    Returns:
        Shortened URI string (e.g., 'emd:model/CESM2')
        
    Example:
        >>> shorten_uri('https://emd.mipcvs.dev/model/CESM2')
        'emd:model/CESM2'
    """
    uri_str = str(uri)
    
    # Get mappings
    if mappings is None:
        try:
            import cmipld
            mappings = cmipld.mapping
        except ImportError:
            return uri_str
    
    # Find matching prefix
    for prefix, namespace in mappings.items():
        if uri_str.startswith(namespace):
            local = uri_str[len(namespace):]
            # Clean up vocabulary paths
            if 'docs/vocabularies/' in local:
                local = local.split('/')[-1]
            return f'{prefix}:{local}'
    
    return uri_str


def get_node_color(
    node_id: str,
    prefix: str,
    colors: Dict[str, str],
    default_color: str = '#808080'
) -> str:
    """
    Determine the color for a graph node based on its ID.
    
    Args:
        node_id: Node identifier
        prefix: Project prefix (e.g., 'emd')
        colors: Color dictionary
        default_color: Color for external nodes
        
    Returns:
        Hex color string
    """
    if node_id.startswith(f'{prefix}:'):
        return colors.get('primary', default_color)
    return default_color


def get_folder_from_uri(uri: str) -> str:
    """
    Extract the folder/collection name from a URI.
    
    Args:
        uri: URI string (e.g., 'emd:model/CESM2' or full URL)
        
    Returns:
        Folder name (e.g., 'emd:model')
    """
    if '/' in uri:
        return uri.rsplit('/', 1)[0]
    return uri


# Status icons for CLI output
STATUS_ICONS = {
    'success': '✓',
    'failed': '✗',
    'warning': '⚠',
    'info': 'ℹ',
    'processing': '⋯',
}

STATUS_EMOJI = {
    'success': '✅',
    'failed': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'processing': '🔄',
}


def format_status(status: str, message: str, use_emoji: bool = False) -> str:
    """
    Format a status message with appropriate icon.
    
    Args:
        status: Status type ('success', 'failed', 'warning', 'info')
        message: Message text
        use_emoji: Use emoji instead of ASCII icons
        
    Returns:
        Formatted status string
    """
    icons = STATUS_EMOJI if use_emoji else STATUS_ICONS
    icon = icons.get(status, '?')
    return f'{icon} {message}'
