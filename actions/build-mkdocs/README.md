# Build MkDocs Documentation Action

A composite GitHub Action for building MkDocs documentation with Material theme support.

## 🚀 Usage

### Basic Usage

```yaml
- name: Build MkDocs
  uses: WCRP-CMIP/CMIP-LD/actions/build-mkdocs@main
  with:
    config_file: '.src/mkdocs/mkdocs.yml'
    build_dir: '.src/mkdocs/site'
```

### Complete Workflow Example

```yaml
name: Build and Deploy Documentation

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build MkDocs
        uses: WCRP-CMIP/CMIP-LD/actions/build-mkdocs@main
        with:
          config_file: '.src/mkdocs/mkdocs.yml'
          build_dir: 'site'
          python_version: '3.11'

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload to Pages
        uses: actions/upload-pages-artifact@v3
        with:
          path: 'site'

      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
```

## 📝 Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `build_dir` | Directory to output the build | No | `.src/mkdocs/site` |
| `config_file` | Path to mkdocs.yml config file | No | `.src/mkdocs/mkdocs.yml` |
| `python_version` | Python version to use | No | `3.11` |
| `upload_artifact` | Whether to upload build as artifact | No | `true` |
| `artifact_name` | Name for the uploaded artifact | No | `mkdocs-build` |

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `build_path` | Path to the built documentation |
| `artifact_name` | Name of the uploaded artifact |

## 🔧 Features

- **Smart dependency detection**: Automatically finds and installs from requirements.txt
- **Pre-build script execution**: Runs Python scripts from `scripts/` directories
- **Build verification**: Validates successful build completion  
- **Optional artifact upload**: Control whether to upload build artifacts
- **Comprehensive logging**: Detailed build summaries and error reporting
- **Flexible configuration**: Supports multiple MkDocs project structures

## 📁 Supported Project Structures

```
# Copier template structure (default)
.src/mkdocs/
├── mkdocs.yml
├── requirements.txt
└── scripts/

# Standard MkDocs structure
├── mkdocs.yml
├── requirements.txt
├── docs/
└── scripts/

# Documentation subfolder
docs/
├── mkdocs.yml
└── requirements.txt
```

## 🐍 Dependency Resolution

The action installs dependencies in this priority order:
1. `.src/mkdocs/requirements.txt`
2. `requirements.txt` (root)
3. `docs/requirements.txt`
4. Default packages if none found

**Default packages:**
- `mkdocs`
- `mkdocs-material` 
- `mkdocs-plotly-plugin`
- `mkdocs-gen-files`
- `mkdocs-literate-nav`
- `pymdown-extensions`
- `mkdocs-mermaid2-plugin`

## 🔧 Pre-build Scripts

Python scripts in these directories run before building:
- `.src/mkdocs/scripts/`
- `scripts/`
- `docs/scripts/`

Failed scripts log warnings but don't stop the build.

## 📊 Build Validation

The action verifies:
- ✅ Config file exists with valid YAML
- ✅ Build directory is created  
- ✅ `index.html` exists in output
- ✅ Provides file count and size metrics

## 🏷️ Version Pinning

For production, pin to a specific version:

```yaml
uses: WCRP-CMIP/CMIP-LD/actions/build-mkdocs@v1.0.0
```

## 🤝 Contributing

Report issues and contribute at [CMIP-LD repository](https://github.com/WCRP-CMIP/CMIP-LD).
