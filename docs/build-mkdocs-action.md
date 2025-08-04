# MkDocs Build Action

A composite GitHub Action for building MkDocs documentation with Material theme support.

## 🚀 Usage

### Basic Usage

```yaml
name: Build Documentation

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        
      - name: Build MkDocs
        uses: WCRP-CMIP/CMIP-LD/actions/build-mkdocs@main
        with:
          config_file: '.src/mkdocs/mkdocs.yml'
          build_dir: '.src/mkdocs/site'
```

### Full Example with Deployment

```yaml
name: Build and Deploy Documentation

on:
  workflow_dispatch:
  push:
    branches: [ main, production ]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  # Build documentation
  build-docs:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          ref: 'production'

      - name: Build MkDocs
        uses: WCRP-CMIP/CMIP-LD/actions/build-mkdocs@main
        with:
          build_dir: '.src/mkdocs/site'
          config_file: '.src/mkdocs/mkdocs.yml'
          python_version: '3.11'

  # Deploy to GitHub Pages
  deploy:
    needs: build-docs
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download build
        uses: actions/download-artifact@v4
        with:
          name: mkdocs-build
          path: site

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload artifact
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
| `checkout_ref` | Git ref to checkout | No | `""` (default branch) |

## 📤 Outputs

| Output | Description |
|--------|-------------|
| `build_path` | Path to the built documentation |
| `artifact_name` | Name of the uploaded artifact (`mkdocs-build`) |

## 🔧 Features

- **Smart dependency detection**: Automatically finds and installs from requirements.txt
- **Pre-build script execution**: Runs Python scripts from `scripts/` directories
- **Build verification**: Validates successful build completion  
- **Artifact upload**: Makes build available for other jobs
- **Comprehensive logging**: Detailed build summaries and error reporting
- **Flexible configuration**: Supports multiple MkDocs project structures

## 📁 Project Structure Support

The action automatically detects and supports these structures:

```
# Option 1: Copier template structure
.src/mkdocs/
├── mkdocs.yml
├── requirements.txt
└── scripts/

# Option 2: Standard MkDocs
├── mkdocs.yml
├── requirements.txt
├── docs/
└── scripts/

# Option 3: Docs subfolder
docs/
├── mkdocs.yml
└── requirements.txt
```

## 🐍 Python Dependencies

The action will install dependencies in this order:
1. `.src/mkdocs/requirements.txt` (if exists)
2. `requirements.txt` (if exists)  
3. `docs/requirements.txt` (if exists)
4. Default packages: `mkdocs`, `mkdocs-material`, `mkdocs-plotly-plugin`, etc.

## 🔧 Pre-build Scripts

Any Python scripts in these directories will be executed before building:
- `.src/mkdocs/scripts/`
- `scripts/`
- `docs/scripts/`

Scripts that fail will log a warning but won't stop the build process.

## 📊 Build Verification

The action performs these checks:
- ✅ Config file exists and has valid YAML syntax
- ✅ Build directory is created
- ✅ `index.html` file exists in output
- ✅ File count and size reporting

## 🏷️ Version Pinning

For production use, pin to a specific version:

```yaml
uses: WCRP-CMIP/CMIP-LD/actions/build-mkdocs@v1.0.0
```

## 🤝 Contributing

This action is maintained in the [CMIP-LD repository](https://github.com/WCRP-CMIP/CMIP-LD).
