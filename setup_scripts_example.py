#!/usr/bin/env python3
"""
Alternative setup.py approach for direct script installation
"""
from setuptools import setup, find_packages
from pathlib import Path

# Get script paths
script_dir = Path("cmipld/scripts")
scripts = []

# Find all shell scripts
for pattern in ["directory-utilities/*", "jsonld-util/*", "development/*"]:
    for script_path in script_dir.glob(pattern):
        if script_path.is_file() and not script_path.name.startswith('.'):
            scripts.append(str(script_path))

setup(
    name="cmipld",
    use_scm_version=True,
    setup_requires=['setuptools_scm'],
    packages=find_packages(),
    scripts=scripts,  # This installs shell scripts directly
    package_data={
        'cmipld': ['scripts/*/*', 'prefix_mappings.json']
    },
    # ... other setup parameters
)
