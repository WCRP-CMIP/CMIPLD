# MkDocs Scripts Documentation

## Overview

This template includes two separate scripts that work together:

1. **Navigation Generation** (`hooks/generate_nav.py`) - Creates SUMMARY.md with all files
2. **Source Data Processing** (`scripts/process_src_data.py`) - Processes src-data folder

## How It Works

### 1. Navigation Hook (runs first)
- Executes before MkDocs build via the hooks system
- Scans all markdown files in docs directory
- Generates SUMMARY.md with proper sorting and titles
- Includes src-data documentation if it exists

### 2. Source Data Processor (runs during build)
- Executes via gen-files plugin during build
- Looks for `src-data` folder in project root
- For each subfolder:
  - Extracts README.md → `src-data-docs/{folder_name}.md`
  - Creates contents page → `src-data-docs/{folder_name}_contents.md`
  - Reads any `*context*` file and displays it
  - Creates table of all files with links

## Directory Structure

```
project/
├── docs/
│   ├── 80-fdsoj.md
│   ├── 99-acknowlegements.md
│   ├── SUMMARY.md (generated)
│   └── src-data-docs/ (generated)
│       ├── index.md
│       ├── folder1.md
│       ├── folder1_contents.md
│       └── ...
├── src-data/ (optional)
│   ├── folder1/
│   │   ├── README.md
│   │   ├── context.txt
│   │   └── data.json
│   └── folder2/
│       └── ...
└── mkdocs.yml
```

## Configuration

In `mkdocs.yml`:

```yaml
plugins:
  - search
  - gen-files:
      scripts:
        - scripts/process_src_data.py
  - literate-nav:
      nav_file: SUMMARY.md

hooks:
  - hooks/generate_nav.py
```

## Features

### Navigation Generation
- Sorts files by numeric prefix (files without numbers = 0)
- Removes numeric prefixes from display titles
- Handles subdirectories
- Includes src-data documentation automatically

### Source Data Processing
- Only runs if `src-data` folder exists
- Creates overview page with all sections
- For each subfolder:
  - Main page from README.md
  - Contents page with:
    - Context file content (if exists)
    - Table of all files
    - File sizes
    - Direct links to original files

## File Links

In the contents pages, files are linked as:
- JSON files: `[View](../../src-data/folder/file.json)`
- Other files: `[View](../../src-data/folder/file.ext)`

This creates relative links back to the original source files.

## Example Output

For a src-data structure:
```
src-data/
├── models/
│   ├── README.md
│   ├── context.yaml
│   └── model1.json
└── configs/
    ├── README.md
    └── config.json
```

Generated documentation:
```
src-data-docs/
├── index.md          # Overview of all sections
├── models.md         # Content from models/README.md
├── models_contents.md # Table of files + context
├── configs.md        # Content from configs/README.md
└── configs_contents.md # Table of files
```

## Troubleshooting

If files don't appear in navigation:
1. Check that SUMMARY.md was created in docs/
2. Verify hooks are configured in mkdocs.yml
3. Look for error messages during build

If src-data isn't processed:
1. Ensure src-data folder exists at project root
2. Check for subfolders (not just files)
3. Look for processing messages in build output
