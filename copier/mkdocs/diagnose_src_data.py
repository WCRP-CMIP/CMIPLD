#!/usr/bin/env python3
"""
Complete diagnostic to check src-data processing and navigation
"""

import os
import sys
from pathlib import Path

print("\n" + "="*60)
print("SRC-DATA DIAGNOSTIC")
print("="*60)

# 1. Check current directory structure
print("\n1. CHECKING DIRECTORY STRUCTURE:")
print(f"   Current directory: {os.getcwd()}")

# Check for src-data in various locations
locations = [
    (".", Path(".")),
    ("parent", Path("..")),
    ("grandparent", Path("../..")),
]

src_data_found = False
src_data_path = None

for name, base in locations:
    path = base / "src-data"
    print(f"   Checking {name}/src-data: ", end="")
    if path.exists() and path.is_dir():
        print(f"✅ FOUND at {path.absolute()}")
        src_data_found = True
        src_data_path = path
        # List subdirectories
        subdirs = [d.name for d in path.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if subdirs:
            print(f"      Subdirectories: {subdirs}")
        else:
            print("      ⚠️  No subdirectories found!")
        break
    else:
        print("❌ not found")

if not src_data_found:
    print("\n❌ ERROR: No src-data directory found!")
    print("   Create a src-data directory with subdirectories containing files")
    sys.exit(1)

# 2. Check for generated files after build
print("\n2. CHECKING FOR GENERATED FILES:")
build_dirs = [
    Path("build"),
    Path("site"),
    Path("_build"),
    Path("public")
]

for build_dir in build_dirs:
    if build_dir.exists():
        print(f"   Found build directory: {build_dir}")
        src_data_docs = build_dir / "src-data-docs"
        if src_data_docs.exists():
            print(f"   ✅ Found generated src-data-docs in {build_dir}")
            files = list(src_data_docs.rglob("*.html"))
            print(f"      Generated files: {len(files)}")
            for f in files[:5]:
                print(f"      - {f.relative_to(build_dir)}")
        else:
            print(f"   ❌ No src-data-docs in {build_dir}")

# 3. Check docs directory
print("\n3. CHECKING DOCS DIRECTORY:")
docs_dirs = [
    Path("docs"),
    Path("../../docs"),
    Path("../docs")
]

for docs_dir in docs_dirs:
    if docs_dir.exists():
        print(f"   Found docs at: {docs_dir.absolute()}")
        summary = docs_dir / "SUMMARY.md"
        if summary.exists():
            print("   ✅ SUMMARY.md exists")
            with open(summary, 'r') as f:
                content = f.read()
                if 'Source Data' in content or 'src-data' in content:
                    print("   ✅ SUMMARY.md contains src-data references")
                else:
                    print("   ⚠️  SUMMARY.md does NOT contain src-data references")
        else:
            print("   ❌ No SUMMARY.md found")
        break

# 4. Test instructions
print("\n4. MANUAL TEST STEPS:")
print("   1. Run: mkdocs build --verbose")
print("   2. Look for output containing:")
print("      - 'Processing src-data folder'")
print("      - 'Processing subfolder:'")
print("      - 'Post-generation hook: Creating navigation'")
print("   3. Check build/src-data-docs/ for generated HTML files")
print("   4. Run: mkdocs serve")
print("   5. Check if 'Source Data' appears in navigation")

print("\n" + "="*60)
