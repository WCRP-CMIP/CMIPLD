#!/usr/bin/env python3
"""
Debug script to test src-data processing directly
"""
import sys
import os
from pathlib import Path

# Add the template scripts directory to Python path
template_dir = Path(__file__).parent / ".src/mkdocs/scripts"
if template_dir.exists():
    sys.path.insert(0, str(template_dir))

# Now we can import and test the processing
try:
    # First, let's check what src-data directories exist
    print("=== Checking for src-data directories ===")
    
    possible_locations = [
        Path.cwd() / "src-data",
        Path.cwd().parent / "src-data",
        Path.cwd().parent.parent / "src-data",
        Path("/Users/daniel.ellis/WIPwork/CMIP-LD/src-data"),
    ]
    
    for loc in possible_locations:
        if loc.exists():
            print(f"✅ Found: {loc}")
            subdirs = [d for d in loc.iterdir() if d.is_dir() and not d.name.startswith('.')]
            if subdirs:
                print(f"   Subdirectories: {[d.name for d in subdirs]}")
            else:
                print("   ⚠️  No subdirectories found!")
        else:
            print(f"❌ Not found: {loc}")
    
    print("\n=== Testing if we can import the processing script ===")
    
    # Try to load the template content
    template_file = Path(__file__).parent / ".src/mkdocs/scripts/process_src_data_fixed.py.jinja"
    if template_file.exists():
        print(f"✅ Template found at: {template_file}")
        
        # Read and execute the template (removing jinja syntax)
        with open(template_file, 'r') as f:
            content = f.read()
            
        # Create a temporary Python file without the .jinja extension
        temp_file = Path(__file__).parent / "temp_process_src_data.py"
        with open(temp_file, 'w') as f:
            f.write(content)
        
        # Import and run
        import importlib.util
        spec = importlib.util.spec_from_file_location("process_module", temp_file)
        process_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(process_module)
        
        print("\n=== Running process_src_data function ===")
        result = process_module.process_src_data()
        print(f"Result: {result}")
        
        # Clean up
        temp_file.unlink()
    else:
        print(f"❌ Template not found at: {template_file}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
