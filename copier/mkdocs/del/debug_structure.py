#!/usr/bin/env python3
"""
Debug version to find why numbered files aren't appearing
"""

from pathlib import Path
import json

# Test the exact file structure
docs_path = Path("../../docs")

if docs_path.exists():
    print(f"Scanning {docs_path.absolute()}")
    
    # Get all files
    all_files = []
    for f in docs_path.rglob("*.md"):
        if not any(p.startswith('.') for p in f.parts):
            all_files.append(str(f.relative_to(docs_path)))
    
    all_files.sort()
    
    print(f"\nFound {len(all_files)} files:")
    for f in all_files:
        print(f"  - {f}")
    
    # Test the structure building
    existing_files = {}
    
    for file_path in all_files:
        parts = file_path.split('/')
        
        # Build hierarchy
        current = existing_files
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Add file
        filename = parts[-1]
        current[filename] = {
            'title': filename.replace('.md', '').title(),
            'path': file_path
        }
    
    print(f"\nStructure:")
    print(json.dumps(existing_files, indent=2))
else:
    print(f"Directory not found: {docs_path.absolute()}")
