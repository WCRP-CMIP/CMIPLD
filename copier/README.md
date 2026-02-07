# CMIPLD Copier Templates

This folder contains copier templates for CMIP-LD projects.

## Available Templates

| Template | Description |
|----------|-------------|
| `documentation` | MkDocs documentation site with shadcn theme |

## Quick Start (Recommended)

Install `cmipld` and use the CLI:

```bash
pip install cmipld

# Install documentation template (auto-detects repo info)
cmipcopier documentation

# Update existing project
cmipcopier documentation update

# List available templates
cmipcopier list
```

## Manual Installation

If you prefer not to install cmipld:

```bash
rm -rf /tmp/cmipld-template && \
git clone --depth=1 https://github.com/WCRP-CMIP/CMIPLD.git /tmp/cmipld-template && \
if command -v gh &>/dev/null && gh repo view &>/dev/null 2>&1; then \
  REPO_OWNER=$(gh repo view --json owner -q .owner.login); \
  REPO_NAME=$(gh repo view --json name -q .name); \
  REPO_DESC=$(gh repo view --json description -q .description); \
elif git remote get-url origin &>/dev/null 2>&1; then \
  REPO_URL=$(git remote get-url origin); \
  REPO_OWNER=$(echo "$REPO_URL" | sed -n 's/.*github\.com[:/]\([^/]*\)\/.*/\1/p'); \
  REPO_NAME=$(basename -s .git "$REPO_URL"); \
  REPO_DESC=""; \
else \
  REPO_OWNER="WCRP-CMIP"; \
  REPO_NAME=$(basename "$PWD"); \
  REPO_DESC=""; \
fi && \
copier copy /tmp/cmipld-template/copier/documentation . \
  --data repo_owner="$REPO_OWNER" \
  --data repo_name="$REPO_NAME" \
  ${REPO_DESC:+--data "description=$REPO_DESC"}
```

### Manual Update

```bash
rm -rf /tmp/cmipld-template && \
git clone --depth=1 https://github.com/WCRP-CMIP/CMIPLD.git /tmp/cmipld-template && \
copier update -a .copier-answers.yml /tmp/cmipld-template/copier/documentation .
```

## Requirements

- [copier](https://copier.readthedocs.io/) >= 9.0.0: `pip install copier`
- Git
- (Optional) [GitHub CLI](https://cli.github.com/) for better auto-detection

## What Gets Auto-Detected

| Field | gh CLI | git fallback | No repo |
|-------|--------|--------------|---------|
| `repo_owner` | ✓ | ✓ (from URL) | WCRP-CMIP |
| `repo_name` | ✓ | ✓ (from URL) | folder name |
| `description` | ✓ | ✗ | ✗ |
| `project_name` | interactive | interactive | interactive |

## Included Scripts

The documentation template includes scripts in `docs/scripts/` that run during build:

| Script | Description |
|--------|-------------|
| `generate_contributors.py` | Creates contributors.md with GitHub avatars and ORCID links |
| `example_generator.py` | Example script template |

## Additional CLI Commands

Once `cmipld` is installed, you also get:

```bash
# Generate contributors page manually
get_contributors --md docs/contributors.md

# Validate JSON-LD files
validate_json path/to/file.json

# Update README files
update_readme
```
