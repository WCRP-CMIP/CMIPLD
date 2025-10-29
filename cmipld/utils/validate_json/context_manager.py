#!/usr/bin/env python3
"""
JSON-LD Context Manager

JSON-LD context loading, resolution, and validation.
"""

import json
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from collections import OrderedDict

from ..logging.unique import UniqueLogger, logging

log = UniqueLogger()


class ContextManager:
    """
    Manages JSON-LD contexts for validation and processing.
    
    Provides context-aware validation, key ordering based on context definitions,
    and automatic fixing of context-related issues.
    """
    
    def __init__(self, context_file: Optional[str] = None):
        """
        Initialize the context manager.
        
        Args:
            context_file: Path to JSON-LD context file or URL
        """
        self.context_file = context_file
        self.context_data = {}
        self.resolved_context = {}
        
        if context_file:
            self.load_context(context_file)

    def load_context(self, context_file: str) -> None:
        """
        Load JSON-LD context from file or URL.
        
        Args:
            context_file: Path to context file or URL
        """
        try:
            if context_file.startswith(('http://', 'https://')):
                # TODO: Implement URL loading with proper caching
                raise NotImplementedError("URL context loading not yet implemented")
            else:
                context_path = Path(context_file)
                if not context_path.exists():
                    raise FileNotFoundError(f"Context file not found: {context_file}")
                
                with open(context_path, 'r', encoding='utf-8') as f:
                    self.context_data = json.load(f)
                    
            self.resolved_context = self._resolve_context(self.context_data)
            log.info(f"Loaded context with {len(self.resolved_context)} definitions")
            
        except Exception as e:
            log.error(f"Failed to load context from {context_file}: {e}")
            raise

    def _resolve_context(self, context: Union[Dict, List, str]) -> Dict[str, Any]:
        """
        Resolve JSON-LD context to a flat dictionary of term definitions.
        
        Args:
            context: Context object to resolve
            
        Returns:
            Dictionary of resolved context terms
        """
        resolved = {}
        
        if isinstance(context, dict):
            if '@context' in context:
                # Context document with @context property
                return self._resolve_context(context['@context'])
            else:
                # Direct context object
                for key, value in context.items():
                    if not key.startswith('@'):
                        resolved[key] = self._resolve_term_definition(value)
        
        elif isinstance(context, list):
            # Array of contexts - merge them
            for ctx in context:
                resolved.update(self._resolve_context(ctx))
        
        elif isinstance(context, str):
            # Context reference - would need to be loaded
            log.warning(f"Context reference not resolved: {context}")
        
        return resolved

    def _resolve_term_definition(self, definition: Any) -> Dict[str, Any]:
        """
        Resolve a term definition to extract metadata.
        
        Args:
            definition: Term definition (string or object)
            
        Returns:
            Resolved term definition with metadata
        """
        if isinstance(definition, str):
            return {
                '@id': definition,
                '@type': None,
                '@required': False,
                '@priority': 0
            }
        
        elif isinstance(definition, dict):
            return {
                '@id': definition.get('@id', ''),
                '@type': definition.get('@type'),
                '@required': definition.get('@required', False),
                '@priority': definition.get('@priority', 0),
                '@container': definition.get('@container'),
                '@language': definition.get('@language'),
                '@context': definition.get('@context'),  # For nested contexts
                **{k: v for k, v in definition.items() if not k.startswith('@')}
            }
        
        else:
            return {
                '@id': str(definition),
                '@type': None,
                '@required': False,
                '@priority': 0
            }

    def get_required_keys(self) -> List[str]:
        """
        Get list of required keys from context definitions.
        
        Returns:
            List of required property names
        """
        return [
            key for key, definition in self.resolved_context.items()
            if definition.get('@required', False)
        ]

    def get_priority_keys(self) -> List[str]:
        """
        Get keys sorted by priority from context definitions.
        
        Returns:
            List of keys sorted by priority (highest first)
        """
        keys_with_priority = [
            (key, definition.get('@priority', 0))
            for key, definition in self.resolved_context.items()
        ]
        
        # Sort by priority (descending), then alphabetically
        keys_with_priority.sort(key=lambda x: (-x[1], x[0]))
        
        return [key for key, priority in keys_with_priority]

    def validate_against_context(self, data: Dict[str, Any]) -> List[str]:
        """
        Validate JSON-LD data against context definitions.
        
        Args:
            data: JSON-LD data to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check required properties
        required_keys = self.get_required_keys()
        for key in required_keys:
            if key not in data:
                errors.append(f"Required property '{key}' missing (defined in context)")
        
        # Validate property types
        for key, value in data.items():
            if key in self.resolved_context:
                definition = self.resolved_context[key]
                type_errors = self._validate_property_type(key, value, definition)
                errors.extend(type_errors)
        
        # Check for undefined properties (if strict mode)
        # TODO: Add strict mode configuration
        
        return errors

    def _validate_property_type(self, key: str, value: Any, definition: Dict[str, Any]) -> List[str]:
        """
        Validate a property's value against its context definition.
        
        Args:
            key: Property name
            value: Property value
            definition: Context definition for the property
            
        Returns:
            List of type validation errors
        """
        errors = []
        expected_type = definition.get('@type')
        
        if not expected_type:
            return errors  # No type constraint
        
        if expected_type == '@id':
            if not isinstance(value, str):
                errors.append(f"Property '{key}' should be a string IRI, got {type(value).__name__}")
            elif not self._is_valid_iri(value):
                errors.append(f"Property '{key}' should be a valid IRI: {value}")
        
        elif expected_type == '@vocab':
            if not isinstance(value, str):
                errors.append(f"Property '{key}' should be a vocabulary term (string), got {type(value).__name__}")
        
        elif expected_type in ('xsd:string', 'http://www.w3.org/2001/XMLSchema#string'):
            if not isinstance(value, str):
                errors.append(f"Property '{key}' should be a string, got {type(value).__name__}")
        
        elif expected_type in ('xsd:integer', 'http://www.w3.org/2001/XMLSchema#integer'):
            if not isinstance(value, int):
                errors.append(f"Property '{key}' should be an integer, got {type(value).__name__}")
        
        elif expected_type in ('xsd:boolean', 'http://www.w3.org/2001/XMLSchema#boolean'):
            if not isinstance(value, bool):
                errors.append(f"Property '{key}' should be a boolean, got {type(value).__name__}")
        
        elif expected_type in ('xsd:dateTime', 'http://www.w3.org/2001/XMLSchema#dateTime'):
            if not isinstance(value, str):
                errors.append(f"Property '{key}' should be a dateTime string, got {type(value).__name__}")
            # TODO: Add datetime format validation
        
        # Handle container types
        container = definition.get('@container')
        if container == '@list' and not isinstance(value, list):
            errors.append(f"Property '{key}' should be a list, got {type(value).__name__}")
        elif container == '@set' and not isinstance(value, list):
            errors.append(f"Property '{key}' should be a set (list), got {type(value).__name__}")
        
        return errors

    def _is_valid_iri(self, value: str) -> bool:
        """Check if a string is a valid IRI."""
        try:
            # Basic IRI validation
            if value.startswith(('http://', 'https://', 'urn:', 'mailto:')):
                return True
            
            # Check for prefixed names (prefix:localname)
            if ':' in value and not value.startswith(':') and not value.endswith(':'):
                return True
            
            # Relative IRIs (basic check)
            parsed = urllib.parse.urlparse(value)
            return bool(parsed.scheme or parsed.path)
        
        except Exception:
            return False

    def apply_context_fixes(self, data: Dict[str, Any]) -> bool:
        """
        Apply automatic fixes based on context definitions.
        
        Args:
            data: JSON-LD data to fix
            
        Returns:
            True if data was modified, False otherwise
        """
        modified = False
        
        # Add missing required properties with default values
        for key in self.get_required_keys():
            if key not in data:
                data[key] = self._get_default_value_for_property(key)
                modified = True
                log.debug(f"Added missing required property: {key}")
        
        # Fix property types where possible
        for key, value in data.items():
            if key in self.resolved_context:
                fixed_value = self._fix_property_type(key, value, self.resolved_context[key])
                if fixed_value != value:
                    data[key] = fixed_value
                    modified = True
                    log.debug(f"Fixed type for property '{key}': {type(value).__name__} -> {type(fixed_value).__name__}")
        
        return modified

    def get_linked_fields_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Get detailed information about linked fields.
        
        Returns:
            Dictionary mapping field names to their link information
        """
        linked_info = {}
        
        for field_name, definition in self.resolved_context.items():
            field_type = definition.get('@type')
            if field_type in ('@id', '@vocab'):
                linked_info[field_name] = {
                    'type': field_type,
                    'container': definition.get('@container'),
                    'id': definition.get('@id'),
                    'required': definition.get('@required', False),
                    'priority': definition.get('@priority', 0)
                }
        
        return linked_info

    def _get_default_value_for_property(self, key: str) -> Any:
        """Get a default value for a missing required property."""
        if key not in self.resolved_context:
            return ""
        
        definition = self.resolved_context[key]
        expected_type = definition.get('@type')
        
        if expected_type == '@id':
            return f"urn:missing:{key}"
        elif expected_type in ('xsd:string', 'http://www.w3.org/2001/XMLSchema#string'):
            return ""
        elif expected_type in ('xsd:integer', 'http://www.w3.org/2001/XMLSchema#integer'):
            return 0
        elif expected_type in ('xsd:boolean', 'http://www.w3.org/2001/XMLSchema#boolean'):
            return False
        elif definition.get('@container') in ('@list', '@set'):
            return []
        else:
            return ""

    def _fix_property_type(self, key: str, value: Any, definition: Dict[str, Any]) -> Any:
        """Attempt to fix a property's type based on context definition."""
        expected_type = definition.get('@type')
        
        if not expected_type:
            return value
        
        try:
            if expected_type == '@id' and not isinstance(value, str):
                return str(value)
            elif expected_type in ('xsd:string', 'http://www.w3.org/2001/XMLSchema#string') and not isinstance(value, str):
                return str(value)
            elif expected_type in ('xsd:integer', 'http://www.w3.org/2001/XMLSchema#integer') and not isinstance(value, int):
                if isinstance(value, str) and value.isdigit():
                    return int(value)
                elif isinstance(value, float):
                    return int(value)
            elif expected_type in ('xsd:boolean', 'http://www.w3.org/2001/XMLSchema#boolean') and not isinstance(value, bool):
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(value, (int, float)):
                    return bool(value)
        except (ValueError, TypeError):
            pass
        
        return value

    def sort_keys_by_context(self, data: Dict[str, Any]) -> OrderedDict:
        """
        Sort dictionary keys based on context priority and definitions.
        
        Args:
            data: Dictionary to sort
            
        Returns:
            OrderedDict with keys sorted by context priority
        """
        # Use existing ldparse sortd function for basic sorting
        try:
            from ..ldparse import sortd
        except ImportError:
            sortd = lambda d: OrderedDict(sorted(d.items()))
        
        # Start with a basic sorted structure
        sorted_data = OrderedDict()
        
        # Get priority keys from context
        priority_keys = self.get_priority_keys()
        
        # Add priority keys first (in priority order)
        for key in priority_keys:
            if key in data:
                sorted_data[key] = data[key]
        
        # Add JSON-LD specific keys
        jsonld_keys = ['@context', '@type', '@id']
        for key in jsonld_keys:
            if key in data and key not in sorted_data:
                sorted_data[key] = data[key]
        
        # Add remaining keys alphabetically using existing sortd function
        remaining_data = {k: v for k, v in data.items() if k not in sorted_data}
        remaining_sorted = sortd(remaining_data)
        
        for key, value in remaining_sorted.items():
            sorted_data[key] = value
        
        return sorted_data

    def get_context_info(self) -> Dict[str, Any]:
        """
        Get information about the loaded context.
        
        Returns:
            Dictionary with context statistics and information
        """
        if not self.resolved_context:
            return {"status": "No context loaded"}
        
        required_count = len(self.get_required_keys())
        priority_count = len([
            k for k, v in self.resolved_context.items()
            if v.get('@priority', 0) > 0
        ])
        
        linked_fields = self.get_linked_fields()
        linked_fields_info = self.get_linked_fields_info()
        
        type_counts = {}
        for definition in self.resolved_context.values():
            type_name = definition.get('@type', 'untyped')
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            "status": "Context loaded",
            "context_file": self.context_file,
            "total_terms": len(self.resolved_context),
            "required_terms": required_count,
            "priority_terms": priority_count,
            "linked_fields_count": len(linked_fields),
            "linked_fields": linked_fields,
            "linked_fields_info": linked_fields_info,
            "type_distribution": type_counts,
            "has_nested_contexts": any(
                v.get('@context') for v in self.resolved_context.values()
            )
        }
