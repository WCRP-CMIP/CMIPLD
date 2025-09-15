#!/usr/bin/env python3
"""
Main entry point for the validate_json module.

This allows the module to be executed directly with:
    python -m cmipld.utils.validate_json
"""

from .cli import main

if __name__ == "__main__":
    exit(main())
