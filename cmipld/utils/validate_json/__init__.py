#!/usr/bin/env python3
"""
JSON-LD Validation Module for CMIP-LD

A comprehensive validation and fixing suite for JSON-LD files with context awareness,
git integration, and performance optimization.

This module provides:
- Core validation and fixing functionality
- JSON-LD context-aware validation
- Git co-author integration
- Multi-threaded processing
- Comprehensive reporting

Example usage:
    # Basic validation
    from cmipld.utils.validate_json import JSONValidator
    validator = JSONValidator('/path/to/json/files')
    validator.run()
    
    # Context-aware validation
    validator = JSONValidator('/path/to/json/files', context_file='context.json')
    validator.run()
    
    # Command-line usage
    python -m cmipld.utils.validate_json /path/to/json/files --context context.json
"""

# Import main classes and functions for easy access
try:
    from .validator import JSONValidator
    from .context_manager import ContextManager
    from .git_integration import GitCoauthorManager
    from .reporting import ValidationReporter
    from .cli import main
except ImportError:
    # Handle import errors gracefully during development
    pass

# Version information
__version__ = "2.0.0"
__author__ = "CMIP-LD Team"

# Export main interface
__all__ = [
    'JSONValidator',
    'ContextManager', 
    'GitCoauthorManager',
    'ValidationReporter',
    'main'
]
