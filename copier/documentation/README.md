# CMIP-LD MkDocs Simple Template

A lightweight [Copier](https://copier.readthedocs.io/) template for creating MkDocs documentation sites with the Material theme.

## Features

- 📚 **MkDocs Material** theme with light/dark mode
- 🔗 **Custom Links** - Add external links to sidebar via `links.yml`
- 🐍 **Script Support** - Run Python scripts during build
- 🎨 **Theme Colors** - Choose from Material Design color palette

## Quick Start

```bash
# Apply template to your project
copier copy /path/to/copier/documentation /path/to/your-repo
```

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `project_name` | Display name for the project | "CMIP-LD Documentation" |
| `repo_name` | GitHub repository name | (derived from project_name) |
| `repo_owner` | GitHub username/organization | "WCRP-CMIP" |
| `url_prefix` | GitHub Pages URL prefix | Same as repo_name |
| `description` | Short project description | Auto-generated |
| `author_name` | Author or organization | "CMIP-IPO" |
| `header_color` | Material theme color | "blue" |
| `enable_custom_links` | Enable links.yml sidebar | true |
| `links_section_title` | Title for links section | "External Links" |
| `enable_scripts` | Run docs/scripts/*.py | true |

## Directory Structure

After applying the template:

```
your-repo/
├── .copier-answers.yml      # Saved configuration
├── .src/
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
  # Simple link
  - title: "CMIP Website"
    url: "https://wcrp-cmip.org/"
    icon: "🌐"
  
  # Categorized link
  - title: "GitHub Issues"
    url: "https://github.com/org/repo/issues"
    icon: "🐛"
    category: "Development"
```

## Python Scripts

Add Python scripts to `docs/scripts/` to run during build:

```python
# docs/scripts/generate_data.py
import mkdocs_gen_files

with mkdocs_gen_files.open("generated/data.md", "w") as f:
    f.write("# Generated Content\n")
    f.write("This was created at build time!")
```

## Building Documentation

```bash
cd .src/mkdocs

# Install dependencies
pip install -r requirements.txt

# Development server
mkdocs serve

# Build static site
mkdocs build
```

## Demo Configuration

See `demo-answers.yml` for a complete example configuration.
