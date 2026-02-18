# CMIP-LD Reusable GitHub Actions

This directory contains reusable GitHub Actions for CMIP documentation workflows.

## Actions

### build-docs

Builds MkDocs documentation and deploys to production branch.

**Usage:**
```yaml
- uses: WCRP-CMIP/CMIPLD/actions/build-docs@copier
  with:
    production-branch: production  # optional, default: production
    docs-branch: docs             # optional, default: docs
    python-version: '3.11'        # optional, default: 3.11
```

**What it does:**
1. Fetches docs source from docs branch
2. Builds with mkdocs
3. Deploys to production branch docs/ directory
4. Outputs version string (v.yy.mm.dd)

### archive-version

Archives built documentation to versions branch with date-based folder.

**Usage:**
```yaml
- uses: WCRP-CMIP/CMIPLD/actions/archive-version@copier
  with:
    version: v.26.02.18           # required
    artifact-name: docs-build     # optional, default: docs-build
    versions-branch: versions     # optional, default: versions
    repository: ${{ github.repository }}  # required
```

**What it does:**
1. Downloads docs artifact
2. Checks out or creates versions branch
3. Creates version folder (v.26.02.18/)
4. Copies docs into version folder
5. Updates versions README
6. Commits and pushes to versions branch

## Example Workflow

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      version: ${{ steps.build.outputs.version }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: production
          fetch-depth: 0
      
      - name: Build docs
        id: build
        uses: WCRP-CMIP/CMIPLD/actions/build-docs@copier
  
  archive:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: WCRP-CMIP/CMIPLD/actions/archive-version@copier
        with:
          version: ${{ needs.build.outputs.version }}
          repository: ${{ github.repository }}
```

## Branch Structure

**production branch:**
- `docs/` - Latest documentation (deployed to GitHub Pages)

**versions branch:**
- `v.26.02.18/` - February 18, 2026 snapshot
- `v.26.02.17/` - February 17, 2026 snapshot
- `README.md` - List of all versions

## No Mike!

These actions use simple file operations (cp, rsync) instead of mike:
- ✅ Reliable and predictable
- ✅ No complex configuration
- ✅ No build loops
- ✅ Easy to debug
