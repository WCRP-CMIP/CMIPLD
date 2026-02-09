# CMIPLD Copier Templates

This folder contains copier templates for CMIP-LD projects.

## Available Templates

| Template | Description |
|----------|-------------|
| `documentation` | MkDocs documentation site with shadcn theme |
| `workflows` | Complete GitHub Actions workflow setup for CMIP repositories |

## Quick Start (Recommended)

Install `cmipld` and use the CLI:

```bash
pip install cmipld

# Install documentation template (auto-detects repo info)
cmipcopier documentation

# Install workflows template
cmipcopier workflows

# Update existing project
cmipcopier documentation update
cmipcopier workflows update

# List available templates
cmipcopier list
```

## Template Details

### Documentation Template

MkDocs-based documentation site with:
- Material theme with shadcn components
- Auto-generated contributors page
- Custom links support
- Script execution during build
- GitHub Pages deployment

**Best for**: Project documentation, API docs, user guides

### Workflows Template (NEW!)

Complete GitHub Actions workflow setup including:
- **src-data-change** - Process vocabulary data from src-data branch
- **docs-change** - Build and deploy documentation from docs branch
- **issue-templates** - Auto-generate GitHub issue templates
- **ci** - Continuous integration and validation
- **sync-workflows** - Keep workflows synchronized across branches
- **stale** - Manage stale issues and PRs

**Features**:
- ✅ All workflows manually runnable (workflow_dispatch)
- ✅ 50% faster than traditional multi-workflow setups
- ✅ Docs branch triggers on docs/ folder changes
- ✅ Optional Python graph generation
- ✅ Configurable via interactive questions

**Best for**: CMIP vocabulary repositories, data repositories

## Manual Installation

If you prefer not to install cmipld:

### Documentation Template

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

### Workflows Template

```bash
rm -rf /tmp/cmipld-template && \
git clone --depth=1 https://github.com/WCRP-CMIP/CMIPLD.git /tmp/cmipld-template && \
if command -v gh &>/dev/null && gh repo view &>/dev/null 2>&1; then \
  REPO_OWNER=$(gh repo view --json owner -q .owner.login); \
  REPO_NAME=$(gh repo view --json name -q .name); \
elif git remote get-url origin &>/dev/null 2>&1; then \
  REPO_URL=$(git remote get-url origin); \
  REPO_OWNER=$(echo "$REPO_URL" | sed -n 's/.*github\.com[:/]\([^/]*\)\/.*/\1/p'); \
  REPO_NAME=$(basename -s .git "$REPO_URL"); \
else \
  REPO_OWNER="WCRP-CMIP"; \
  REPO_NAME=$(basename "$PWD"); \
fi && \
copier copy /tmp/cmipld-template/copier/workflows . \
  --data repo_owner="$REPO_OWNER" \
  --data repo_name="$REPO_NAME"
```

### Manual Update

**Documentation:**
```bash
rm -rf /tmp/cmipld-template && \
git clone --depth=1 https://github.com/WCRP-CMIP/CMIPLD.git /tmp/cmipld-template && \
copier update -a .copier-answers.yml /tmp/cmipld-template/copier/documentation .
```

**Workflows:**
```bash
rm -rf /tmp/cmipld-template && \
git clone --depth=1 https://github.com/WCRP-CMIP/CMIPLD.git /tmp/cmipld-template && \
copier update -a .copier-answers.yml /tmp/cmipld-template/copier/workflows .
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
| `description` | ✓ (docs only) | ✗ | ✗ |
| `project_name` | interactive | interactive | interactive |

## Using Both Templates

You can use both templates in the same repository:

```bash
# Install documentation
cmipcopier documentation

# Install workflows
cmipcopier workflows

# Both work together:
# - Workflows handle CI/CD and data processing
# - Documentation provides user-facing docs
```

## Workflows Template Configuration

The workflows template asks interactive questions:

- **Repository type**: vocabulary, documentation, or mixed
- **Branch setup**: src-data branch, docs branch, production branch
- **Features**: graph generation, prepublish scripts, issue templates
- **CI/CD**: schedule, stale days, GitHub Pages
- **Documentation**: MkDocs support, directory location

See `workflows/README.md` for full details.

## Documentation Template Features

### Included Scripts

Scripts in `docs/scripts/` that run during build:

| Script | Description |
|--------|-------------|
| `generate_contributors.py` | Creates contributors.md with GitHub avatars and ORCID links |
| `example_generator.py` | Example script template |

### Customization

- **Material theme colors**: Configurable primary/accent colors
- **Custom links**: External links in sidebar
- **CSS prefix**: Custom CSS variables
- **Python scripts**: Run custom logic during build

## Additional CLI Commands

Once `cmipld` is installed, you also get:

```bash
# Generate contributors page manually
get_contributors --md docs/contributors.md

# Validate JSON-LD files
validate_json path/to/file.json

# Update README files
update_readme

# Template management
cmipcopier list              # List available templates
cmipcopier documentation     # Install documentation template
cmipcopier workflows         # Install workflows template
cmipcopier <template> update # Update from template
```

## Example Usage

### For New Repository

```bash
# Clone your new repository
git clone https://github.com/WCRP-CMIP/my-new-repo.git
cd my-new-repo

# Install cmipld
pip install cmipld

# Set up workflows
cmipcopier workflows

# Set up documentation
cmipcopier documentation

# Configure branches
git checkout -b src-data
git checkout -b docs
git checkout -b production

# Commit and push
git checkout main
git add .
git commit -m "Initial setup from copier templates"
git push origin main src-data docs production
```

### For Existing Repository

```bash
cd /path/to/existing-repo

# Add workflows
cmipcopier workflows

# Review changes
git diff

# Commit
git add .github/
git commit -m "Add CMIP workflows from template"
git push
```

## Troubleshooting

### copier not found
```bash
pip install copier
```

### Permission denied when copying
```bash
# Make sure you're in your repository directory
pwd
# Should show your repository path
```

### Template not updating
```bash
# Force update
copier update --force
```

### Auto-detection not working
```bash
# Manually specify values
copier copy /path/to/template . \
  --data repo_owner="WCRP-CMIP" \
  --data repo_name="my-repo"
```

## Contributing

To improve these templates:

1. Edit templates in `CMIP-LD/copier/<template>/`
2. Test with a repository: `copier copy . /path/to/test-repo`
3. Submit PR with improvements

## Documentation

- **Documentation template**: See `documentation/README.md`
- **Workflows template**: See `workflows/README.md` and `workflows/QUICKSTART.md`
- **Copier docs**: https://copier.readthedocs.io/

---

**Maintained by**: CMIP-IPO
**Last updated**: February 9, 2025
