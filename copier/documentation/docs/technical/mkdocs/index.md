# MkDocs Build System

This documentation site uses MkDocs with the shadcn theme and a custom build pipeline for generating dynamic pages.

## Overview

The build system has three main stages:

1. **Pre-build Generation** - Python scripts fetch data and generate HTML pages
2. **Navigation Generation** - Automatic navigation built from directory structure
3. **MkDocs Build** - Standard MkDocs compilation and static site generation

## Directory Structure

```
project/
├── docs/                          # Documentation source
│   ├── scripts/                   # Generation scripts
│   │   ├── helpers/               # Shared utilities
│   │   │   ├── __init__.py        # Icons, keywords, utilities
│   │   │   ├── utils.py           # Parsing functions
│   │   │   └── templates/         # Jinja2 templates
│   │   └── generate_*.py          # Generator scripts
│   ├── stylesheets/               # CSS and JS
│   │   ├── custom.css             # Theme customizations
│   │   ├── custom.js              # Custom functionality
│   │   └── embed.js               # Embed mode support
│   └── SUMMARY.md                 # Auto-generated navigation
│
└── src/mkdocs/
    ├── mkdocs.yml                 # MkDocs configuration
    └── hooks/
        ├── run_scripts.py         # Runs generators before build
        └── generate_nav.py        # Creates SUMMARY.md
```

## Build Pipeline

### Stage 1: Generator Scripts

Generator scripts in `docs/scripts/` are executed before MkDocs builds. Each generator:

1. Fetches data from external sources
2. Parses and transforms the data
3. Renders HTML using Jinja2 templates
4. Writes files to the appropriate `docs/` subdirectory

### Stage 2: Navigation Generation

The `generate_nav.py` hook creates `SUMMARY.md` by scanning the docs directory:

- Discovers all `.md` and `.html` files
- Builds hierarchical navigation from folder structure
- Adds custom links from `links.yml`
- Generates proper titles from filenames

### Stage 3: MkDocs Build

Standard MkDocs compilation with shadcn theme features:

- Search indexing
- Collapsible navigation
- Code syntax highlighting
- Dark/light mode support

## Configuration

### mkdocs.yml

Key settings:

```yaml
theme:
  name: shadcn
  palette:
    primary: blue
    accent: cyan

plugins:
  - search
  - gen-files:
      scripts:
        - hooks/run_scripts.py
  - literate-nav:
      nav_file: SUMMARY.md

extra_css:
  - stylesheets/custom.css

extra_javascript:
  - stylesheets/custom.js
  - stylesheets/embed.js
```

## Running Locally

```bash
cd src/mkdocs
pip install -r requirements.txt
mkdocs serve
```

## Troubleshooting

### Pages not appearing in navigation

- Check that files are in `docs/` before `generate_nav.py` runs
- Verify the generator scripts completed successfully
- Check for errors in script output

### Styles not loading

- Ensure CSS imports use correct relative paths
- Check that `custom.css` exists
- Verify browser cache is cleared

### Generator script errors

- Check dependencies are installed
- Verify network access to data sources
- Review script output for error messages
