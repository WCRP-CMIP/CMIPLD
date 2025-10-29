#!/usr/bin/env python3
"""
Core JSON-LD Validator

This module contains the main JSONValidator class responsible for validating
and fixing JSON-LD files according to CMIP-LD standards.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

from ..git import git_repo_metadata
from ..logging.unique import UniqueLogger, logging
from .context_manager import ContextManager
from .git_integration import GitCoauthorManager
from .reporting import ValidationReporter

log = UniqueLogger()
log.logger.setLevel(logging.WARNING)

# Default required keys for CMIP-LD compliance
DEFAULT_REQUIRED_KEYS = [
    '@id',
    'validation-key', 
    'ui-label',
    'description',
    '@context',
    '@type'
]

# Default values for missing keys
DEFAULT_VALUES = {
    '@id': '',
    'validation-key': '',
    'ui-label': '',
    '@context': '_context',
    '@type': [],
    'description': ''
}


class JSONValidator:
    """
    Main JSON-LD validator for CMIP-LD compliance.
    
    Validates and fixes JSON-LD files to ensure they meet CMIP-LD standards,
    with optional context-aware validation and git integration.
    """
    
    def __init__(self, directory: str, context_file: Optional[str] = None,
                 max_workers: int = 4, dry_run: bool = False, 
                 add_coauthors: bool = False, use_last_author: bool = False,
                 auto_commit: bool = False, custom_required_keys: Optional[List[str]] = None):
        """
        Initialize the JSON validator.
        
        Args:
            directory: Directory containing JSON files to validate
            context_file: Optional JSON-LD context file for context-aware validation
            max_workers: Number of parallel workers for processing
            dry_run: If True, show changes without modifying files
            add_coauthors: Include historic authors as co-authors when modifying files
            use_last_author: Use the author of the last commit instead of current user
            auto_commit: Automatically create commits after modifications
            custom_required_keys: Custom list of required keys (overrides defaults)
        """
        self.directory = Path(directory)
        self.max_workers = max_workers
        self.dry_run = dry_run
        self.required_keys = custom_required_keys or DEFAULT_REQUIRED_KEYS.copy()
        
        # Initialize sub-components
        self.context_manager = ContextManager(context_file) if context_file else None
        self.git_manager = GitCoauthorManager(
            self.directory, add_coauthors, use_last_author, auto_commit
        ) if (add_coauthors or use_last_author or auto_commit) else None
        self.reporter = ValidationReporter()
        
        # Get full repository info
        self.repo_info = git_repo_metadata.get_repository_info()
        # Returns: {'owner': 'WCRP-CMIP', 'repo': 'CMIP-LD', 'prefix': 'WCRP-CMIP/CMIP-LD'}
        log.info(f"Repository info: {self.repo_info}")
        
        # # Just the owner
        # owner = repo_info['owner']  # 'WCRP-CMIP'
        # # Just the repo name
        # repo = repo_info['repo']  # 'CMIP-LD'
        # # Full prefix
        # prefix = repo_info['prefix'] 
        
        
        # Threading and state management
        self.stats = {
            'processed': 0,
            'modified': 0,
            'errors': 0,
            'skipped': 0
        }
        self.stats_lock = Lock()
        self.modified_files = []
        self.modified_files_lock = Lock()
        
        # Update required keys from context if available
        if self.context_manager:
            context_required = self.context_manager.get_required_keys()
            if context_required:
                self.required_keys = list(set(self.required_keys + context_required))
                log.info(f"Updated required keys from context: {context_required}")

    def find_json_files(self) -> List[Path]:
        """Find all JSON files in the directory tree."""
        json_files = []
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(Path(root) / file)
        return json_files

    def validate_and_fix_json(self, file_path: Path) -> Tuple[bool, str]:
        """
        Validate and fix a single JSON file.
        
        Args:
            file_path: Path to the JSON file to validate
            
        Returns:
            Tuple of (was_modified, status_message)
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content:
                return False, "Empty file"

            try:
                data = json.loads(content, object_pairs_hook=OrderedDict)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {e}"

            if not isinstance(data, dict):
                return False, "JSON root is not an object"

            modified = False
            current_filename = file_path.stem.lower().replace('_', '-')
            
            # Handle file renaming
            modified = self._handle_file_rename(file_path, current_filename) or modified
            
            # Basic validation and fixing
            modified = self._validate_required_keys(data) or modified
            modified = self._validate_id_field(data, current_filename) or modified
            modified = self._validate_type_field(data, file_path) or modified
            
            # Context-aware validation if enabled
            if self.context_manager:
                modified = self._validate_with_context(data, file_path) or modified
            
            # Key ordering
            sorted_data = self._sort_json_keys(data)
            if list(data.keys()) != list(sorted_data.keys()):
                modified = True
                data = sorted_data
            else:
                data = sorted_data

            # Write changes if modified and not in dry-run mode
            if modified and not self.dry_run:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                    f.write('\n')
                with self.modified_files_lock:
                    self.modified_files.append(file_path)

            return modified, "Fixed" if modified else "Already valid"

        except Exception as e:
            log.debug(f"Error processing {file_path}: {e}")
            return False, f"Error: {str(e)}"

    def _handle_file_rename(self, file_path: Path, expected_filename: str) -> bool:
        """Handle file renaming if needed."""
        if expected_filename != file_path.stem:
            new_file_path = file_path.parent / (expected_filename + file_path.suffix)
            
            if new_file_path.exists():
                raise FileExistsError(f"Target file already exists: {new_file_path}")
            
            if not self.dry_run:
                file_path.rename(new_file_path)
                log.info(f"Renamed file: {file_path.name} -> {new_file_path.name}")
            
            return True
        return False

    def _validate_required_keys(self, data: Dict[str, Any]) -> bool:
        """Validate and add missing required keys."""
        modified = False
        
        # Check if validation-key is missing but id exists
        
        if '@id' not in data and 'id' in data:
            data['@id'] = data['id']
            del data['id']
            modified = True
            log.warning(f"Missing @id: using id '{data['@id']}' as @id")

        if 'validation-key' not in data and '@id' in data:
            data['validation-key'] = data['@id']
            modified = True
            log.warning(f"Missing validation-key: using @id '{data['@id']}' as validation-key")
        
        for key in self.required_keys:
            if key not in data:
                data[key] = DEFAULT_VALUES.get(key, '')
                modified = True
                    
        return modified

    def _validate_id_field(self, data: Dict[str, Any], expected_id: str) -> bool:
        """Validate and fix the ID field."""
        if data.get('@id') != expected_id:
            data['@id'] = expected_id
            return True
        return False

    def _validate_type_field(self, data: Dict[str, Any], file_path: Path) -> bool:
        """Validate and fix the type field based on parent folder."""
        parent_folder = file_path.parent.name
        modified_internal = False
        
        if parent_folder and parent_folder != '.':
            
            if '@type' not in data and 'type' in data:
                data['@type'] = data['type']
                del data['type']
                modified_internal = True
                log.warning(f"Missing @type: using type '{data['@type']}' as @type")
            
            esgvoc = ''.join(word.capitalize() for word in parent_folder.split('_'))
            if '-' in parent_folder:
                log.warning(f"Parent folder '{parent_folder}' contains hyphen '-', "
                            f"consider using underscores '_' for ESGVoc compliance.")
                
            prefix = self.repo_info['prefix'] or 'undefined'
            expected_type_part = [f"wcrp:{parent_folder}", f"esgvoc:{esgvoc}", prefix]

            
            current_type = data.get('@type', [])
            
            if not isinstance(current_type, list):
                current_type = [current_type] if current_type else []
                
            # current_type = [t for t in current_type if not t.startswith(('wcrp:', 'esgvoc:', f"{prefix}:"))]
            
            for i in current_type:
                if i.startswith(('wcrp:', 'esgvoc:', f"{prefix}:")) and i not in expected_type_part:
                    current_type.remove(i)
                    modified_internal = True
                
            
            for part in expected_type_part:
                if part not in current_type:
                    current_type.append(expected_type_part)
                    data['type'] = current_type
                    modified_internal = True

        return modified_internal

    def _validate_with_context(self, data: Dict[str, Any], file_path: Path) -> bool:
        """Perform context-aware validation if context manager is available."""
        if not self.context_manager:
            return False
            
        modified = False
        try:
            # Validate against context definitions
            context_errors = self.context_manager.validate_against_context(data)
            if context_errors:
                log.debug(f"Context validation errors in {file_path}: {context_errors}")
            
            # Apply context-based fixes
            modified = self.context_manager.apply_context_fixes(data) or modified
            
            # Normalize linked field values (NEW!)
            # modified = self.context_manager.normalize_link_values(data) or modified
            
            return modified
        except Exception as e:
            log.warning(f"Context validation failed for {file_path}: {e}")
            return False

    def _sort_json_keys(self, data: Dict[str, Any]) -> OrderedDict:
        """Sort JSON keys according to CMIP-LD standards (original order)."""
        if self.context_manager:
            return self.context_manager.sort_keys_by_context(data)
        
        # Original CMIP-LD key ordering logic
        sorted_data = OrderedDict()
        priority_keys = ['validation-key', 'ui-label', 'description']
        
        # Add priority keys first
        for key in priority_keys:
            if key in data:
                sorted_data[key] = data[key]

        # Add remaining keys alphabetically (excluding @context and type)
        remaining_keys = sorted([
            k for k in data.keys()
            if k not in priority_keys and k not in ['@id','@context', '@type']
        ])
        for key in remaining_keys:
            sorted_data[key] = data[key]

        # Add @context and type at the end (original order)
        if '@id' in data:
            sorted_data['@id'] = data['@id']
        if '@context' in data:
            sorted_data['@context'] = data['@context']
        if '@type' in data:
            sorted_data['@type'] = data['@type']
        

        return sorted_data

    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single file and return results."""
        try:
            modified, message = self.validate_and_fix_json(file_path)

            with self.stats_lock:
                self.stats['processed'] += 1
                if modified:
                    self.stats['modified'] += 1

            return {
                'file': str(file_path.relative_to(self.directory)),
                'modified': modified,
                'message': message,
                'success': True
            }

        except Exception as e:
            with self.stats_lock:
                self.stats['errors'] += 1

            return {
                'file': str(file_path.relative_to(self.directory)),
                'modified': False,
                'message': f"Error: {str(e)}",
                'success': False
            }

    def run(self) -> bool:
        """
        Run the validation process on all JSON files.
        
        Returns:
            True if no errors occurred, False otherwise
        """
        log.info(f"Scanning directory: {self.directory}")
        json_files = self.find_json_files()

        if not json_files:
            log.warn("No JSON files found")
            return True

        log.info(f"Found {len(json_files)} JSON files")

        if self.dry_run:
            log.info("🔍 DRY RUN MODE - No files will be modified")
            
        if self.context_manager:
            log.info(f"📋 Context-aware validation enabled: {self.context_manager.context_file}")

        results = []

        if HAS_TQDM:
            progress = tqdm(total=len(json_files), desc="Processing JSON files", unit="file")
        else:
            progress = None
            log.debug(f"Processing {len(json_files)} files...")

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_file = {
                executor.submit(self.process_file, file_path): file_path
                for file_path in json_files
            }

            for future in as_completed(future_to_file):
                result = future.result()
                
                if result['modified'] or not result['success']:
                    results.append(result)

                if progress:
                    progress.update(1)
                    progress.set_postfix({
                        'Modified': self.stats['modified'],
                        'Errors': self.stats['errors']
                    })
                else:
                    processed = self.stats['processed']
                    if processed % 10 == 0 or processed == len(json_files):
                        log.debug(f"Processed: {processed}/{len(json_files)} "
                                  f"(Modified: {self.stats['modified']}, Errors: {self.stats['errors']})")

        if progress:
            progress.close()

        # Generate report
        self.reporter.report_results(results, self.stats, self.dry_run)
        
        # Handle git operations
        if self.git_manager and self.modified_files and not self.dry_run:
            self.git_manager.handle_commits(self.modified_files)
        
        return self.stats['errors'] == 0
