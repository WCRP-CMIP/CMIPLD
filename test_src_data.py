#!/usr/bin/env python3
"""Quick test to check src-data processing"""
import os
from pathlib import Path

print("=== SRC-DATA CHECK ===\n")

# Check various locations
locations = [
    Path("src-data"),
    Path("../src-data"),
    Path("../../src-data"),
    Path("/Users/daniel.ellis/WIPwork/CMIP-LD/src-data"),
]

for loc in locations:
    print(f"Checking {loc}:")
    if loc.exists():
        print(f"  ✅ EXISTS at {loc.absolute()}")
        subdirs = [d for d in loc.iterdir() if d.is_dir() and not d.name.startswith('.')]
        if subdirs:
            print(f"  📁 Subdirectories: {[d.name for d in subdirs]}")
        else:
            print("  ⚠️  NO SUBDIRECTORIES FOUND - this is the problem!")
            files = [f for f in loc.iterdir() if f.is_file()]
            print(f"  📄 Files in root: {[f.name for f in files[:5]]}")
    else:
        print(f"  ❌ Not found")

print("\n💡 Remember: src-data must contain SUBDIRECTORIES, not just files!")
