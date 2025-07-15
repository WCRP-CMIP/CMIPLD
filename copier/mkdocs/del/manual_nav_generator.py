#!/usr/bin/env python3
"""
Manual script to generate SUMMARY.md for your docs
Run this in your project root after copying the template
"""

import os
import sys
from pathlib import Path
import re

def get_sort_key(filename):
    """Extract sort key from filename for proper ordering."""
    import re
    # Extract leading number if present
    match = re.match(r'^(\d+)[-_.]', filename)
    if match:
        return (int(match.group(1)), filename)
    else:
        # No number prefix, treat as 0 for sorting
        return (0, filename)

def clean_title(filename):
    """Clean filename to create a nice title."""
    name = filename.replace('.md', '')
    # Remove leading numbers only if followed by separator
    name = re.sub(r'^\d+[-_.](?=\w)', '', name)
    # Replace underscores and hyphens with spaces
    name = name.replace('_', ' ').replace('-', ' ')
    # Title case
    return name.title()

def generate_nav():
    """Generate navigation for all markdown files."""
    # Find docs directory
    if os.path.exists('../../docs'):
        docs_dir = Path('../../docs')
    elif os.path.exists('docs'):
        docs_dir = Path('docs')
    else:
        print("Error: Cannot find docs directory")
        return
    
    print(f"Scanning {docs_dir.absolute()}")
    
    # Collect all markdown files
    md_files = list(docs_dir.rglob('*.md'))
    # Sort by the sort key (number prefix or 0)
    md_files.sort(key=lambda f: get_sort_key(f.name))
    
    nav_lines = []
    
    # Add home if exists
    if (docs_dir / 'index.md').exists():
        nav_lines.append('- [Home](index.md)')
    
    # Process files by directory
    processed = set()
    processed.add('index.md')
    
    # First, add all top-level files
    for f in md_files:
        rel_path = f.relative_to(docs_dir)
        if len(rel_path.parts) == 1 and str(rel_path) not in processed:
            if not str(rel_path).startswith('.'):
                title = clean_title(f.stem)
                nav_lines.append(f'- [{title}]({rel_path})')
                processed.add(str(rel_path))
    
    # Then add directories
    dirs_processed = set()
    for f in md_files:
        rel_path = f.relative_to(docs_dir)
        if len(rel_path.parts) > 1:
            # Process directory structure
            parts = rel_path.parts
            
            # Add directory if not yet added
            dir_name = parts[0]
            if dir_name not in dirs_processed and not dir_name.startswith('.'):
                dirs_processed.add(dir_name)
                dir_title = clean_title(dir_name)
                nav_lines.append(f'- {dir_title}:')
                
                # Add all files in this directory
                for subf in md_files:
                    sub_rel = subf.relative_to(docs_dir)
                    if len(sub_rel.parts) > 1 and sub_rel.parts[0] == dir_name:
                        if len(sub_rel.parts) == 2:
                            # Direct child
                            file_title = clean_title(subf.stem)
                            nav_lines.append(f'  - [{file_title}]({sub_rel})')
    
    # Write SUMMARY.md
    summary_path = docs_dir / 'SUMMARY.md'
    with open(summary_path, 'w') as f:
        f.write('\n'.join(nav_lines))
    
    print(f"\nGenerated {summary_path}")
    print(f"Total files: {len(md_files)}")
    print("\nNavigation preview:")
    print("-" * 40)
    for line in nav_lines[:10]:
        print(line)
    if len(nav_lines) > 10:
        print("...")
    print("-" * 40)

if __name__ == "__main__":
    generate_nav()
