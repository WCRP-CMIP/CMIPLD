#!/usr/bin/env python3
"""
JSON File Validator and Fixer for CMIP-LD

This script validates and fixes JSON files in a directory structure, ensuring
they have required keys, proper ordering, matching IDs, and correct type prefixes.

Required keys:
- id (must match filename without .json extension)
- type (list - gets wcrp:parentfolder appended if not present)
- validation-key
- ui-label
- description
- @context

Key ordering:
1. id
2. validation-key
3. ui-label
4. description
5. All other keys (alphabetically)
6. @context
7. type

Additional fixes:
- Ensures id and filename match (renames file to match ID if they differ)
- Ensures type is a list and contains wcrp:parentfolder (appends if missing)
- Converts string type values to lists
- Creates missing required keys with appropriate defaults
- Sorts all keys according to specification
"""

import json
import os
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import time

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("Warning: tqdm not available. Install with 'pip install tqdm' for progress bars.")

from ..utils.logging.unique import UniqueLogger

log = UniqueLogger()

# Required keys in order
REQUIRED_KEYS = [
    'id',
    'validation-key', 
    'ui-label',
    'description',
    '@context',
    'type'
]

# Default values for missing keys
DEFAULT_VALUES = {
    'id': '',
    'validation-key': '',
    'ui-label': '',
    '@context': '_context_',
    'type': [],
    'description': ''
}


class JSONValidator:
    """Validates and fixes JSON files according to CMIP-LD standards"""
    
    def __init__(self, directory: str, max_workers: int = 4, dry_run: bool = False):
        self.directory = Path(directory)
        self.max_workers = max_workers
        self.dry_run = dry_run
        self.stats = {
            'processed': 0,
            'modified': 0,
            'errors': 0,
            'skipped': 0
        }
        self.stats_lock = Lock()
        
    def find_json_files(self) -> List[Path]:
        """Find all JSON files in the directory recursively"""
        json_files = []
        
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(Path(root) / file)
        
        return json_files
    
    def validate_and_fix_json(self, file_path: Path) -> Tuple[bool, str]:
        """
        Validate and fix a single JSON file
        
        Returns:
            (modified: bool, message: str)
        """
        try:
            # Read the JSON file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                return False, "Empty file"
            
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {e}"
            
            if not isinstance(data, dict):
                return False, "JSON root is not an object"
            
            # Check if modifications are needed
            modified = False
            original_data = data.copy()
            current_filename = file_path.stem
            
            # Add missing required keys
            for key in REQUIRED_KEYS:
                if key not in data:
                    data[key] = DEFAULT_VALUES[key]
                    modified = True
            
            # Determine the correct ID (prefer existing ID if valid, otherwise use filename)
            existing_id = data.get('id', '')
            if existing_id and existing_id != current_filename:
                # ID exists but doesn't match filename - use ID as source of truth
                correct_id = existing_id
                needs_file_rename = True
            else:
                # Use filename as ID
                correct_id = current_filename
                needs_file_rename = False
            
            # Set the correct ID
            if data.get('id') != correct_id:
                data['id'] = correct_id
                modified = True
            
            # Fix type to include parent folder with wcrp: prefix
            parent_folder = file_path.parent.name
            if parent_folder and parent_folder != '.':
                expected_type_part = f"wcrp:{parent_folder}"
                current_type = data.get('type', [])
                
                # Ensure type is a list
                if not isinstance(current_type, list):
                    # Convert string to list
                    if current_type:
                        current_type = [current_type]
                    else:
                        current_type = []
                    data['type'] = current_type
                    modified = True
                
                # Check if wcrp:parentfolder is present in the type list
                if expected_type_part not in current_type:
                    current_type.append(expected_type_part)
                    modified = True
            
            # Sort keys according to specification
            sorted_data = self.sort_json_keys(data)
            
            # Check if key order changed
            if list(data.keys()) != list(sorted_data.keys()):
                modified = True
                data = sorted_data
            
            # Determine final file path
            final_file_path = file_path
            if needs_file_rename and not self.dry_run:
                # Rename file to match ID
                new_filename = f"{correct_id}.json"
                new_file_path = file_path.parent / new_filename
                
                # Check if target file already exists
                if new_file_path.exists() and new_file_path != file_path:
                    return False, f"Cannot rename to {new_filename} - file already exists"
                
                try:
                    file_path.rename(new_file_path)
                    final_file_path = new_file_path
                    modified = True
                except OSError as e:
                    return False, f"Failed to rename file: {e}"
            
            # Write back if modified and not dry run
            if modified and not self.dry_run:
                with open(final_file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                    f.write('\n')  # Add trailing newline
            
            # Generate status message
            message_parts = []
            if modified:
                message_parts.append("Fixed")
            if needs_file_rename:
                if self.dry_run:
                    message_parts.append(f"Would rename to {correct_id}.json")
                else:
                    message_parts.append(f"Renamed to {correct_id}.json")
            
            status_message = " | ".join(message_parts) if message_parts else "OK"
            
            return modified, status_message
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def sort_json_keys(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sort JSON keys according to CMIP-LD specification"""
        sorted_data = {}
        
        # First, add priority keys in order (excluding @context and type)
        priority_keys = ['id', 'validation-key', 'ui-label', 'description']
        for key in priority_keys:
            if key in data:
                sorted_data[key] = data[key]
        
        # Then add remaining keys alphabetically (excluding @context and type)
        remaining_keys = sorted([
            k for k in data.keys() 
            if k not in priority_keys and k not in ['@context', 'type']
        ])
        for key in remaining_keys:
            sorted_data[key] = data[key]
        
        # Finally add @context and type at the end
        if '@context' in data:
            sorted_data['@context'] = data['@context']
        if 'type' in data:
            sorted_data['type'] = data['type']
        
        return sorted_data
    
    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single file and return results"""
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
        """Run the validation process"""
        log.info(f"Scanning directory: {self.directory}")
        
        # Find all JSON files
        json_files = self.find_json_files()
        
        if not json_files:
            log.warn("No JSON files found")
            return True
        
        log.info(f"Found {len(json_files)} JSON files")
        
        if self.dry_run:
            log.info("🔍 DRY RUN MODE - No files will be modified")
        
        # Process files in parallel
        results = []
        
        if HAS_TQDM:
            progress = tqdm(total=len(json_files), desc="Processing JSON files", unit="file")
        else:
            progress = None
            print(f"Processing {len(json_files)} files...")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_file = {
                executor.submit(self.process_file, file_path): file_path
                for file_path in json_files
            }
            
            # Collect results
            for future in as_completed(future_to_file):
                result = future.result()
                results.append(result)
                
                if progress:
                    progress.update(1)
                    # Update description with current stats
                    progress.set_postfix({
                        'Modified': self.stats['modified'],
                        'Errors': self.stats['errors']
                    })
                else:
                    # Simple progress without tqdm
                    processed = self.stats['processed']
                    if processed % 10 == 0 or processed == len(json_files):
                        print(f"Processed: {processed}/{len(json_files)} "
                              f"(Modified: {self.stats['modified']}, Errors: {self.stats['errors']})")
        
        if progress:
            progress.close()
        
        # Report results
        self.report_results(results)
        
        return self.stats['errors'] == 0
    
    def report_results(self, results: List[Dict[str, Any]]):
        """Report processing results"""
        print("\n" + "="*60)
        print("📊 PROCESSING SUMMARY")
        print("="*60)
        
        print(f"Total files processed: {self.stats['processed']}")
        print(f"Files modified: {self.stats['modified']}")
        print(f"Errors encountered: {self.stats['errors']}")
        
        if self.dry_run and self.stats['modified'] > 0:
            print(f"\n💡 DRY RUN: {self.stats['modified']} files would be modified in actual run")
        
        # Show errors if any
        errors = [r for r in results if not r['success']]
        if errors:
            print(f"\n❌ ERRORS ({len(errors)} files):")
            for error in errors[:10]:  # Show first 10 errors
                print(f"   {error['file']}: {error['message']}")
            if len(errors) > 10:
                print(f"   ... and {len(errors) - 10} more errors")
        
        # Show modifications if requested
        modifications = [r for r in results if r['modified']]
        if modifications and len(modifications) <= 20:
            print(f"\n✅ MODIFIED FILES ({len(modifications)}):")
            for mod in modifications:
                print(f"   {mod['file']}")
        elif modifications:
            print(f"\n✅ MODIFIED: {len(modifications)} files (too many to list)")
        
        print("="*60)


def main():
    """Main command line interface"""
    parser = argparse.ArgumentParser(
        description="Validate and fix JSON files for CMIP-LD compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate and fix JSON files in current directory
  python -m cmipld.generate.validate_json .

  # Dry run to see what would be changed
  python -m cmipld.generate.validate_json /path/to/json/files --dry-run

  # Use more parallel workers
  python -m cmipld.generate.validate_json /path/to/json/files --workers 8

  # Verbose output
  python -m cmipld.generate.validate_json /path/to/json/files --verbose
        """
    )
    
    parser.add_argument(
        'directory',
        help='Directory containing JSON files to validate'
    )
    
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Show what would be changed without modifying files'
    )
    
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=4,
        help='Number of parallel workers (default: 4)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Validate directory
    if not os.path.exists(args.directory):
        print(f"❌ Error: Directory '{args.directory}' does not exist")
        return 1
    
    if not os.path.isdir(args.directory):
        print(f"❌ Error: '{args.directory}' is not a directory")
        return 1
    
    # Configure logging
    if args.verbose:
        log.debug("Verbose logging enabled")
    
    # Create validator and run
    validator = JSONValidator(
        directory=args.directory,
        max_workers=args.workers,
        dry_run=args.dry_run
    )
    
    try:
        success = validator.run()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
