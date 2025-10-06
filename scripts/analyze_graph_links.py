#!/usr/bin/env python3
"""
JSON-LD Link Analysis using Graph Files

Analyzes graph.jsonld files in each folder to extract links and test them with cmipld.get(depth=0).
Enhanced debugging to identify why no property mappings are found.
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


class GraphLinkAnalyzer:
    """Analyzes graph.jsonld files for link extraction with detailed debugging."""
    
    def __init__(self, src_data_path: str, max_workers: int = None):
        self.src_data_path = Path(src_data_path)
        self.repo = None
        self.server = None
        self.max_workers = max_workers or min(multiprocessing.cpu_count(), 4)
        
        # Results storage
        self.file_links_by_folder = {}
        self.directory_links = []
        self.broken_links = []
        
        # Internal tracking
        self.all_file_ids = set()
        self.file_id_to_folder = {}
        
        if not self.src_data_path.exists():
            raise FileNotFoundError(f"src-data path not found: {src_data_path}")

    def setup_server(self):
        """Setup server using cmipld library pattern."""
        print("🔧 Setting up CMIP-LD repository info...")
        
        self.repo = cmip_info()
        directory_path = str(self.repo.path)
        location = directory_path.split('src-data')[0] + 'src-data' if 'src-data' in directory_path else os.path.join(directory_path, 'src-data')
        
        if str(self.src_data_path) != location:
            location = str(self.src_data_path)
        
        prefix = self.repo.whoami
        local = [(location, cmipld.mapping.get(prefix, f"http://localhost:8000/"), prefix)]
        
        print("🌐 Starting LD_server...")
        self.server = LD_server(copy=local, use_ssl=False)
        print("✅ Server setup complete")

    def find_graph_files(self) -> List[Path]:
        """Find all graph files."""
        graph_files = []
        for pattern in ['graph.jsonld', 'graph.json']:
            for file_path in glob.glob(os.path.join(self.src_data_path, '**', pattern), recursive=True):
                graph_files.append(Path(file_path))
        return graph_files

    def get_folder_prefix(self, folder_path: Path) -> str:
        """Get prefix for folder."""
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

    def extract_links_from_item_with_rdf(self, item: Dict[str, Any], item_id: str, folder_prefix: str) -> Tuple[Set[str], Dict[str, Set[str]]]:
        """Extract links from a single file using RDF analysis, avoiding cyclical context issues."""
        links = set()
        property_links = defaultdict(set)
        
        try:
            from pyld import jsonld
            
            print(f"🔍 Analyzing file: {item_id}")
            
            # Use cmipld reference directly instead of adding context to avoid cycles
            # Create proper cmipld reference for this item
            folder_relative = ''
            for graph_path in self.find_graph_files():
                if graph_path.parent.name in str(graph_path):
                    folder_relative = graph_path.parent.relative_to(self.src_data_path)
                    break
            
            cmipld_ref = f"{folder_prefix}:{folder_relative}/{item_id}" if folder_relative else f"{folder_prefix}:{item_id}"
            
            print(f"   Using cmipld reference: {cmipld_ref}")
            
            # Get the expanded document using cmipld.get to avoid context cycles
            try:
                expanded_item = cmipld.get(cmipld_ref, depth=0)
                if not expanded_item:
                    print(f"   ⚠️  Could not fetch item with cmipld.get: {cmipld_ref}")
                    return self.extract_links_direct_from_item(item)
                
                print(f"   Successfully fetched expanded item")
                print(f"   Expanded item keys: {list(expanded_item.keys()) if isinstance(expanded_item, dict) else 'N/A'}")
                
                # Now convert the properly expanded item to RDF
                rdf_dataset = jsonld.to_rdf(expanded_item)
                
            except Exception as e:
                print(f"   ⚠️  cmipld.get failed: {e}")
                print(f"   Falling back to direct item analysis...")
                return self.extract_links_direct_from_item(item)
            
            # Process RDF triples to find links
            total_triples = 0
            iri_objects = 0
            
            for graph_name, triples in rdf_dataset.items():
                print(f"   Graph '{graph_name}': {len(triples)} triples")
                
                for i, triple in enumerate(triples):
                    total_triples += 1
                    predicate_uri = triple['predicate']['value']
                    object_val = triple['object']['value']
                    object_type = triple['object']['type']
                    
                    if i < 3:  # Show first 3 triples
                        print(f"     Triple {i+1}: {predicate_uri} -> {object_val} ({object_type})")
                    
                    # Process IRI objects (links)
                    if object_type == 'IRI':
                        iri_objects += 1
                        property_name = self._uri_to_property_name(predicate_uri)
                        
                        # Test if link is fetchable
                        print(f"   Testing link: {property_name} -> {object_val}")
                        try:
                            result = cmipld.get(object_val, depth=0)
                            if result and isinstance(result, dict):
                                links.add(object_val)
                                if property_name != 'type':
                                    property_links[property_name].add(object_val)
                                print(f"     ✅ VALID")
                            else:
                                print(f"     💔 BROKEN - empty result")
                        except Exception as e:
                            print(f"     💔 BROKEN - {e}")
            
            print(f"   Total: {total_triples} triples, {iri_objects} IRI objects")
            print(f"📋 Results: {len(links)} valid links, {len(property_links)} properties")
            
            return links, dict(property_links)
            
        except Exception as e:
            print(f"❌ RDF processing failed: {e}")
            return self.extract_links_direct_from_item(item)
    
    def extract_links_direct_from_item(self, item: Dict[str, Any]) -> Tuple[Set[str], Dict[str, Set[str]]]:
        """Direct link extraction from item without RDF conversion."""
        links = set()
        property_links = defaultdict(set)
        
        print(f"   Using direct extraction (no RDF)")
        
        # Check each property for link-like values
        for key, value in item.items():
            if key in {'id', '@id'}:
                continue
                
            # Look for string values that look like references
            if isinstance(value, str):
                if self._looks_like_link(value):
                    links.add(value)
                    property_links[key].add(value)
                    print(f"     Found link in {key}: {value}")
            elif isinstance(value, list):
                for list_item in value:
                    if isinstance(list_item, str) and self._looks_like_link(list_item):
                        links.add(list_item)
                        property_links[key].add(list_item)
                        print(f"     Found link in {key}[]: {list_item}")
                    elif isinstance(list_item, dict) and '@id' in list_item:
                        link_val = str(list_item['@id'])
                        links.add(link_val)
                        property_links[key].add(link_val)
                        print(f"     Found @id in {key}[]: {link_val}")
        
        print(f"   Direct extraction found: {len(links)} links, {len(property_links)} properties")
        return links, dict(property_links)
    
    def _looks_like_link(self, value: str) -> bool:
        """Check if string looks like a link."""
        if not value or len(value) < 3:
            return False
        
        # URL patterns
        if value.startswith(('http://', 'https://', 'urn:', 'mailto:')):
            return True
        
        # Prefixed reference (prefix:path/to/something)
        if ':' in value and not value.startswith(':'):
            prefix, local = value.split(':', 1)
            if len(prefix) > 0 and len(local) > 0 and ('/' in local or local in self.all_file_ids):
                return True
        
        return False

    def _uri_to_property_name(self, predicate_uri: str) -> str:
        """Convert predicate URI to property name."""
        if predicate_uri == 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type':
            return 'type'
        
        for prefix, base_url in cmipld.mapping.items():
            if predicate_uri.startswith(base_url):
                local_part = predicate_uri[len(base_url):].strip('/')
                return local_part.split('/')[-1]
        
        if '#' in predicate_uri:
            return predicate_uri.split('#')[-1]
        elif '/' in predicate_uri:
            return predicate_uri.split('/')[-1]
        return predicate_uri

    def process_single_graph(self, graph_path: Path, folder_prefix: str) -> Tuple[str, List[Dict]]:
        """Process a single graph file."""
        try:
            with open(graph_path, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
            
            print(f"📊 Processing graph: {graph_path}")
            print(f"   Graph data type: {type(graph_data)}")
            print(f"   Graph keys: {list(graph_data.keys()) if isinstance(graph_data, dict) else 'N/A'}")
            
            # Extract items from graph
            if '@graph' in graph_data:
                items = graph_data['@graph']
                print(f"   Found @graph with {len(items)} items")
            elif isinstance(graph_data, list):
                items = graph_data
                print(f"   Graph is list with {len(items)} items")
            else:
                items = [graph_data]
                print(f"   Graph is single item")
            
            folder_files = []
            folder_relative = graph_path.parent.relative_to(self.src_data_path)
            folder_str = str(folder_relative) if str(folder_relative) != '.' else ''
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                
                item_id = item.get('id', item.get('@id', ''))
                if not item_id:
                    print(f"   ⚠️  Skipping item with no ID")
                    continue
                
                print(f"\n🔍 Processing item: {item_id}")
                
                # Extract links from this specific file using RDF
                item_links, property_links = self.extract_links_from_item_with_rdf(item, item_id, folder_prefix)
                
                folder_files.append({
                    'file_id': item_id,
                    'rel': f"{folder_str}/{item_id}.json" if folder_str else f"{item_id}.json",
                    'location': str(graph_path.parent / f"{item_id}.json"),
                    'links_to_files': list(item_links),
                    'total_links': len(item_links),
                    'property_links': property_links
                })
                
                self.all_file_ids.add(item_id)
                self.file_id_to_folder[item_id] = folder_str
            
            return folder_str, folder_files
            
        except Exception as e:
            print(f"❌ Error processing {graph_path}: {e}")
            return '', []

    def analyze_graphs(self):
        """Main analysis method."""
        print(f"🔍 Analyzing graph files in: {self.src_data_path}")
        
        graph_files = self.find_graph_files()
        print(f"📊 Found {len(graph_files)} graph files")
        
        if not graph_files:
            print("⚠️  No graph files found!")
            return
        
        # Process each graph file
        for graph_path in graph_files:
            folder_prefix = self.get_folder_prefix(graph_path.parent)
            folder_str, folder_files = self.process_single_graph(graph_path, folder_prefix)
            
            if folder_files:
                self.file_links_by_folder[folder_str] = {
                    'folder': folder_str,
                    'prefix': folder_prefix,
                    'graph_file': str(graph_path.relative_to(self.src_data_path)),
                    'files': folder_files
                }
        
        print(f"\n✅ Analysis complete:")
        print(f"   📁 {len(self.file_links_by_folder)} folders")
        print(f"   📄 {sum(len(f['files']) for f in self.file_links_by_folder.values())} files")
        print(f"   🆔 {len(self.all_file_ids)} unique file IDs")

    def save_results(self, output_dir: Path):
        """Save results."""
        output_dir.mkdir(exist_ok=True)
        
        file_links_path = output_dir / 'file_links_from_graphs.json'
        with open(file_links_path, 'w', encoding='utf-8') as f:
            json.dump(self.file_links_by_folder, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved to: {file_links_path}")

    def cleanup(self):
        """Cleanup server."""
        if self.server:
            try:
                if hasattr(self.server, 'stop'):
                    self.server.stop()
            except Exception as e:
                print(f"⚠️  Server cleanup warning: {e}")


def main():
    parser = argparse.ArgumentParser(description="Analyze graph.jsonld files for links")
    parser.add_argument('src_data', help='Path to src-data directory')
    parser.add_argument('--output', '-o', default='generated', help='Output directory')
    parser.add_argument('--no-server', action='store_true', help='Skip server setup')
    
    args = parser.parse_args()
    
    try:
        print("🚀 Starting Graph Link Analysis with Enhanced Debugging")
        print("=" * 60)
        
        analyzer = GraphLinkAnalyzer(args.src_data)
        
        if not args.no_server:
            try:
                analyzer.setup_server()
            except Exception as e:
                print(f"⚠️  Server setup failed: {e}")
        
        analyzer.analyze_graphs()
        
        output_path = Path(args.output)
        analyzer.save_results(output_path)
        
        return 0
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        try:
            if 'analyzer' in locals():
                analyzer.cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
