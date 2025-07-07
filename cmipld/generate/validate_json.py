#!/usr/bin/env python3
"""
JSON File Validator and Fixer for CMIP-LD

This script validates and fixes JSON files in a directory structure, ensuring
they have required keys, proper ordering, matching IDs, and correct type prefixes.
"""

import json
import os
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False
    print("Warning: tqdm not available. Install with 'pip install tqdm' for progress bars.")

from ..utils.logging.unique import UniqueLogger, logging

log = UniqueLogger()
log.logger.setLevel(logging.WARNING)  # Only show warnings and above by default

REQUIRED_KEYS = [
    'id',
    'validation-key',
    'ui-label',
    'description',
    '@context',
    'type'
]

DEFAULT_VALUES = {
    'id': '',
    'validation-key': '',
    'ui-label': '',
    '@context': '_context_',
    'type': [],
    'description': ''
}


class JSONValidator:
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
        json_files = []
        for root, _, files in os.walk(self.directory):
            for file in files:
                if file.endswith('.json'):
                    json_files.append(Path(root) / file)
        return json_files

    def validate_and_fix_json(self, file_path: Path) -> Tuple[bool, str]:
        if isinstance(file_path, str):
            file_path = Path(file_path)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            if not content:
                return False, "Empty file"

            try:
                data = json.loads(content, object_pairs_hook=OrderedDict)
            except json.JSONDecodeError as e:
                return False, f"Invalid JSON: {e}"

            if not isinstance(data, dict):
                return False, "JSON root is not an object"

            modified = False
            log.debug(f"=== Processing {file_path.name} ===")
            log.debug(f"  Initial modified flag: {modified}")

            original_data = OrderedDict(data)
            current_filename = file_path.stem

            for key in REQUIRED_KEYS:
                if key not in data:
                    data[key] = DEFAULT_VALUES[key]
                    modified = True
                    log.debug(f"  Added missing key '{key}', modified={modified}")

            existing_id = data.get('id', '')
            if existing_id and existing_id != current_filename:
                correct_id = existing_id
                needs_file_rename = True
            else:
                correct_id = current_filename
                needs_file_rename = False

            if data.get('id') != correct_id:
                data['id'] = correct_id
                modified = True

            parent_folder = file_path.parent.name
            if parent_folder and parent_folder != '.':
                expected_type_part = f"wcrp:{parent_folder}"
                current_type = data.get('type', [])

                if not isinstance(current_type, list):
                    current_type = [current_type] if current_type else []
                    data['type'] = current_type
                    modified = True

                if expected_type_part not in current_type:
                    current_type.append(expected_type_part)
                    modified = True
                    log.debug(f"  Added type '{expected_type_part}', modified={modified}")

            sorted_data = self.sort_json_keys(data)
            what_we_will_write = json.dumps(sorted_data, indent=4, ensure_ascii=False, sort_keys=False) + '\n'

            if content != what_we_will_write:
                log.debug("  Content differs from expected")
                log.debug(f"  Current keys: {list(json.loads(content, object_pairs_hook=OrderedDict).keys())}")
                log.debug(f"  Expected keys: {list(sorted_data.keys())}")
                modified = True
                log.debug(f"  Set modified={modified} due to content mismatch")
            else:
                log.debug("  Content matches expected, no reordering needed")

            log.debug(f"  Final modified flag before write check: {modified}")

            data = sorted_data
            final_file_path = file_path
            if needs_file_rename and not self.dry_run:
                new_filename = f"{correct_id}.json"
                new_file_path = file_path.parent / new_filename

                if new_file_path.exists() and new_file_path != file_path:
                    log.debug(f"  Cannot rename {file_path.name} to {new_filename} - file already exists")
                    return False, f"Cannot rename to {new_filename} - file already exists"

                try:
                    file_path.rename(new_file_path)
                    final_file_path = new_file_path
                    modified = True
                except OSError as e:
                    log.debug(f"  Error renaming file: {e}")
                    return False, f"Failed to rename file: {e}"

            log.debug(f"  Final file path: {final_file_path}")
            log.debug(f"  MODIFIED: {modified}")

            if modified:
                log.debug(f"  File {file_path.name} is marked as modified")
                if self.dry_run:
                    log.debug(f"  DRY RUN: Would write file")
                else:
                    log.debug(f"  Writing file: {final_file_path}")
                    with open(final_file_path, 'w', encoding='utf-8') as f:
                        json.dump(sorted_data, f, indent=4, ensure_ascii=False, sort_keys=False)
                        f.write('\n')
                    log.debug(f"  File written successfully")

            message_parts = []
            if modified:
                message_parts.append("Fixed")
            if needs_file_rename:
                message_parts.append(f"{'Would rename' if self.dry_run else 'Renamed'} to {correct_id}.json")

            return modified, " | ".join(message_parts) if message_parts else "OK"

        except Exception as e:
            log.debug(f"error {e}")
            return False, f"Error: {str(e)}"

    def sort_json_keys(self, data: Dict[str, Any]) -> OrderedDict:
        sorted_data = OrderedDict()
        priority_keys = ['id', 'validation-key', 'ui-label', 'description']
        for key in priority_keys:
            if key in data:
                sorted_data[key] = data[key]

        remaining_keys = sorted([
            k for k in data.keys()
            if k not in priority_keys and k not in ['@context', 'type']
        ])
        for key in remaining_keys:
            sorted_data[key] = data[key]

        if '@context' in data:
            sorted_data['@context'] = data['@context']
        if 'type' in data:
            sorted_data['type'] = data['type']

        return sorted_data

    def process_file(self, file_path: Path) -> Dict[str, Any]:
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
        log.info(f"Scanning directory: {self.directory}")
        json_files = self.find_json_files()

        if not json_files:
            log.warning("No JSON files found")
            return True

        log.info(f"Found {len(json_files)} JSON files")

        if self.dry_run:
            log.info("🔍 DRY RUN MODE - No files will be modified")

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

        self.report_results(results)
        return self.stats['errors'] == 0

    def report_results(self, results: List[Dict[str, Any]]):
        print("\n" + "=" * 60)
        print("📊 PROCESSING SUMMARY")
        print("=" * 60)

        print(f"Total files processed: {self.stats['processed']}")
        print(f"Files modified: {self.stats['modified']}")
        print(f"Errors encountered: {self.stats['errors']}")

        if self.dry_run and self.stats['modified'] > 0:
            print(f"\n💡 DRY RUN: {self.stats['modified']} files would be modified in actual run")

        errors = [r for r in results if not r['success']]
        if errors:
            print(f"\n❌ ERRORS ({len(errors)} files):")
            for error in errors[:10]:
                print(f"   {error['file']}: {error['message']}")
            if len(errors) > 10:
                print(f"   ... and {len(errors) - 10} more errors")

        modifications = [r for r in results if r['modified']]
        if modifications and len(modifications) <= 20:
            print(f"\n✅ MODIFIED FILES ({len(modifications)}):")
            for mod in modifications:
                print(f"   {mod['file']}")
        elif modifications:
            print(f"\n✅ MODIFIED: {len(modifications)} files (too many to list)")

        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Validate and fix JSON files for CMIP-LD compliance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m cmipld.generate.validate_json .
  python -m cmipld.generate.validate_json /path/to/json/files --dry-run
  python -m cmipld.generate.validate_json /path/to/json/files --workers 8
  python -m cmipld.generate.validate_json /path/to/json/files --verbose
        """
    )

    parser.add_argument('directory', help='Directory containing JSON files to validate')
    parser.add_argument('--dry-run', '-n', action='store_true', help='Show changes without modifying files')
    parser.add_argument('--workers', '-w', type=int, default=4, help='Number of parallel workers (default: 4)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')

    args = parser.parse_args()

    if not os.path.exists(args.directory):
        print(f"❌ Error: Directory '{args.directory}' does not exist")
        return 1

    if not os.path.isdir(args.directory):
        print(f"❌ Error: '{args.directory}' is not a directory")
        return 1

    if args.verbose:
        log.logger.setLevel(logging.DEBUG)
        log.debug("Verbose logging enabled")

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
