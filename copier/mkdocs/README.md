# MkDocs Copier Template with Custom Links

This Copier template generates MkDocs documentation with support for custom navigation links through a configurable links file.

## Features

- **Custom Links Support**: Add external links and custom menu items via a configurable links file
- **Flexible Format**: Supports both YAML and JSON format for links
- **Categorized Links**: Organize links into categories for better navigation structure
- **Backward Compatibility**: Maintains support for legacy `external-links.json` format
- **Auto-generated Navigation**: Automatically scans and organizes your documentation structure

## Usage

### 1. Generate Documentation Site

```bash
copier copy /path/to/copier/mkdocs /path/to/destination
```

During setup, you'll be asked to configure:
- **Project name**: Your project's display name
- **Repository name**: GitHub repository name
- **GitHub username**: Your GitHub username or organization
- **Header color**: Material theme color for the site
- **Links file**: Name of the file containing custom links (default: `links.yml`)
- **Enable custom links**: Whether to include custom links in navigation
- **Links section title**: Title for the links section (default: "External Links")

### 2. Configure Custom Links

Create or edit your links file (e.g., `docs/links.yml`) with the following format:

```yaml
links:
  # Root-level links (appear directly under the section)
  - title: "CMIP Website"
    url: "https://www.wcrp-climate.org/wgcm-cmip"
    description: "Official CMIP website"
    
  # Categorized links (grouped under subsections)
  - title: "ES-DOC Documentation"
    url: "https://es-doc.org"
    category: "Documentation"
    description: "Earth System Documentation project"
    
  - title: "CF Conventions"
    url: "http://cfconventions.org"
    category: "Standards"
    description: "Climate and Forecast metadata conventions"
```

### 3. Link Format Options

**Required fields:**
- `title`: Display name for the link
- `url` or `link`: Target URL

**Optional fields:**
- `category`: Groups links under subsections
- `description`: Adds a comment to the navigation entry

**Supported formats:**
- YAML (recommended): `links.yml`
- JSON: `links.json`

## Navigation Structure

The generated navigation follows this hierarchy:

1. **Home** (if `index.md` exists)
2. **Documentation files** (sorted by filename)
3. **Directory sections** (containing organized content)
4. **Repository Contents** (auto-generated from source data)
5. **Summary of Data** (auto-generated data summaries)
6. **Custom Links Section** (from your links file)

## File Structure

```
your-project/
├── docs/
│   ├── index.md
│   ├── links.yml          # Your custom links configuration
│   ├── auxiliary/
│   └── [other docs]
├── mkdocs.yml             # Generated MkDocs configuration
└── hooks/                 # Navigation generation scripts
```

## Configuration Variables

When running the Copier template, you can configure:

| Variable | Default | Description |
|----------|---------|-------------|
| `links_file` | `"links.yml"` | Path to links file (relative to docs directory) |
| `enable_custom_links` | `true` | Enable/disable custom links functionality |
| `links_section_title` | `"External Links"` | Title for the links section in navigation |

## Advanced Features

### Multiple Link Files
You can use different link files for different purposes by running the template with different `links_file` values.

### Dynamic Links with Jinja
Since the links file supports Jinja templating, you can use template variables:

```yaml
links:
  - title: "GitHub Repository"
    url: "https://github.com/{{ github_username }}/{{ repo_name }}"
```

### Conditional Links
You can conditionally include links based on project configuration by using Jinja conditionals in the links file.

## Migration from Legacy Format

If you have an existing `external-links.json` file, it will continue to work alongside the new links file. The template supports both formats simultaneously for backward compatibility.

## Troubleshooting

- **Links not appearing**: Check that the links file exists in the docs directory and has valid YAML/JSON syntax
- **Navigation issues**: Verify the `enable_custom_links` setting is `true`
- **Template errors**: Ensure Jinja variables in links file match your Copier configuration

## Example Links File

```yaml
links:
  # Quick access links
  - title: "Project Dashboard"
    url: "https://dashboard.example.com"
    
  - title: "Issue Tracker"
    url: "https://github.com/owner/repo/issues"
  
  # Organized by category
  - title: "API Documentation"
    url: "https://api-docs.example.com"
    category: "Development"
    
  - title: "User Guide"
    url: "https://user-guide.example.com"
    category: "Documentation"
    
  - title: "Community Forum"
    url: "https://forum.example.com"
    category: "Community"
```

This will generate a navigation structure like:

```
- External Links:
  - Project Dashboard
  - Issue Tracker
  - Development:
    - API Documentation
  - Documentation:
    - User Guide
  - Community:
    - Community Forum
```
