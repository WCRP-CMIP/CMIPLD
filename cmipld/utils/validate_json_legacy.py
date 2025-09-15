#!/usr/bin/env python3
"""
Backward compatibility wrapper for validate_json module.

This file maintains compatibility with existing imports while redirecting
to the new modular structure.
"""

import warnings

# Import all the main components from the new module structure
from .validate_json import (
    JSONValidator,
    ContextManager, 
    GitCoauthorManager,
    ValidationReporter,
    main
)

# Import the original classes and functions for backward compatibility
from .validate_json.validator import (
    DEFAULT_REQUIRED_KEYS,
    DEFAULT_VALUES
)

# Re-export everything that was available in the original module
__all__ = [
    'JSONValidator',
    'ContextManager',
    'GitCoauthorManager', 
    'ValidationReporter',
    'DEFAULT_REQUIRED_KEYS',
    'DEFAULT_VALUES',
    'main'
]

# Issue deprecation warning for direct imports
warnings.warn(
    "Direct import from cmipld.utils.validate_json_legacy is deprecated. "
    "Use 'from cmipld.utils.validate_json import JSONValidator' instead.",
    DeprecationWarning,
    stacklevel=2
)

if __name__ == "__main__":
    main()
