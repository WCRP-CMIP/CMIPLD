#!/usr/bin/env python3
"""
JSON-LD Link Analysis using CMIPLD Library

Creates a server that mounts src-data and analyzes all JSON-LD files to extract:
1. File-level links: (file_id, rel, location, links_to_other_files)
2. Directory-level links: (directory, links_to_other_directories)

Outputs generated to 'generated/' folder.

Uses cmipld library pattern from notebooks for server setup and link extraction.
"""

import cmipld
import os
import glob
import importlib.util
import json
import argparse
import sys
import time
from pathlib import Path
from typing import Dict, Set, List, Any, Tuple
from collections import defaultdict

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from cmipld.utils.git.repo_info import cmip_info
from cmipld.utils.server_tools.offline import LD_server
from cmipld.utils.checksum import version
from cmipld.utils.extract.links import depends, depends_keys_detailed


class CmipLDLinkAnalyzer:
    """Analyzes JSON-LD files using cmipld library for link extraction."""
    
    def __init__(self, src_data_path: str):
        self.src_data_path = Path(src_data_path)
        self.repo = None
        self.server = None
        self.file_links = []
        self.directory_links = []
        self.all_file_ids = set()
        
        # Validate path
        if not self.src_data_path.exists():
            raise FileNotFoundError(f"src-data path not found: {src_data_path}")
        if not self.src_data_path.is_dir():
            raise NotADirectoryError(f"src-data path is not a directory: {src_data_path}")
    
    def setup_server(self):
        """Setup server using cmipld library pattern from notebooks."""
        print("🔧 Setting up CMIP-LD repository info...")
        
        # Get repository information
        self.repo = cmip_info()
        
        # Server setup matching notebook pattern
        directory_path = str(self.repo.path)
        location = directory_path.split('src-data')[0] + 'src-data' if 'src-data' in directory_path else os.path.join(directory_path, 'src-data')
        
        # Use the provided src-data path if different
        if str(self.src_data_path) != location:
            location = str(self.src_data_path)
        
        prefix = self.repo.whoami
        
        print(f"📁 Repository: {self.repo.path}")
        print(f"🏷️  Prefix: {prefix}")
        print(f"📂 Location: {location}")
        
        # Create local server mapping
        local = [(location, cmipld.mapping.get(prefix, f"http://localhost:8000/"), prefix)]
        
        print("🌐 Starting LD_server...")
        self.server = LD_server(copy=local, use_ssl=False)
        
        print(f"✅ Server setup complete")
        return self.server
    
    def find_json_files(self) -> List[Path]:
        """Find all JSON files in src-data directory using glob pattern, excluding graph.json files."""
        json_files = []
        
        # Use glob to find JSON files recursively
        pattern = os.path.join(self.src_data_path, '**', '*.json')
        for file_path in glob.glob(pattern, recursive=True):
            path_obj = Path(file_path)
            # Ignore graph.json files
            if path_obj.name != 'graph.json':
                json_files.append(path_obj)
        
        # Also look for _context files
        context_pattern = os.path.join(self.src_data_path, '**', '_context')
        for file_path in glob.glob(context_pattern, recursive=True):
            json_files.append(Path(file_path))
        
        return json_files
    
    def extract_links_from_file(self, file_path: Path) -> Tuple[str, Set[str], Dict[str, Set[str]]]:
        """Extract links using cmipld library functions."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                return None, set(), {}
            
            # Get file ID
            file_id = data.get('id', data.get('@id', file_path.stem))
            
            # Convert to cmipld-style reference if possible
            relative_path = file_path.relative_to(self.src_data_path)
            
            # Try to create a proper cmipld reference
            if self.repo and self.repo.whoami:
                prefix = self.repo.whoami
                # Remove .json extension for cmipld reference
                ref_path = str(relative_path).replace('.json', '') if str(relative_path).endswith('.json') else str(relative_path)
                cmipld_ref = f"{prefix}:{ref_path}"
            else:
                cmipld_ref = str(relative_path)
            
            links = set()
            property_links = {}
            
            try:
                # Use cmipld depends function
                print(f"🔍 Analyzing dependencies for: {cmipld_ref}")
                deps = depends(cmipld_ref, relative=True)
                if deps:
                    links.update(deps)
                    print(f"   Found {len(deps)} dependencies")
                
                # Get detailed property links
                detailed_links = depends_keys_detailed(cmipld_ref, prefix=True)
                if detailed_links:
                    property_links.update(detailed_links)
                    print(f"   Found property links: {list(detailed_links.keys())}")
                
            except Exception as e:
                print(f"⚠️  Warning: cmipld link extraction failed for {file_path}: {e}")
                # Fallback to basic extraction from JSON data
                links.update(self.extract_links_fallback(data))
            
            return file_id, links, property_links
            
        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return None, set(), {}
    
    def extract_links_fallback(self, data: Dict[str, Any]) -> Set[str]:
        """Fallback method to extract links when cmipld functions fail."""
        links = set()
        
        def extract_ids_recursive(obj, visited=None):
            if visited is None:
                visited = set()
            
            if isinstance(obj, dict):
                if id(obj) in visited:
                    return
                visited.add(id(obj))
                
                # Check for @id fields
                if '@id' in obj:
                    links.add(str(obj['@id']))
                
                # Check for properties that might contain links
                link_properties = {
                    'activity', 'parent-experiment', 'model-realms',
                    'seeAlso', 'related', 'belongsTo', 'hasComponent', 
                    'definedBy', 'references', 'license', 'contact',
                    'experiment', 'variable', 'institution', 'model',
                    'creator', 'publisher', 'contributor'
                }
                
                for key, value in obj.items():
                    if key in link_properties:
                        if isinstance(value, str):
                            links.add(value)
                        elif isinstance(value, list):
                            for item in value:
                                if isinstance(item, str):
                                    links.add(item)
                                elif isinstance(item, dict) and '@id' in item:
                                    links.add(item['@id'])
                    
                    extract_ids_recursive(value, visited)
                    
            elif isinstance(obj, list):
                for item in obj:
                    extract_ids_recursive(item, visited)
        
        extract_ids_recursive(data)
        return links
    
    def categorize_links(self, links: Set[str], current_file_path: Path) -> Dict[str, Set[str]]:
        """Categorize links into internal files, external links, etc."""
        categorized = {
            'internal_files': set(),
            'external_urls': set(),
            'prefix_refs': set(),
            'unknown': set()
        }
        
        for link in links:
            if not link:
                continue
            
            # Check if it's a full URL
            if link.startswith(('http://', 'https://')):
                # Check if it's one of our known mappings
                is_internal = False
                for prefix, base_url in cmipld.mapping.items():
                    if link.startswith(base_url):
                        categorized['internal_files'].add(link)
                        is_internal = True
                        break
                
                if not is_internal:
                    categorized['external_urls'].add(link)
            
            # Check if it's a prefixed reference (e.g., "cmip7:experiment/amip")
            elif ':' in link and not link.startswith('http'):
                categorized['prefix_refs'].add(link)
            
            # Check for direct file ID matches
            elif link in self.all_file_ids:
                categorized['internal_files'].add(link)
            
            else:
                categorized['unknown'].add(link)
        
        return categorized
    
    def analyze_files(self):
        """Analyze all JSON files and extract links."""
        print(f"🔍 Analyzing JSON-LD files in: {self.src_data_path}")
        
        json_files = self.find_json_files()
        print(f"📄 Found {len(json_files)} JSON files")
        
        if not json_files:
            print("⚠️  No JSON files found!")
            return
        
        # First pass: collect all file IDs
        print("📋 First pass: collecting file IDs...")
        file_data = {}
        
        if HAS_TQDM:
            files_iter = tqdm(json_files, desc="Collecting file IDs")
        else:
            files_iter = json_files
        
        for file_path in files_iter:
            file_id, links, property_links = self.extract_links_from_file(file_path)
            if file_id:
                self.all_file_ids.add(file_id)
                file_data[file_path] = (file_id, links, property_links)
        
        print(f"🆔 Collected {len(self.all_file_ids)} file IDs")
        
        # Second pass: categorize links and build relationships
        print("🔗 Second pass: analyzing links...")
        directory_internal_links = defaultdict(set)
        
        if HAS_TQDM:
            data_iter = tqdm(file_data.items(), desc="Analyzing links")
        else:
            data_iter = file_data.items()
        
        for file_path, (file_id, links, property_links) in data_iter:
            # Get file location info
            relative_path = file_path.relative_to(self.src_data_path)
            directory = relative_path.parent
            
            # Categorize links
            categorized = self.categorize_links(links, file_path)
            
            # Combine internal references
            internal_file_links = (
                categorized['internal_files'] | 
                categorized['prefix_refs'] | 
                {link for link in categorized['unknown'] if link in self.all_file_ids}
            )
            other_file_links = [link for link in internal_file_links if link != file_id]
            
            # Add to file links
            self.file_links.append({
                'file_id': file_id,
                'rel': str(relative_path),
                'location': str(file_path),
                'directory': str(directory) if str(directory) != '.' else '',
                'links_to_files': list(other_file_links),
                'external_links': list(categorized['external_urls']),
                'total_links': len(links),
                'property_links': {k: list(v) for k, v in property_links.items()},
                'link_categories': {k: list(v) for k, v in categorized.items()}
            })
            
            # Track directory-level relationships
            if other_file_links:
                for link in other_file_links:
                    linked_file_dir = self.find_file_directory(link, file_data)
                    if linked_file_dir and linked_file_dir != directory:
                        directory_internal_links[str(directory)].add(str(linked_file_dir))
        
        # Build directory links
        for directory, linked_dirs in directory_internal_links.items():
            self.directory_links.append({
                'directory': directory,
                'links_to_directories': list(linked_dirs),
                'link_count': len(linked_dirs)
            })
        
        print(f"✅ Analysis complete: {len(self.file_links)} files, {len(self.directory_links)} directories")
    
    def find_file_directory(self, file_id: str, file_data: Dict) -> Path:
        """Find which directory a file ID belongs to."""
        for file_path, (fid, _, _) in file_data.items():
            if fid == file_id or file_id.endswith(fid) or fid.endswith(file_id):
                return file_path.parent.relative_to(self.src_data_path)
        
        # Try to match prefix-style references
        if ':' in file_id:
            _, local_part = file_id.split(':', 1)
            for file_path, (fid, _, _) in file_data.items():
                if local_part in str(file_path) or fid == local_part:
                    return file_path.parent.relative_to(self.src_data_path)
        
        return None
    
    def save_results(self, output_dir: Path):
        """Save analysis results to files."""
        output_dir.mkdir(exist_ok=True)
        
        # Save file links
        file_links_path = output_dir / 'file_links.json'
        with open(file_links_path, 'w', encoding='utf-8') as f:
            json.dump(self.file_links, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved file links to: {file_links_path}")
        
        # Save directory links  
        dir_links_path = output_dir / 'directory_links.json'
        with open(dir_links_path, 'w', encoding='utf-8') as f:
            json.dump(self.directory_links, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved directory links to: {dir_links_path}")
        
        # Save analysis summary
        summary = {
            'analysis_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'src_data_path': str(self.src_data_path),
            'cmipld_version': version() if hasattr(cmipld, 'version') else 'unknown',
            'repository_info': {
                'path': str(self.repo.path) if self.repo else None,
                'prefix': self.repo.whoami if self.repo else None,
                'branch': getattr(self.repo, 'branch', None) if self.repo else None
            },
            'prefix_mappings': dict(cmipld.mapping),
            'total_files': len(self.file_links),
            'total_directories': len(self.directory_links),
            'total_file_ids': len(self.all_file_ids),
            'files_with_links': len([f for f in self.file_links if f['links_to_files']]),
            'directories_with_links': len([d for d in self.directory_links if d['links_to_directories']])
        }
        
        summary_path = output_dir / 'analysis_summary.json'
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        print(f"📊 Saved analysis summary to: {summary_path}")
    
    def cleanup(self):
        """Clean up server resources."""
        if self.server:
            print("🛑 Shutting down LD_server...")
            try:
                # The LD_server might have a cleanup method
                if hasattr(self.server, 'stop'):
                    self.server.stop()
                elif hasattr(self.server, 'close'):
                    self.server.close()
            except Exception as e:
                print(f"⚠️  Warning during server cleanup: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze JSON-LD files using cmipld library to extract links and generate reports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze src-data directory
  python scripts/analyze_links.py src-data
  
  # Custom output directory
  python scripts/analyze_links.py src-data --output analysis-results
  
  # Skip server setup (direct file analysis only)
  python scripts/analyze_links.py src-data --no-server
        """
    )
    
    parser.add_argument(
        'src_data', 
        help='Path to src-data directory'
    )
    parser.add_argument(
        '--output', '-o',
        default='generated',
        help='Output directory for generated files (default: generated)'
    )
    parser.add_argument(
        '--no-server',
        action='store_true',
        help='Skip LD_server setup (analyze files directly)'
    )
    
    args = parser.parse_args()
    
    try:
        print("🚀 Starting CMIP-LD Link Analysis")
        print("=" * 50)
        
        # Create analyzer
        analyzer = CmipLDLinkAnalyzer(args.src_data)
        
        # Setup server if requested
        if not args.no_server:
            try:
                analyzer.setup_server()
            except Exception as e:
                print(f"⚠️  Server setup failed: {e}")
                print("   Continuing with direct file analysis...")
        else:
            print("⏭️  Skipping server setup as requested")
        
        # Run analysis
        print("\n🔍 Starting link analysis...")
        analyzer.analyze_files()
        
        # Save results
        output_path = Path(args.output)
        print(f"\n💾 Saving results to: {output_path.absolute()}")
        analyzer.save_results(output_path)
        
        # Print summary
        print("\n" + "="*60)
        print("📊 ANALYSIS SUMMARY")
        print("="*60)
        print(f"Files analyzed: {len(analyzer.file_links)}")
        print(f"Directories analyzed: {len(analyzer.directory_links)}")
        print(f"Total file IDs found: {len(analyzer.all_file_ids)}")
        
        files_with_links = len([f for f in analyzer.file_links if f['links_to_files']])
        dirs_with_links = len([d for d in analyzer.directory_links if d['links_to_directories']])
        print(f"Files with internal links: {files_with_links}")
        print(f"Directories with cross-links: {dirs_with_links}")
        
        print(f"\nOutput files:")
        print(f"  📄 file_links.json - File-level link relationships")
        print(f"  📁 directory_links.json - Directory-level link relationships") 
        print(f"  📊 analysis_summary.json - Analysis metadata")
        print("="*60)
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⚠️ Analysis interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        try:
            if 'analyzer' in locals():
                analyzer.cleanup()
        except Exception as e:
            print(f"⚠️  Cleanup warning: {e}")


if __name__ == "__main__":
    sys.exit(main())
