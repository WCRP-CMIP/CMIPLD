# JSON-LD Validation Module

## Quick Start

### Installation

```bash
# Install the package (if not already installed)
pip install -e /path/to/CMIP-LD
```

### Basic Usage

```bash
# Validate all JSON files in a directory
validate_json /path/to/json/files

# See what would change without modifying files
validate_json /path/to/json/files --dry-run
```

## Command-Line Arguments

### Required Arguments

| Argument | Description |
|----------|-------------|
| `directory` | Directory containing JSON files to validate |

### Core Options

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--dry-run` | `-n` | Show changes without modifying files | `False` |
| `--context` | `-c` | Path to JSON-LD context file for context-aware validation | None |
| `--workers` | `-w` | Number of parallel workers | `4` |

### Logging Options

| Argument | Short | Description |
|----------|-------|-------------|
| `--verbose` | `-v` | Enable verbose logging (DEBUG level) |
| `--quiet` | `-q` | Suppress non-essential output (ERROR level only) |

### Git Integration Options

| Argument | Short | Description |
|----------|-------|-------------|
| `--add-coauthors` | `-a` | Add historic file authors as co-authors when modifying files |
| `--use-last-author` | `-l` | Use the author of the last commit instead of current user |
| `--auto-commit` | `-m` | Automatically create commits after modifications (implies `--add-coauthors`) |

### Reporting Options

| Argument | Short | Description |
|----------|-------|-------------|
| `--report` | `-r` | Generate JSON report and save to specified file |

### Advanced Options

| Argument | Description |
|----------|-------------|
| `--required-keys` | Custom list of required keys (overrides defaults) |
| `--config` | Path to configuration file (JSON format) |

## Use Case Examples

### 1. Basic Validation and Fixing

**Scenario:** Check and fix all JSON files in a directory

```bash
validate_json ./data/experiments
```

**What it does:**
- Validates all `.json` files recursively
- Checks for required keys (`@id`, `validation_key`, `ui-label`, `description`, `@context`, `@type`)
- Adds missing keys with default values
- Ensures `@id` matches filename
- Validates `@type` includes parent folder prefix (e.g., `wcrp:experiment`)
- Reorders keys according to CMIP-LD standards
- Modifies files in-place

### 2. Preview Changes (Dry Run)

**Scenario:** See what would change before making modifications

```bash
validate_json ./data/experiments --dry-run
```

**What it does:**
- Performs all validation checks
- Shows which files would be modified
- **Does NOT** modify any files
- Useful for reviewing changes before committing

### 3. Context-Aware Validation

**Scenario:** Validate against a specific JSON-LD context schema

```bash
validate_json ./data/experiments --context _context.json
```

**What it does:**
- Loads context definitions from `_context.json`
- Validates required properties defined in context
- Checks type constraints (`@type: "@id"`, `xsd:string`, etc.)
- Validates IRI formats for `@id` typed properties
- Applies context-based key ordering
- More comprehensive validation than basic mode

### 4. Parallel Processing for Large Datasets

**Scenario:** Speed up validation for directories with many files

```bash
validate_json ./data --workers 8
```

**What it does:**
- Processes 8 files simultaneously
- Faster processing for large datasets
- Default is 4 workers (adjust based on CPU cores)

### 5. Git Integration with Co-Authors

**Scenario:** Track all contributors when fixing files

```bash
validate_json ./data/experiments --add-coauthors
```

**What it does:**
- Validates and fixes files
- Extracts all past contributors from git history
- Adds co-author lines to commit messages
- You must manually commit the changes

### 6. Full Automation with Auto-Commit

**Scenario:** Automatically commit each fixed file with proper attribution

```bash
validate_json ./data/experiments --auto-commit
```

**What it does:**
- Validates and fixes files
- Creates individual commits for each modified file
- Automatically includes co-authors (implies `--add-coauthors`)
- Generates descriptive commit messages
- Example commit message:
  ```
  fix: validate and update experiments/historical.json
  
  - Added missing required keys
  - Fixed ID consistency
  - Corrected type prefixes
  - Reordered keys for consistency
  
  Co-authored-by: John Doe <john@example.com>
  Co-authored-by: Jane Smith <jane@example.com>
  ```

### 7. Use Last Author Instead of Current User

**Scenario:** Maintain original authorship attribution

```bash
validate_json ./data/experiments --use-last-author --auto-commit
```

**What it does:**
- Uses the author from the file's last commit
- Preserves original authorship
- Useful when doing automated cleanup
- Combines well with `--auto-commit`

### 8. Generate Detailed Report

**Scenario:** Document validation results for review or audit

```bash
validate_json ./data/experiments --report validation_report.json
```

**What it does:**
- Performs validation
- Generates comprehensive JSON report including:
  - Files processed, modified, errors
  - Processing time and configuration
  - Context information (if used)
  - Git information (if available)
- Saves to `validation_report.json`

### 9. Quiet Mode for Scripts

**Scenario:** Run in CI/CD or automated scripts

```bash
validate_json ./data/experiments --quiet
```

**What it does:**
- Suppresses all non-essential output
- Only shows errors
- Exit code 0 = success, non-zero = failure
- Ideal for automated workflows

### 10. Verbose Debugging

**Scenario:** Troubleshoot validation issues

```bash
validate_json ./data/experiments --verbose
```

**What it does:**
- Shows detailed debug information
- Logs every validation check
- Displays processing details
- Helpful for understanding why files are being modified

### 11. Custom Required Keys

**Scenario:** Enforce project-specific requirements

```bash
validate_json ./data/experiments --required-keys @id validation_key ui-label custom-field
```

**What it does:**
- Overrides default required keys
- Validates presence of specified keys only
- Adds missing keys with empty defaults

### 12. Complete Workflow Example

**Scenario:** Full validation workflow with all features

```bash
# Step 1: Preview changes
validate_json ./data/experiments --dry-run --context _context.json --verbose

# Step 2: Apply changes and generate report
validate_json ./data/experiments --context _context.json --report report.json

# Step 3: Review changes, then commit with co-authors
git diff
validate_json ./data/experiments --auto-commit --add-coauthors
```

### 13. Configuration File Approach

**Scenario:** Standardize validation across team

Create `validation_config.json`:
```json
{
  "context": "_context.json",
  "workers": 8,
  "add_coauthors": true,
  "required_keys": ["@id", "validation_key", "ui-label", "description"]
}
```

Run with config:
```bash
validate_json ./data/experiments --config validation_config.json
```

**What it does:**
- Loads settings from configuration file
- Command-line arguments override config file
- Ensures consistent validation across team

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
    +-- Check for required keys: @id, validation_key, ui-label, 
    |   description, @context, @type
    +-- Add missing keys with default values
    +-- Special case: use '@id' value for missing 'validation_key'
```

**ID Field Validation**
```python
_validate_id_field(data, expected_id)
    |
    +-- Compare data['@id'] to expected ID (based on filename)
    +-- Update ID if mismatch
```

**Type Field Validation**
```python
_validate_type_field(data, file_path)
    |
    +-- Extract parent folder name
    +-- Expected types: "wcrp:{parent_folder}", "esgvoc:{ParentFolder}", "{prefix}:{filename}"
    +-- Ensure @type field is a list
    +-- Add missing type prefixes if needed
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
            |
            +-- Add missing required properties
            +-- Fix property types where possible
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
            +-- Priority keys: validation_key, ui-label, description
            +-- Remaining keys alphabetically
            +-- JSON-LD keys at end: @id, @context, @type
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
- `@id` - Must match filename (lowercase, hyphenated)
- `validation_key` - Must exist (defaults to `@id` value)
- `ui-label` - User-facing label
- `description` - Description text
- `@context` - JSON-LD context reference
- `@type` - Array containing type information

#### Default Values
- `@id`: empty string
- `validation_key`: empty string (or copied from `@id`)
- `ui-label`: empty string
- `@context`: `_context`
- `@type`: empty array
- `description`: empty string

#### Type Field Rules
- Must be an array (converted if not)
- Should contain:
  - `wcrp:{parent_folder}` - WCRP vocabulary term
  - `esgvoc:{ParentFolder}` - ESG vocabulary term (PascalCase)
  - `{prefix}:{filename}` - Repository-specific term
- Example: file `historical.json` in `experiment/` gets:
  - `"wcrp:experiment"`
  - `"esgvoc:Experiment"`
  - `"WCRP-CMIP/CMIP-LD:historical"`

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

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success - all files validated successfully |
| `1` | Failure - validation errors occurred or invalid arguments |

## Troubleshooting

### Common Issues

**Issue:** "Directory not found"
```bash
# Solution: Check directory path
ls -la /path/to/json/files
validate_json /path/to/json/files
```

**Issue:** "Cannot use --auto-commit with --dry-run"
```bash
# Solution: Remove one of the flags
validate_json ./data --dry-run  # Preview only
# OR
validate_json ./data --auto-commit  # Apply changes
```

**Issue:** Files modified but not committed
```bash
# Solution: Check if --auto-commit was used
validate_json ./data --auto-commit  # Creates commits
# OR manually commit
git add .
git commit -m "fix: validate JSON files"
```

**Issue:** "Context file not found"
```bash
# Solution: Verify context file path
ls -la _context.json
validate_json ./data --context ./_context.json
```

## Best Practices

1. **Always run dry-run first** - Preview changes before applying
2. **Use context files** - Enable stricter validation with `--context`
3. **Enable co-authors** - Give credit with `--add-coauthors`
4. **Generate reports** - Document validation for audit trails
5. **Adjust workers** - Optimize for your CPU: `--workers 8`
6. **Version control** - Commit before running bulk validations

## Known Issues

### Missing Methods

The following methods are referenced but may need full implementation:

1. **`normalize_link_values(data)`** - Called in validator.py for normalizing linked field values
2. **Repository info extraction** - Depends on git remote configuration

These features work but may need enhancements for edge cases.
