# Build and Deploy Versioned Documentation

A GitHub Action to build MkDocs documentation with mike versioning and deploy to a docs branch.

## How it works

1. **Checkout production branch** - Gets the source documentation
2. **Get version** - From input, `docs/.version` file, or defaults to `v0.1.0`
3. **Build with mike** - Builds docs and manages versions
4. **Save artifact** - Uploads versions folder as artifact
5. **Commit to production** - Updates `.version` file if changed
6. **Push docs branch** - Deploys the versioned documentation

## Usage

```yaml
- name: Build and Deploy Docs
  uses: ./actions/build-docs
  with:
    production_branch: 'production'
    docs_branch: 'docs'
    mkdocs_dir: 'src/mkdocs'
    github_token: ${{ secrets.GITHUB_TOKEN }}
```

## Inputs

| Input | Description | Default |
|-------|-------------|---------|
| `production_branch` | Branch containing source docs | `production` |
| `docs_branch` | Branch to deploy versioned docs to | `docs` |
| `mkdocs_dir` | Directory containing mkdocs.yml | `src/mkdocs` |
| `python_version` | Python version | `3.11` |
| `version` | Version to deploy (reads from `docs/.version` if empty) | `''` |
| `set_latest` | Set this version as latest alias | `true` |
| `github_token` | GitHub token for pushing | required |

## Outputs

| Output | Description |
|--------|-------------|
| `version` | Version that was deployed |
| `deployed` | Whether deployment occurred |

## Version Management

The action reads version from `docs/.version` file. Use the auto-versioning script to bump versions:

```bash
# Auto-bump patch version
python docs/scripts/auto_version.py

# Bump minor version
python docs/scripts/auto_version.py --bump minor

# Bump major version  
python docs/scripts/auto_version.py --bump major
```

## Workflow Example

```yaml
name: Deploy Documentation

on:
  push:
    branches: [production]
    paths:
      - 'docs/**/*.md'
      - 'src/mkdocs/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build and Deploy Docs
        uses: ./actions/build-docs
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```
