# CMIP-LD MkDocs Simple Template

A lightweight [Copier](https://copier.readthedocs.io/) template for creating MkDocs documentation sites with the shadcn theme.

## Features

- 📚 **MkDocs shadcn** theme with light/dark mode
- 🔗 **Custom Links** - Add external links to sidebar via `links.yml`
- 🐍 **Script Support** - Run Python scripts during build
- 🎨 **Theme Colors** - Choose from Material Design color palette
- 📌 **Versioning** - Manual version deployment with mike

## Quick Start

```bash
# Install cmipld
pip install cmipld

# Apply template to your project
cmipcopier documentation

# Update existing project
cmipcopier documentation update
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `project_name` | Display name for the project | Folder name |
| `repo_name` | GitHub repository name | Folder name |
| `repo_owner` | GitHub username/organization | "WCRP-CMIP" |
| `url_prefix` | GitHub Pages URL prefix | Same as repo_name |
| `description` | Short project description | Auto-generated |
| `author_name` | Author or organization | "CMIP-IPO" |
| `header_color` | Theme color (teal, blue, etc.) | "blue" |
| `css_prefix` | CSS variable prefix | url_prefix |
| `enable_custom_links` | Enable links.yml sidebar | true |
| `links_section_title` | Title for links section | "External Links" |
| `enable_scripts` | Run docs/scripts/*.py | true |

## Directory Structure

After applying the template:

```
your-repo/
├── .copier-answers.yml      # Saved configuration
├── src/
│   └── mkdocs/
│       ├── mkdocs.yml       # MkDocs configuration
│       ├── requirements.txt # Python dependencies
│       ├── hooks/           # Build hooks
│       └── overrides/       # Theme overrides
└── docs/
    ├── index.md             # Homepage
    ├── links.yml            # Custom sidebar links
    ├── scripts/             # Python scripts (run at build)
    ├── assets/              # Images, logos
    └── stylesheets/         # Custom CSS
```

## Custom Links

Edit `docs/links.yml` to add external links to the sidebar:

```yaml
links:
  - title: "Docs Github"
    url: "https://github.com/your-org/your-repo"

  - title: "CMIP Website"
    url: "https://wcrp-cmip.org/"
    category: "Resources"
```

## Python Scripts

Add Python scripts to `docs/scripts/` to run during build:

```python
# docs/scripts/generate_data.py
import mkdocs_gen_files

with mkdocs_gen_files.open("generated/data.md", "w") as f:
    f.write("# Generated Content\n")
```

## Building Documentation

```bash
cd src/mkdocs

# Install dependencies
pip install -r requirements.txt

# Development server
mkdocs serve

# Build static site
mkdocs build
```

## Versioning with Mike

Mike allows you to deploy multiple versions of your documentation.

### Auto-versioning (recommended)

The template includes auto-versioning that:
- Tracks version in `docs/.version`
- Auto-increments patch version when `.md` files change
- Only deploys on production branches (main/master)

```bash
# Check status
python docs/scripts/auto_version.py --status

# Auto-deploy (bumps patch if .md files changed)
python docs/scripts/auto_version.py

# Force deploy
python docs/scripts/auto_version.py --force

# Bump minor/major version and deploy
python docs/scripts/auto_version.py --bump minor --deploy
python docs/scripts/auto_version.py --bump major --deploy
```

### Auto-deploy on build

Enable auto-versioning during mkdocs build:

```bash
AUTO_VERSION=1 mkdocs build
```

### Manual deployment

```bash
# Deploy specific version
python docs/scripts/deploy_version.py v1.0 --latest --push
```

### Commands

| Command | Description |
|---------|-------------|
| `auto_version.py --status` | Show current version status |
| `auto_version.py` | Auto-deploy if .md files changed |
| `auto_version.py --force` | Force deploy current version |
| `auto_version.py --bump patch` | Bump patch version |
| `auto_version.py --bump minor --deploy` | Bump minor and deploy |
| `auto_version.py --bump major --deploy` | Bump major and deploy |
| `deploy_version.py v1.0 --latest --push` | Manual deploy specific version |
| `deploy_version.py --list` | List all versions |

## Demo Configuration

See `demo-answers.yml` for a complete example configuration.
