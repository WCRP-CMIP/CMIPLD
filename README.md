# CMIP-LD

**CMIP Linked Data Utilities Library**

<img style='width:400px;' src="https://wcrp-cmip.github.io/CMIP-LD/img/logo.jpg" alt="CMIP-LD Logo"/>

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

---

## Overview

CMIP-LD is a Python library for working with **CMIP (Coupled Model Intercomparison Project) Linked Data** vocabularies. It provides tools to fetch, resolve, validate, and generate documentation for JSON-LD controlled vocabularies used across CMIP and related climate science projects.

### Key Features

- 🔗 **Prefix Resolution** - Resolve short prefixes (e.g., `universal:frequency`) to full URLs
- 📥 **Data Fetching** - Retrieve and expand JSON-LD documents with automatic dereferencing
- 📝 **Documentation Generation** - Auto-generate README files for vocabulary directories
- ✅ **Validation** - Validate JSON files against schemas and contexts
- 🔄 **CI/CD Actions** - GitHub Actions for automated vocabulary processing

### Supported Vocabularies

| Prefix | Repository | Description |
|--------|------------|-------------|
| `universal` | [WCRP-universe](https://github.com/wcrp-cmip/WCRP-universe) | Universal controlled vocabularies |
| `cmip7` | [CMIP7-CVs](https://github.com/wcrp-cmip/CMIP7-CVs) | CMIP7 controlled vocabularies |
| `cmip6plus` | [CMIP6Plus_CVs](https://github.com/wcrp-cmip/CMIP6Plus_CVs) | CMIP6Plus controlled vocabularies |
| `cf` | [CF](https://github.com/wcrp-cmip/CF) | CF Conventions vocabularies |
| `vr` | [Variable-Registry](https://github.com/wcrp-cmip/Variable-Registry) | Variable registry |
| `emd` | [Essential-Model-Documentation](https://github.com/wcrp-cmip/Essential-Model-Documentation) | Essential model documentation |

---

## Installation

### Using pip (editable mode for development)

```bash
git clone https://github.com/wcrp-cmip/CMIP-LD.git
cd CMIP-LD
pip install -e .
```

### Dependencies

- Python 3.8+
- `jsonld-recursive` - JSON-LD processing
- `requests` - HTTP requests
- Optional: `esgvoc` - For Pydantic model integration

---

## Quick Start

### Fetching Data

```python
import cmipld

# Fetch and resolve a vocabulary term
data = cmipld.get("universal:frequency/mon")
print(data)

# Expand a JSON-LD document
expanded = cmipld.expand("universal:frequency")
```

### Resolving Prefixes

```python
import cmipld

# Get the full URL for a prefix
url = cmipld.mapping['universal']
# → 'https://wcrp-cmip.github.io/WCRP-universe/'

# Resolve a prefixed URI
full_url = cmipld.resolve_prefix("universal:frequency/mon")
```

### Using with esgvoc

```python
from esgvoc.api import search

# Search for terms
results = search.find("frequency", term="mon")
print(results)
```

---

## Repository Structure

```
CMIP-LD/
├── cmipld/                    # Main Python package
│   ├── __init__.py            # Package initialization & client setup
│   ├── locations.py           # Prefix mappings and URL resolution
│   ├── prefix_mappings.json   # Prefix → repository mappings
│   ├── generate/              # Documentation generation tools
│   │   ├── create_readme.py   # Generate READMEs for vocab directories
│   │   ├── generate_summary.py
│   │   └── validate_json.py
│   └── utils/                 # Utility functions
│       ├── git/               # Git integration
│       ├── extract/           # Data extraction tools
│       └── ...
├── actions/                   # GitHub Actions for CI/CD
├── static/                    # Static assets (viewer, images)
├── notebooks/                 # Example Jupyter notebooks
└── scripts/                   # Standalone utility scripts
```

---

## Documentation Generation

### Generate READMEs for Vocabulary Directories

The `create_readme.py` script generates standardized documentation for vocabulary directories containing JSON-LD files:

```bash
python -m cmipld.generate.create_readme /path/to/src-data/universe
```

**Features:**
- Only processes directories with a `_context` file
- Extracts schema from Pydantic models (via esgvoc) or JSON keys
- Generates usage examples for cmipld, esgvoc, and direct HTTP
- Creates collapsible file listings
- Analyzes external dependencies

### Collect READMEs for MkDocs

```bash
python scripts/collect_vocab_docs.py /path/to/src-data --output docs/vocabularies
```

This collects all vocabulary READMEs into a single folder for rendering with MkDocs.

---

## GitHub Actions

CMIP-LD provides reusable GitHub Actions for vocabulary repositories:

| Action | Description |
|--------|-------------|
| `actions/process_jsonld` | Process and validate JSON-LD files |
| `actions/build-mkdocs` | Build MkDocs documentation |
| `actions/check-graph` | Validate graph structure |
| `actions/commit-all` | Commit changes with attribution |

---

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

---

## Related Projects

- **[esgvoc](https://github.com/ESGF/esgf-vocab)** - ESGF Vocabulary API with Pydantic models
- **[jsonld-recursive](https://github.com/wolfiex/jsonld-recursive)** - JSON-LD recursive resolution
- **[WCRP-universe](https://github.com/wcrp-cmip/WCRP-universe)** - Universal vocabularies

---

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

---

*Developed by [WCRP-CMIP](https://wcrp-cmip.org) for the climate science community.*
