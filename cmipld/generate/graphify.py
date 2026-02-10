#!/usr/bin/env python3
"""
graphify - Generate JSON-LD graphs for vocabulary directories

This tool generates graph.jsonld files from JSON-LD vocabulary directories.
It can use either the ld2graph command or a pure Python implementation.

Usage:
    graphify --all                      # Process all vocabulary directories
    graphify --dir vocab_name           # Process single directory
    graphify --dirs vocab1 vocab2       # Process specific directories
    graphify vocab1 vocab2              # Short form
    
    # In GitHub Actions:
    graphify --all --output-summary     # Output to GitHub Actions summary
"""

import argparse
import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import subprocess


def find_vocab_directories(base_path: Path = Path(".")) -> List[Path]:
    """
    Find all vocabulary directories (those with _context files).
    
    Args:
        base_path: Base directory to search from
        
    Returns:
        List of vocabulary directory paths
    """
    skip_dirs = {"docs", "summaries", ".github", "project", "ignore", ".git", "node_modules"}
    vocab_dirs = []
    
    for item in base_path.iterdir():
        if not item.is_dir():
            continue
        
        if item.name in skip_dirs or item.name.startswith("."):
            continue
        
        # Check for _context file
        if (item / "_context").exists():
            vocab_dirs.append(item)
    
    return sorted(vocab_dirs)


def generate_graph_with_ld2graph(vocab_dir: Path, verbose: bool = True) -> Dict[str, Any]:
    """
    Generate graph using the ld2graph command.
    
    Args:
        vocab_dir: Path to vocabulary directory
        verbose: Print progress messages
        
    Returns:
        Dictionary with status information
    """
    result = {
        "directory": vocab_dir.name,
        "status": "success",
        "message": "",
        "files_created": []
    }
    
    if verbose:
        print(f"  Running ld2graph...")
    
    try:
        # Run ld2graph command
        process = subprocess.run(
            ["ld2graph", "."],
            cwd=vocab_dir,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if process.returncode != 0:
            result["status"] = "failed"
            result["message"] = f"ld2graph failed: {process.stderr[:100]}"
            return result
        
        # Check if graph.jsonld was created
        graph_file = vocab_dir / "graph.jsonld"
        if not graph_file.exists():
            result["status"] = "warning"
            result["message"] = "graph.jsonld not created"
            return result
        
        result["files_created"].append("graph.jsonld")
        
        if verbose:
            print(f"  ✓ graph.jsonld created")
        
        # Create minified version
        with open(graph_file, 'r') as f:
            graph_data = json.load(f)
        
        # Write minified version
        min_file = vocab_dir / "graph.min.json"
        with open(min_file, 'w') as f:
            json.dump(graph_data, f, separators=(',', ':'))
        result["files_created"].append("graph.min.json")
        
        # Create copies without extension (for content negotiation)
        for name in ["graph", "graph.json"]:
            target = vocab_dir / name
            target.write_bytes(min_file.read_bytes())
            result["files_created"].append(name)
        
        if verbose:
            print(f"  ✓ Created {len(result['files_created'])} files")
        
        result["message"] = "Success"
        
    except subprocess.TimeoutExpired:
        result["status"] = "failed"
        result["message"] = "Timeout after 60 seconds"
    except FileNotFoundError:
        result["status"] = "failed"
        result["message"] = "ld2graph command not found - install cmipld"
    except Exception as e:
        result["status"] = "failed"
        result["message"] = str(e)[:100]
    
    return result


def print_summary(results: List[Dict[str, Any]]):
    """Print a summary table of results."""
    if not results:
        return
    
    print("\n" + "="*70)
    print("GRAPH GENERATION SUMMARY")
    print("="*70)
    
    # Count statuses
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    warning = sum(1 for r in results if r["status"] == "warning")
    
    print(f"\nTotal: {len(results)} directories")
    if success > 0:
        print(f"  ✓ Success: {success}")
    if failed > 0:
        print(f"  ✗ Failed: {failed}")
    if warning > 0:
        print(f"  ⚠ Warnings: {warning}")
    
    # Detailed results
    print("\nDetailed Results:")
    print("-" * 70)
    for result in results:
        status_icon = {
            "success": "✓",
            "failed": "✗",
            "warning": "⚠"
        }.get(result["status"], "?")
        
        print(f"{status_icon} {result['directory']:25s} {result['message']}")
        if result["files_created"]:
            files_str = ", ".join(result['files_created'])
            print(f"  Files: {files_str}")
    
    print("="*70 + "\n")


def output_github_summary(results: List[Dict[str, Any]]):
    """Output results to GitHub Actions summary."""
    summary_file = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return
    
    with open(summary_file, "a") as f:
        f.write("## Graph Generation Report\n\n")
        f.write("| Directory | Status | Details |\n")
        f.write("|-----------|--------|----------|\n")
        
        for result in results:
            status_emoji = {
                "success": "✅",
                "failed": "❌",
                "warning": "⚠️"
            }.get(result["status"], "❓")
            
            f.write(f"| `{result['directory']}` | {status_emoji} | {result['message']} |\n")
        
        success = sum(1 for r in results if r["status"] == "success")
        f.write(f"\n**Completed**: {success}/{len(results)} directories\n")


def main():
    """Main entry point for graphify CLI."""
    parser = argparse.ArgumentParser(
        description="Generate JSON-LD graphs for vocabulary directories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  graphify --all                    Process all vocabulary directories
  graphify --dir vocab_name         Process single directory
  graphify vocab1 vocab2 vocab3     Process specific directories
  graphify --all --quiet            Process all (minimal output)
  
GitHub Actions:
  graphify --all --output-summary   Output to GitHub Actions summary
        """
    )
    
    # Directory selection
    parser.add_argument(
        "directories",
        nargs="*",
        help="Directory names to process (default argument)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Process all vocabulary directories (with _context files)"
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
        help="List of directory names to process"
    )
    
    # Options
    parser.add_argument(
        "--method",
        choices=["ld2graph", "python"],
        default="ld2graph",
        help="Method to use for graph generation (default: ld2graph)"
    )
    parser.add_argument(
        "--output-summary",
        action="store_true",
        help="Output GitHub Actions summary markdown"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Minimal output (only errors)"
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=Path("."),
        help="Base directory to search from (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Determine which directories to process
    if args.all:
        vocab_dirs = find_vocab_directories(args.base_dir)
        if not args.quiet:
            print(f"Found {len(vocab_dirs)} vocabulary directories")
    elif args.dir:
        vocab_dirs = [Path(args.dir)]
    elif args.dirs:
        vocab_dirs = [Path(name) for name in args.dirs]
    elif args.directories:
        vocab_dirs = [Path(name) for name in args.directories]
    else:
        # Default: find all
        vocab_dirs = find_vocab_directories(args.base_dir)
        if not vocab_dirs:
            print("No vocabulary directories found. Use --help for usage.")
            return 0
    
    if not vocab_dirs:
        print("No vocabulary directories to process")
        return 0
    
    if not args.quiet:
        print(f"\nProcessing {len(vocab_dirs)} directories...\n")
    
    # Generate graphs
    results = []
    for vocab_dir in vocab_dirs:
        if not vocab_dir.exists():
            results.append({
                "directory": vocab_dir.name,
                "status": "failed",
                "message": "Directory not found",
                "files_created": []
            })
            if not args.quiet:
                print(f"✗ {vocab_dir.name}: Directory not found")
            continue
        
        if not args.quiet:
            print(f"Processing: {vocab_dir.name}")
        
        if args.method == "ld2graph":
            result = generate_graph_with_ld2graph(vocab_dir, verbose=not args.quiet)
        else:
            result = generate_graph_python(vocab_dir)
        
        results.append(result)
        
        if not args.quiet:
            status_icon = "✓" if result["status"] == "success" else "✗"
            print(f"  {status_icon} {result['message']}\n")
    
    # Print summary
    if not args.quiet:
        print_summary(results)
    
    # Output GitHub Actions summary if requested
    if args.output_summary:
        output_github_summary(results)
    
    # Return exit code
    if any(r["status"] == "failed" for r in results):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
