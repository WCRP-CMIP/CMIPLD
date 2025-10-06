#!/usr/bin/env python3
"""
JSON-LD Link Analysis using Graph Files

Analyzes graph.jsonld files in each folder to extract:
1. File-level links: (file_id, rel, location, links_to_other_files) - nested by folder
2. Directory-level links: (directory, links_to_other_directories) - with prefixes  
3. Broken links: (from, to) - links that don't resolve

Uses graph.jsonld files instead of individual JSON files for faster processing.

Outputs generated to 'generated/' folder.
"""

import cmipld
import os
import glob
import json
import argparse
import sys
import time
from pathlib import Path
from typing import Dict, Set, List, Any, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from cmipld.utils.git.repo_info import cmip_info
from cmipld.utils.server_tools.offline import LD_server
from cmipld.utils.checksum import version
from cmipld.utils.extract.links import depends, depends_keys_detailed


class GraphLinkAnalyzer:
    """Analyzes graph.jsonld files for link extraction."""
    
    def __init__(self, src_data_path: str, max_workers: int = None):
        self.src_data_path = Path(src_data_path)
        self.repo = None
        self.server = None
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 4)
        
        # Results storage - nested by folder structure
        self.file_links_by_folder = {}  # folder -> {files: [...], prefixes: [...]}
        self.directory_links = []       # directory relationships with prefixes
        self.broken_links = []          # (from, to) for unresolvable links
        
        # Internal tracking
        self.all_file_ids = set()
        self.file_id_to_folder = {}     # map file_id -> folder for broken link detection
        
        if not self.src_data_path.exists():
            raise FileNotFoundError(f"src-data path not found: {src_data_path}")
        if not self.src_data_path.is_dir():
            raise NotADirectoryError(f"src-data path is not a directory: {src_data_path}")

    def setup_server(self):
        """Setup server using cmipld library pattern from notebooks."""
        print("🔧 Setting up CMIP-LD repository info...")
        
        self.repo = cmip_info()
        
        directory_path = str(self.repo.path)
        location = directory_path.split('src-data')[0] + 'src-data' if 'src-data' in directory_path else os.path.join(directory_path, 'src-data')
        
        if str(self.src_data_path) != location:
            location = str(self.src_data_path)
        
        prefix = self.repo.whoami
        
        print(f"📁 Repository: {self.repo.path}")
        print(f"🏷️  Prefix: {prefix}")
        print(f"📂 Location: {location}")
        
        local = [(location, cmipld.mapping.get(prefix, f"http://localhost:8000/"), prefix)]
        
        print("🌐 Starting LD_server...")
        self.server = LD_server(copy=local, use_ssl=False)
        
        print(f"✅ Server setup complete")
        return self.server

    def find_graph_files(self) -> List[Path]:
        """Find all graph.jsonld files in src-data directory."""
        graph_files = []
        
        # Find graph.jsonld files recursively
        pattern = os.path.join(self.src_data_path, '**', 'graph.jsonld')
        for file_path in glob.glob(pattern, recursive=True):
            graph_files.append(Path(file_path))
        
        # Also look for graph.json files
        json_pattern = os.path.join(self.src_data_path, '**', 'graph.json')
        for file_path in glob.glob(json_pattern, recursive=True):
            graph_files.append(Path(file_path))
        
        return graph_files

    def get_folder_prefix(self, folder_path: Path) -> str:
        """Get the appropriate prefix for a folder based on cmipld mappings."""
        folder_name = folder_path.name.lower()
        
        folder_prefix_map = {
            'experiment': 'cmip7', 'experiments': 'cmip7',
            'activity': 'universal', 'activities': 'universal',
            'source-type': 'universal', 'source_type': 'universal',
            'model': 'cmip7', 'models': 'cmip7',
            'variable': 'vr', 'variables': 'vr',
            'cf': 'cf', 'standard-name': 'cf', 'standard_name': 'cf'
        }
        
        return folder_prefix_map.get(folder_name, self.repo.whoami if self.repo else 'universal')

    def extract_links_from_graph_parallel(self, graph_info: Tuple[Path, str]) -> Tuple[Path, str, List[Dict], Dict[str, Set[str]]]:
        """Extract links from a graph.jsonld file - designed for parallel processing."""
        graph_path, folder_prefix = graph_info
        
        try:
            with open(graph_path, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
            
            if not isinstance(graph_data, dict):
                return graph_path, folder_prefix, [], {}
            
            # Extract @graph array or treat whole document as graph
            if '@graph' in graph_data:
                items = graph_data['@graph']
            elif isinstance(graph_data, list):
                items = graph_data
            else:
                # Single item - wrap in list
                items = [graph_data]
            
            if not isinstance(items, list):
                items = [items]
            
            # Process each item in the graph
            folder_files = []
            all_folder_links = defaultdict(set)
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                    
                # Get item ID
                item_id = item.get('id', item.get('@id', ''))
                if not item_id:
                    continue
                
                # Extract links from this item
                item_links, property_links = self.extract_links_from_item(item)\n                \n                # Store file info\n                folder_files.append({\n                    'file_id': item_id,\n                    'links_to_files': list(item_links),\n                    'total_links': len(item_links),\n                    'property_links': {k: list(v) for k, v in property_links.items()}\n                })\n                \n                # Collect all links for folder-level analysis\n                for link in item_links:\n                    all_folder_links[item_id].add(link)\n            \n            return graph_path, folder_prefix, folder_files, dict(all_folder_links)\n            \n        except Exception as e:\n            print(f\"❌ Error processing graph {graph_path}: {e}\")\n            return graph_path, folder_prefix, [], {}\n\n    def extract_links_from_item(self, item: Dict[str, Any]) -> Tuple[Set[str], Dict[str, Set[str]]]:\n        \"\"\"Extract links from a single item in the graph.\"\"\"\n        links = set()\n        property_links = defaultdict(set)\n        \n        def extract_links_recursive(obj, current_property=None, visited=None):\n            if visited is None:\n                visited = set()\n            \n            if isinstance(obj, dict):\n                if id(obj) in visited:\n                    return\n                visited.add(id(obj))\n                \n                # Extract @id fields\n                if '@id' in obj:\n                    link_value = str(obj['@id'])\n                    links.add(link_value)\n                    if current_property:\n                        property_links[current_property].add(link_value)\n                \n                # Process all properties\n                for key, value in obj.items():\n                    if key == '@id':\n                        continue  # Already handled above\n                    \n                    # Check if this property contains link-like values\n                    if self._is_link_property(key, value):\n                        extracted = self._extract_property_links(value)\n                        links.update(extracted)\n                        if extracted:\n                            property_links[key].update(extracted)\n                    \n                    # Recursively process nested objects\n                    extract_links_recursive(value, key, visited)\n                    \n            elif isinstance(obj, list):\n                for item in obj:\n                    extract_links_recursive(item, current_property, visited)\n        \n        extract_links_recursive(item)\n        return links, dict(property_links)\n    \n    def _is_link_property(self, key: str, value: Any) -> bool:\n        \"\"\"Check if a property likely contains links based on name and value.\"\"\"\n        # Known link property names\n        link_properties = {\n            'activity', 'parent-experiment', 'model-realms', 'parent-activity',\n            'seeAlso', 'related', 'belongsTo', 'hasComponent', 'component',\n            'definedBy', 'references', 'license', 'contact', 'creator',\n            'experiment', 'variable', 'institution', 'model', 'source',\n            'publisher', 'contributor', 'author', 'editor', 'maintainer'\n        }\n        \n        if key in link_properties:\n            return True\n        \n        # Check if value looks like a link\n        if isinstance(value, str):\n            return self._looks_like_link(value)\n        elif isinstance(value, list) and value:\n            return any(isinstance(item, str) and self._looks_like_link(item) for item in value[:3])\n        elif isinstance(value, dict):\n            return '@id' in value\n        \n        return False\n    \n    def _looks_like_link(self, value: str) -> bool:\n        \"\"\"Check if a string value looks like a link/reference.\"\"\"\n        if not value or len(value) < 3:\n            return False\n            \n        # URL patterns\n        if value.startswith(('http://', 'https://', 'urn:', 'mailto:', 'ftp:')):\n            return True\n        \n        # Prefixed reference pattern (prefix:something)\n        if ':' in value and not value.startswith(':') and not value.endswith(':'):\n            prefix, local = value.split(':', 1)\n            if len(prefix) > 0 and len(local) > 0 and '/' in local:\n                return True\n        \n        # Path-like patterns\n        if '/' in value and len(value.split('/')) >= 2:\n            return True\n            \n        return False\n    \n    def _extract_property_links(self, value: Any) -> Set[str]:\n        \"\"\"Extract link values from a property value.\"\"\"\n        links = set()\n        \n        if isinstance(value, str):\n            if self._looks_like_link(value):\n                links.add(value)\n        elif isinstance(value, list):\n            for item in value:\n                if isinstance(item, str) and self._looks_like_link(item):\n                    links.add(item)\n                elif isinstance(item, dict) and '@id' in item:\n                    links.add(str(item['@id']))\n        elif isinstance(value, dict) and '@id' in value:\n            links.add(str(value['@id']))\n        \n        return links", "oldText": "                else:\n                    # This is a broken link - test with cmipld.get and classify properly\n                    # Combine from_path and from_prefix into single prefixed reference\n                    from_ref = f\"{folder_prefix}:{relative_path}\".replace('.json', '') if str(relative_path).endswith('.json') else f\"{folder_prefix}:{relative_path}\"\n                    \n                    self.broken_links.append({\n                        'from': from_ref,\n                        'to': link,\n                        'broken_link_type': self._classify_broken_link(link, folder_prefix)\n                    })"}]