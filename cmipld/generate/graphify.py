#!/usr/bin/env python3
"""
graphify - Generate JSON-LD graphs, RDF/Turtle, and visualization JSON

This tool processes vocabulary directories to generate:
1. JSON-LD graph files (_graph.json) - Collection of all entities
2. RDF/Turtle files (_graph.ttl) - Semantic web format (if .ttl allowed)
3. D3/Graphology JSON files - For visualization
   - _d3graph.json: Entity-level relationship graph
   - _d3structure.json: Folder-level structure graph

Usage:
    graphify --all                      # Process all vocabulary directories
    graphify --dir vocab_name           # Process single directory  
    graphify --dirs vocab1 vocab2       # Process specific directories
    graphify --visualize                # Generate visualization JSON only
    
    # In GitHub Actions:
    graphify --all --output-summary     # Output to GitHub Actions summary
"""

import argparse
import json
import sys
import os
import re
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


# =============================================================================
# Styling Utilities (inline fallbacks if cmipld.utils.styling not available)
# =============================================================================

DEFAULT_COLORS = {
    'primary': '#2196f3',
    'primary_light': '#bbdefb', 
    'primary_dark': '#1976d2',
    'secondary': '#ff9800',
    'success': '#4caf50',
    'warning': '#ff9800',
    'error': '#f44336',
    'grey': '#808080',
    'grey_light': '#e0e0e0',
}


def get_colors_from_css(
    css_path: str = 'docs/stylesheets/custom.css',
    prefix: str = 'emd',
    defaults: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """Extract color variables from a CSS file."""
    colors = dict(defaults or DEFAULT_COLORS)
    
    try:
        with open(css_path, 'r') as f:
            css = f.read()
        
        pattern = rf'--{prefix}-([a-z0-9-]+):\s*([^;]+);'
        for match in re.finditer(pattern, css, re.IGNORECASE):
            key = match.group(1).replace('-', '_')
            value = match.group(2).strip()
            colors[key] = value
            
    except (FileNotFoundError, IOError):
        pass
    
    return colors


def get_project_colors(base_dir: Optional[Path] = None) -> Dict[str, str]:
    """Get colors for the current project."""
    if base_dir is None:
        base_dir = Path.cwd()
    
    css_paths = [
        'docs/stylesheets/custom.css',
        'docs/css/custom.css',
        'docs/assets/css/custom.css',
    ]
    
    # Try to detect prefix
    prefix = 'emd'
    try:
        import cmipld
        prefix = cmipld.prefix()
    except:
        pass
    
    for css_path in css_paths:
        full_path = base_dir / css_path
        if full_path.exists():
            return get_colors_from_css(str(full_path), prefix)
    
    return dict(DEFAULT_COLORS)


# =============================================================================
# Core Functions
# =============================================================================

def find_vocab_directories(base_path: Path = Path(".")) -> List[Path]:
    """
    Find all vocabulary directories (those with _context files).
    
    Args:
        base_path: Base directory to search from
        
    Returns:
        List of vocabulary directory paths
    """
    skip_dirs = {"docs", "summaries", ".github", "project", "ignore", 
                 ".git", "node_modules", "__pycache__"}
    vocab_dirs = []
    
    for item in base_path.iterdir():
        if not item.is_dir():
            continue
        
        if item.name in skip_dirs or item.name.startswith("."):
            continue
        
        # Check for _context or _context.json file
        if (item / "_context").exists() or (item / "_context.json").exists():
            vocab_dirs.append(item)
    
    return sorted(vocab_dirs)


def get_context_file(vocab_dir: Path) -> Optional[Path]:
    """Get the context file path for a vocabulary directory."""
    for name in ["_context.json", "_context"]:
        path = vocab_dir / name
        if path.exists():
            return path
    return None


def generate_jsonld_graph(vocab_dir: Path, verbose: bool = True) -> Dict[str, Any]:
    """
    Generate JSON-LD graph file from vocabulary directory.
    
    Collects all JSON files in the directory and creates a Collection graph.
    Uses .json extension for compatibility with restrictive .gitignore patterns.
    """
    result = {
        "directory": vocab_dir.name,
        "status": "success",
        "message": "",
        "files_created": [],
        "entity_count": 0
    }
    
    try:
        # Load context
        ctx_file = get_context_file(vocab_dir)
        if not ctx_file:
            result["status"] = "warning"
            result["message"] = "No _context file found"
            return result
        
        with open(ctx_file, 'r') as f:
            ctx = json.load(f)
        
        # Collect all entity IDs
        ids = []
        for json_file in glob.glob(str(vocab_dir / "*.json")):
            basename = os.path.basename(json_file)
            if basename.startswith("_"):
                continue
            
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                if "@id" in data:
                    ids.append(data["@id"])
            except (json.JSONDecodeError, KeyError):
                continue
        
        result["entity_count"] = len(ids)
        
        # Create graph document
        graph = {
            "@context": ctx.get("@context", ctx),
            "@type": ["Collection"],
            "contents": [{"@id": i} for i in ids]
        }
        
        # Write graph file (compact format for @id references)
        # Use .json extension for gitignore compatibility
        graph_file = vocab_dir / "_graph.json"
        graph_json = json.dumps(graph, indent=2)
        # Compact single-key objects
        graph_json = re.sub(
            r'\{\s+"@id":\s+"([^"]+)"\s+\}',
            r'{"@id": "\1"}',
            graph_json
        )
        
        with open(graph_file, 'w') as f:
            f.write(graph_json)
        result["files_created"].append("_graph.json")
        
        if verbose:
            print(f"  ✓ _graph.json ({len(ids)} entities)")
        
        result["message"] = f"{len(ids)} entities"
        
    except Exception as e:
        result["status"] = "failed"
        result["message"] = str(e)[:100]
    
    return result


def generate_rdf_turtle(
    vocab_dir: Path, 
    prefix: str,
    cmipld_module: Any = None,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Generate RDF/Turtle file from JSON-LD graph.
    
    Requires cmipld and rdflib to be available.
    Note: .ttl files may be gitignored in some repos.
    """
    result = {
        "directory": vocab_dir.name,
        "status": "success", 
        "message": "",
        "files_created": [],
        "graph": None
    }
    
    # Check for required modules
    try:
        from rdflib import Graph as RGraph, Namespace
        from rdflib.namespace import NamespaceManager
    except ImportError:
        result["status"] = "skipped"
        result["message"] = "rdflib not available"
        return result
    
    if cmipld_module is None:
        result["status"] = "skipped"
        result["message"] = "cmipld not available"
        return result
    
    try:
        # Add vocabulary namespace mappings
        vocab_types = [
            'Model', 'ModelFamily', 'ModelComponent', 'ComponentConfig',
            'HorizontalComputationalGrid', 'HorizontalGridCells',
            'HorizontalSubgrid', 'VerticalComputationalGrid'
        ]
        for v in vocab_types:
            cmipld_module.mapping[f'vocab_{v}'] = f'https://{prefix}.mipcvs.dev/docs/vocabularies/{v}/'
        
        # Expand JSON-LD (use .json extension now)
        graph_file = f'{prefix}:{vocab_dir.name}/_graph.json'
        data = cmipld_module.expand(graph_file, depth=3)
        
        # Create RDF graph
        g = RGraph()
        g.namespace_manager = NamespaceManager(g)
        
        # Bind prefixes
        for p, u in cmipld_module.mapping.items():
            try:
                g.bind(p, Namespace(u), replace=True)
            except:
                pass
        
        # Parse JSON-LD
        g.parse(data=json.dumps(data), format='json-ld')
        
        # Serialize to Turtle
        ttl_file = vocab_dir / "_graph.ttl"
        g.serialize(str(ttl_file), format='turtle')
        result["files_created"].append("_graph.ttl")
        result["graph"] = g
        
        if verbose:
            print(f"  ✓ _graph.ttl ({len(g)} triples)")
        
        result["message"] = f"{len(g)} triples"
        
    except Exception as e:
        result["status"] = "failed"
        result["message"] = str(e)[:100]
    
    return result


def extract_relationships(
    rdf_graphs: Dict[str, Any],
    prefix: str,
    mappings: Dict[str, str]
) -> List[Tuple[str, str, str]]:
    """Extract relationships from RDF graphs."""
    try:
        from rdflib import URIRef
    except ImportError:
        return []
    
    def shorten(uri):
        if not isinstance(uri, URIRef):
            return str(uri)
        uri_str = str(uri)
        for p, ns in mappings.items():
            if uri_str.startswith(ns):
                local = uri_str[len(ns):]
                if 'docs/vocabularies/' in local:
                    local = local.split('/')[-1]
                return f'{p}:{local}'
        return uri_str
    
    relationships = []
    for g in rdf_graphs.values():
        for s, p, o in g:
            # Skip W3C predicates
            if 'www.w3.org' in str(p):
                continue
            # Only include internal relationships
            if 'mipcvs.dev' in str(s) and 'mipcvs.dev' in str(o):
                relationships.append((shorten(s), shorten(p), shorten(o)))
    
    return relationships


def generate_d3_graph(
    relationships: List[Tuple[str, str, str]],
    prefix: str,
    colors: Dict[str, str],
    output_path: Path,
    verbose: bool = True
) -> Dict[str, Any]:
    """Generate D3/Graphology JSON for entity-level visualization."""
    result = {
        "status": "success",
        "message": "",
        "node_count": 0,
        "edge_count": 0
    }
    
    if not relationships:
        result["status"] = "skipped"
        result["message"] = "No relationships available"
        return result
    
    try:
        nodes = []
        edges = []
        seen_nodes = set()
        
        for s, p, t in relationships:
            # Add source node
            if s not in seen_nodes:
                nodes.append({
                    'id': s,
                    'label': s.split('/')[-1],
                    'color': colors.get('primary', '#2196f3') if s.startswith(f'{prefix}:') else colors.get('grey', '#808080')
                })
                seen_nodes.add(s)
            
            # Add target node
            if t not in seen_nodes:
                nodes.append({
                    'id': t,
                    'label': t.split('/')[-1],
                    'color': colors.get('primary', '#2196f3') if t.startswith(f'{prefix}:') else colors.get('grey', '#808080')
                })
                seen_nodes.add(t)
            
            # Add edge
            edges.append({
                'source': s,
                'target': t,
                'label': p,
                'color': colors.get('primary_light', '#bbdefb')
            })
        
        # Write file
        graph_data = {'nodes': nodes, 'links': edges}
        with open(output_path, 'w') as f:
            json.dump(graph_data, f, indent=2)
        
        result["node_count"] = len(nodes)
        result["edge_count"] = len(edges)
        result["message"] = f"{len(nodes)} nodes, {len(edges)} edges"
        
        if verbose:
            print(f"✓ {output_path.name}: {result['message']}")
        
    except Exception as e:
        result["status"] = "failed"
        result["message"] = str(e)[:100]
    
    return result


def generate_d3_structure(
    relationships: List[Tuple[str, str, str]],
    prefix: str,
    colors: Dict[str, str],
    output_path: Path,
    root_label: str = "Root",
    verbose: bool = True
) -> Dict[str, Any]:
    """Generate D3/Graphology JSON for folder-level structure visualization."""
    result = {
        "status": "success",
        "message": "",
        "node_count": 0,
        "edge_count": 0
    }
    
    if not relationships:
        result["status"] = "skipped"
        result["message"] = "No relationships available"
        return result
    
    try:
        # Root node
        nodes = [{
            'id': 'root',
            'label': root_label,
            'color': colors.get('primary_dark', '#1976d2'),
            'size': 30
        }]
        edges = []
        folder_set = set()
        folder_links = defaultdict(int)
        
        def get_folder(uri):
            return uri.rsplit('/', 1)[0] if '/' in uri else uri
        
        for s, p, t in relationships:
            sf, tf = get_folder(s), get_folder(t)
            
            if sf and tf:
                # Add folder nodes
                for f in [sf, tf]:
                    if f not in folder_set and f:
                        folder_set.add(f)
                        nodes.append({
                            'id': f,
                            'label': f.split(':')[-1],
                            'color': colors.get('primary_light', '#bbdefb') if f.startswith(f'{prefix}:') else colors.get('grey', '#808080'),
                            'size': 15
                        })
                        
                        # Connect to root if internal
                        if f.startswith(f'{prefix}:'):
                            edges.append({
                                'source': 'root',
                                'target': f,
                                'label': 'contains',
                                'color': colors.get('primary_light', '#bbdefb')
                            })
                
                # Count inter-folder links
                if sf != tf:
                    folder_links[(sf, tf)] += 1
        
        # Add inter-folder edges
        for (sf, tf), cnt in folder_links.items():
            edges.append({
                'source': sf,
                'target': tf,
                'label': f'{cnt} links',
                'color': colors.get('primary_light', '#bbdefb'),
                'weight': cnt
            })
        
        # Write file
        graph_data = {
            'nodes': nodes,
            'links': edges,
            'directed': True,
            'multigraph': True
        }
        with open(output_path, 'w') as f:
            json.dump(graph_data, f, indent=2)
        
        result["node_count"] = len(nodes)
        result["edge_count"] = len(edges)
        result["message"] = f"{len(nodes)} nodes, {len(edges)} edges"
        
        if verbose:
            print(f"✓ {output_path.name}: {result['message']}")
        
    except Exception as e:
        result["status"] = "failed"
        result["message"] = str(e)[:100]
    
    return result


def process_all(
    base_path: Path = Path("."),
    vocab_dirs: Optional[List[Path]] = None,
    generate_rdf: bool = True,
    generate_viz: bool = True,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Process all vocabulary directories and generate all outputs.
    
    Args:
        base_path: Base directory
        vocab_dirs: Specific directories to process (None = auto-detect)
        generate_rdf: Generate RDF/Turtle files
        generate_viz: Generate visualization JSON files
        verbose: Print progress messages
        
    Returns:
        Dictionary with all results
    """
    results = {
        "jsonld": [],
        "rdf": [],
        "viz": {},
        "summary": {}
    }
    
    # Try to import cmipld
    cmipld_module = None
    prefix = 'emd'
    mappings = {}
    
    try:
        import cmipld
        cmipld_module = cmipld
        prefix = cmipld.prefix()
        cmipld.map_current(prefix)
        mappings = cmipld.mapping
        if verbose:
            print(f"Project prefix: {prefix}")
    except ImportError:
        if verbose:
            print("cmipld not available - using defaults")
            print(f"Project prefix: {prefix}")
    except Exception as e:
        if verbose:
            print(f"cmipld error: {e}")
            print(f"Project prefix: {prefix}")
    
    colors = get_project_colors(base_path)
    if verbose:
        print(f"Colors: primary={colors.get('primary', 'default')}\n")
    
    # Find directories
    if vocab_dirs is None:
        vocab_dirs = find_vocab_directories(base_path)
    
    if not vocab_dirs:
        print("No vocabulary directories found")
        return results
    
    if verbose:
        print(f"Found {len(vocab_dirs)} vocabulary directories\n")
        print("=" * 60)
        print("Generating JSON-LD graphs...")
        print("=" * 60)
    
    # Generate JSON-LD graphs
    for vocab_dir in vocab_dirs:
        if verbose:
            print(f"\nProcessing: {vocab_dir.name}")
        result = generate_jsonld_graph(vocab_dir, verbose=verbose)
        results["jsonld"].append(result)
    
    # Generate RDF/Turtle
    rdf_graphs = {}
    if generate_rdf and cmipld_module is not None:
        if verbose:
            print("\n" + "=" * 60)
            print("Generating RDF/Turtle...")
            print("=" * 60)
        
        for vocab_dir in vocab_dirs:
            if verbose:
                print(f"\nProcessing: {vocab_dir.name}")
            result = generate_rdf_turtle(vocab_dir, prefix, cmipld_module, verbose=verbose)
            results["rdf"].append(result)
            if result.get("graph") is not None:
                rdf_graphs[vocab_dir.name] = result["graph"]
    elif generate_rdf:
        if verbose:
            print("\n⚠ Skipping RDF generation (cmipld not available)")
    
    # Generate visualization JSON
    relationships = []
    if generate_viz and rdf_graphs:
        if verbose:
            print("\n" + "=" * 60)
            print("Generating visualization JSON...")
            print("=" * 60 + "\n")
        
        relationships = extract_relationships(rdf_graphs, prefix, mappings)
        if verbose:
            print(f"Extracted {len(relationships)} relationships\n")
        
        # Entity-level graph
        results["viz"]["d3graph"] = generate_d3_graph(
            relationships, prefix, colors,
            base_path / "_d3graph.json",
            verbose=verbose
        )
        
        # Structure graph
        root_label = prefix.upper() if prefix else "Root"
        results["viz"]["d3structure"] = generate_d3_structure(
            relationships, prefix, colors,
            base_path / "_d3structure.json",
            root_label=root_label,
            verbose=verbose
        )
    elif generate_viz:
        if verbose:
            print("\n⚠ Skipping visualization (no RDF graphs available)")
    
    # Summary
    jsonld_success = sum(1 for r in results["jsonld"] if r["status"] == "success")
    rdf_success = sum(1 for r in results["rdf"] if r["status"] == "success")
    
    results["summary"] = {
        "jsonld_processed": len(results["jsonld"]),
        "jsonld_success": jsonld_success,
        "rdf_processed": len(results["rdf"]),
        "rdf_success": rdf_success,
        "relationships_extracted": len(relationships) if generate_viz else 0
    }
    
    return results


def print_summary(results: Dict[str, Any]):
    """Print a summary of processing results."""
    print("\n" + "=" * 60)
    print("GRAPHIFY SUMMARY")
    print("=" * 60)
    
    summary = results.get("summary", {})
    
    print(f"\nJSON-LD: {summary.get('jsonld_success', 0)}/{summary.get('jsonld_processed', 0)} successful")
    print(f"RDF/TTL: {summary.get('rdf_success', 0)}/{summary.get('rdf_processed', 0)} successful")
    print(f"Relationships: {summary.get('relationships_extracted', 0)} extracted")
    
    # Visualization files
    viz = results.get("viz", {})
    if viz.get("d3graph", {}).get("status") == "success":
        d3g = viz["d3graph"]
        print(f"\n_d3graph.json: {d3g['node_count']} nodes, {d3g['edge_count']} edges")
    if viz.get("d3structure", {}).get("status") == "success":
        d3s = viz["d3structure"]
        print(f"_d3structure.json: {d3s['node_count']} nodes, {d3s['edge_count']} edges")
    
    # Errors
    errors = []
    for r in results.get("jsonld", []) + results.get("rdf", []):
        if r["status"] == "failed":
            errors.append(f"  {r['directory']}: {r['message']}")
    
    if errors:
        print("\nErrors:")
        for e in errors:
            print(e)
    
    print("=" * 60 + "\n")


def output_github_summary(results: Dict[str, Any]):
    """Output results to GitHub Actions summary."""
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return
    
    with open(summary_file, "a") as f:
        f.write("## Graphify Report\n\n")
        
        # JSON-LD table
        f.write("### JSON-LD Generation\n\n")
        f.write("| Directory | Status | Entities |\n")
        f.write("|-----------|--------|----------|\n")
        
        for r in results.get("jsonld", []):
            emoji = "✅" if r["status"] == "success" else "❌"
            f.write(f"| `{r['directory']}` | {emoji} | {r.get('entity_count', 0)} |\n")
        
        # RDF table
        if results.get("rdf"):
            f.write("\n### RDF/Turtle Generation\n\n")
            f.write("| Directory | Status | Details |\n")
            f.write("|-----------|--------|----------|\n")
            
            for r in results.get("rdf", []):
                emoji = {"success": "✅", "failed": "❌", "skipped": "⏭️"}.get(r["status"], "❓")
                f.write(f"| `{r['directory']}` | {emoji} | {r['message']} |\n")
        
        # Visualization
        viz = results.get("viz", {})
        if viz:
            f.write("\n### Visualization Files\n\n")
            if viz.get("d3graph", {}).get("status") == "success":
                d3g = viz["d3graph"]
                f.write(f"- `_d3graph.json`: {d3g['node_count']} nodes, {d3g['edge_count']} edges\n")
            if viz.get("d3structure", {}).get("status") == "success":
                d3s = viz["d3structure"]
                f.write(f"- `_d3structure.json`: {d3s['node_count']} nodes, {d3s['edge_count']} edges\n")
        
        # Summary
        summary = results.get("summary", {})
        f.write(f"\n**Total**: {summary.get('jsonld_success', 0)}/{summary.get('jsonld_processed', 0)} JSON-LD, ")
        f.write(f"{summary.get('rdf_success', 0)}/{summary.get('rdf_processed', 0)} RDF\n")


def main():
    """Main entry point for graphify CLI."""
    parser = argparse.ArgumentParser(
        description="Generate JSON-LD graphs, RDF/Turtle, and visualization JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  graphify --all                    Process all vocabulary directories
  graphify --dir vocab_name         Process single directory
  graphify vocab1 vocab2            Process specific directories
  graphify --all --no-rdf           Skip RDF generation
  graphify --visualize-only         Regenerate visualization JSON only
  
GitHub Actions:
  graphify --all --output-summary   Output to GitHub Actions summary
        """
    )
    
    # Directory selection
    parser.add_argument(
        "directories",
        nargs="*",
        help="Directory names to process"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all vocabulary directories"
    )
    parser.add_argument(
        "--dir",
        type=str,
        help="Single directory to process"
    )
    parser.add_argument(
        "--dirs",
        type=str,
        nargs="+",
        help="List of directories to process"
    )
    
    # Generation options
    parser.add_argument(
        "--no-rdf",
        action="store_true",
        help="Skip RDF/Turtle generation"
    )
    parser.add_argument(
        "--no-viz",
        action="store_true",
        help="Skip visualization JSON generation"
    )
    parser.add_argument(
        "--visualize-only",
        action="store_true",
        help="Only regenerate visualization JSON (requires existing RDF)"
    )
    
    # Output options
    parser.add_argument(
        "--output-summary",
        action="store_true",
        help="Output GitHub Actions summary"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("."),
        help="Base directory (default: current)"
    )
    
    args = parser.parse_args()
    
    # Determine directories
    if args.all:
        vocab_dirs = find_vocab_directories(args.base_dir)
    elif args.dir:
        vocab_dirs = [Path(args.dir)]
    elif args.dirs:
        vocab_dirs = [Path(d) for d in args.dirs]
    elif args.directories:
        vocab_dirs = [Path(d) for d in args.directories]
    else:
        vocab_dirs = find_vocab_directories(args.base_dir)
    
    if not vocab_dirs and not args.visualize_only:
        print("No vocabulary directories found")
        return 0
    
    # Process
    results = process_all(
        base_path=args.base_dir,
        vocab_dirs=vocab_dirs if not args.visualize_only else None,
        generate_rdf=not args.no_rdf,
        generate_viz=not args.no_viz,
        verbose=not args.quiet
    )
    
    # Output
    if not args.quiet:
        print_summary(results)
    
    if args.output_summary:
        output_github_summary(results)
    
    # Exit code
    errors = sum(1 for r in results.get("jsonld", []) + results.get("rdf", []) 
                 if r["status"] == "failed")
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
