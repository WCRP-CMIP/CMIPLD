#!/usr/bin/env python3
"""
Pre-build hook: clean the build output directory before each build.

Prevents stale files from previous builds (e.g. renamed or deleted pages)
from accumulating and causing duplicate navigation entries.
"""

import shutil
from pathlib import Path


def on_pre_build(config, **kwargs):
    """Remove the site_dir before mkdocs populates it."""
    site_dir = Path(config['site_dir'])

    if site_dir.exists():
        count = sum(1 for _ in site_dir.rglob('*') if _.is_file())
        shutil.rmtree(site_dir)
        print(f"[clean_build] Removed {site_dir} ({count} files)")

    site_dir.mkdir(parents=True, exist_ok=True)
