# JSON-LD Validation Module

## Overview

This module provides comprehensive validation and fixing capabilities for JSON-LD files in the CMIP-LD ecosystem.

## Information Flow

### Command Execution Flow

```
validate_json (terminal command)
    |
    v
cmipld.utils.validate_json:main (__init__.py)
    |
    v
cli.main() (cli.py)
    |
    +-- create_argument_parser()
    +-- load_configuration() [if --config provided]
    +-- validate_arguments()
    +-- configure_logging()
    +-- print_startup_info()
    |
    v
run_validation(args) (cli.py)
    |
    +-- Creates JSONValidator instance
    |       |
    |       +-- ContextManager [if --context provided]
    |       +-- GitCoauthorManager [if git features enabled]
    |       +-- ValidationReporter
    |
    v
JSONValidator.run() (validator.py)
    |
    +-- find_json_files()
    +-- ThreadPoolExecutor (parallel processing)
    |       |
    |       +-- process_file() for each JSON file
    |               |
    |               v
    |           validate_and_fix_json()
    |
    +-- ValidationReporter.report_results()
    +-- GitCoauthorManager.handle_commits() [if auto-commit enabled]
```

### Data Flow

```
JSON Files (on disk)
    |
    v
JSONValidator.find_json_files()
    |
    v
List[Path] of JSON files
    |
    v
ThreadPoolExecutor (parallel workers)
    |
    +-- Worker 1: process_file(file1.json)
    +-- Worker 2: process_file(file2.json)
    +-- Worker 3: process_file(file3.json)
    +-- Worker N: process_file(fileN.json)
    |
    v
Aggregated results and statistics
    |
    v
ValidationReporter (formatted output)
    |
    v
Console output / JSON report file
```

## File Validation Process

### Core Validation Logic

The actual JSON file checking occurs in `validator.py` through the `validate_and_fix_json()` method:

#### Step 1: File Loading and Parsing
```python
validate_and_fix_json(file_path)
    |
    +-- Open and read file content
    +-- Parse JSON with OrderedDict (preserves key order)
    +-- Validate JSON is a dictionary object
```

#### Step 2: Basic Validation Checks

Each check returns a boolean indicating if the file was modified:

**File Naming Check**
```python
_handle_file_rename(file_path, expected_filename)
    |
    +-- Compare actual filename to expected (lowercase, hyphens)
    +-- Rename file if mismatch found
```

**Required Keys Check**
```python
_validate_required_keys(data)
    |
    +-- Check for required keys: id, validation-key, ui-label, 
    |   description, @context, type
    +-- Add missing keys with default values
    +-- Special case: use 'id' value for missing 'validation-key'
```

**ID Field Validation**
```python
_validate_id_field(data, expected_id)
    |
    +-- Compare data['id'] to expected ID (based on filename)
    +-- Update ID if mismatch
```

**Type Field Validation**
```python
_validate_type_field(data, file_path)
    |
    +-- Extract parent folder name
    +-- Expected type: "wcrp:{parent_folder}"
    +-- Ensure type field is a list
    +-- Add missing type prefix if needed
```

#### Step 3: Context-Aware Validation (Optional)

If `--context` flag is provided:

```python
_validate_with_context(data, file_path)
    |
    +-- ContextManager.validate_against_context(data)
    |       |
    |       +-- Check required properties from context
    |       +-- Validate property types against context definitions
    |       +-- Return list of validation errors
    |
    +-- ContextManager.apply_context_fixes(data)
    |       |
    |       +-- Add missing required properties
    |       +-- Fix property types where possible
    |
    +-- ContextManager.normalize_link_values(data)
            |
            +-- Normalize linked field values (MISSING - NOT IMPLEMENTED)
```

#### Step 4: Key Ordering

```python
_sort_json_keys(data)
    |
    +-- If context available:
    |       |
    |       +-- ContextManager.sort_keys_by_context(data)
    |               |
    |               +-- Priority keys first (from context @priority)
    |               +-- JSON-LD keys (@context, @type, @id)
    |               +-- Remaining keys alphabetically
    |
    +-- If no context:
            |
            +-- Priority keys: id, validation-key, ui-label, description
            +-- Remaining keys alphabetically
            +-- JSON-LD keys at end: @context, type
```

#### Step 5: File Writing

```python
if modified and not dry_run:
    |
    +-- Write JSON with 4-space indentation
    +-- Add trailing newline
    +-- Track file in modified_files list
```

### Validation Rules

#### Default Required Keys
- `id` - Must match filename (lowercase, hyphenated)
- `validation-key` - Must exist (defaults to `id` value)
- `ui-label` - User-facing label
- `description` - Description text
- `@context` - JSON-LD context reference
- `type` - Array containing at least `wcrp:{parent_folder}`

#### Default Values
- `id`: empty string
- `validation-key`: empty string (or copied from `id`)
- `ui-label`: empty string
- `@context`: `_context_`
- `type`: empty array
- `description`: empty string

#### Type Field Rules
- Must be an array (converted if not)
- Must contain `wcrp:{parent_folder}` where parent_folder is the containing directory name
- Example: file in `experiment/` must have `"wcrp:experiment"` in type array

### Context-Aware Validation

When a context file is provided via `--context`:

#### Context Loading
```
ContextManager.load_context(context_file)
    |
    +-- Parse context JSON
    +-- Resolve context definitions
    +-- Extract required keys, priorities, type constraints
```

#### Context Validation Checks
- Required properties (marked with `@required: true`)
- Type constraints (`@type: "@id"`, `xsd:string`, `xsd:integer`, etc.)
- Container types (`@container: "@list"` or `"@set"`)
- IRI validation for `@id` typed properties

#### Auto-Fixes Applied
- Add missing required properties
- Convert types where safe (string to int, etc.)
- Normalize boolean values
- Fix list/array structures

## Module Components

### validator.py
Core validation engine. Contains JSONValidator class with all validation logic.

### cli.py
Command-line interface. Handles argument parsing, configuration loading, and orchestration.

### context_manager.py
JSON-LD context operations. Provides context-aware validation and property resolution.

### git_integration.py
Git operations. Manages co-authors, commits, and repository validation.

### reporting.py
Output formatting. Generates console reports and JSON export files.

### __init__.py
Package interface. Exports main classes and functions.

### __main__.py
Module entry point. Enables `python -m cmipld.utils.validate_json` execution.

## Usage Examples

### Basic Validation
```bash
validate_json /path/to/json/files
```

### Dry Run
```bash
validate_json /path/to/json/files --dry-run
```

### Context-Aware Validation
```bash
validate_json /path/to/json/files --context context.json
```

### With Git Integration
```bash
validate_json /path/to/json/files --add-coauthors --auto-commit
```

### Generate Report
```bash
validate_json /path/to/json/files --report validation_report.json
```

## Known Issues

### Missing Methods

The following methods are called but not implemented in `context_manager.py`:

1. **`normalize_link_values(data)`** - Called in validator.py line ~157
2. **`get_linked_fields()`** - Referenced in reporting but not fully defined

These need to be implemented for full functionality.
