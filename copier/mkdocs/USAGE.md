# MkDocs Copier Template Usage Guide

## Quick Start

1. **Generate your documentation site:**
   ```bash
   copier copy ./copier/mkdocs /path/to/your/project
   ```

2. **Configure your custom links:**
   ```bash
   cd /path/to/your/project
   python setup-links.py create --file docs/links.yml
   ```

3. **Edit the links file** (`docs/links.yml`) to add your custom menu items

4. **Build your site:**
   ```bash
   mkdocs serve  # For development
   mkdocs build  # For production
   ```

## Links File Configuration

### Basic Format (YAML)

```yaml
links:
  - title: "Project Home"
    url: "https://example.com"
    description: "Main project website"
    
  - title: "GitHub Repository"
    url: "https://github.com/username/repo"
    category: "Development"
    description: "Source code and issues"
```

### Using Template Variables

You can use Jinja template variables from your Copier configuration:

```yaml
links:
  - title: "Repository"
    url: "https://github.com/{{ github_username }}/{{ repo_name }}"
    
  - title: "Project Site"
    url: "{{ site_url }}"
```

### Link Properties

- **title** (required): Display name in navigation
- **url** or **link** (required): Target URL
- **category** (optional): Groups links under subsections
- **description** (optional): Adds explanatory text

### Categories

Links with the same `category` are grouped together:

```yaml
links:
  - title: "User Manual"
    url: "https://manual.example.com"
    category: "Documentation"
    
  - title: "API Docs"
    url: "https://api.example.com"
    category: "Documentation"
    
  - title: "Bug Tracker"
    url: "https://bugs.example.com"
    category: "Development"
```

Results in navigation structure:
```
- External Links:
  - Documentation:
    - User Manual
    - API Docs
  - Development:
    - Bug Tracker
```

## Management Commands

### Validate Links File
```bash
python setup-links.py validate --file docs/links.yml
```

### Create Sample Links File
```bash
# Create YAML format (default)
python setup-links.py create --file docs/links.yml

# Create JSON format
python setup-links.py create --file docs/links.json --format json
```

### List All Links
```bash
python setup-links.py list --file docs/links.yml
```

## Advanced Configuration

### Custom Section Title

When running the Copier template, you can customize the section title:

```bash
copier copy ./copier/mkdocs /path/to/project --data links_section_title="Useful Links"
```

### Disable Custom Links

```bash
copier copy ./copier/mkdocs /path/to/project --data enable_custom_links=false
```

### Different Links File Name

```bash
copier copy ./copier/mkdocs /path/to/project --data links_file="custom-links.yml"
```

## Integration with MkDocs

The custom links are automatically integrated into the MkDocs navigation through:

1. **Navigation Hook**: `hooks/nav_post_gen_v2.py` processes the links file
2. **SUMMARY.md Generation**: Links are added to the auto-generated navigation
3. **Template Variables**: Copier variables are available in the links file

## Example Project Structure

```
my-project/
├── docs/
│   ├── index.md
│   ├── links.yml              # Your custom links
│   ├── getting-started.md
│   ├── tutorials/
│   │   ├── basic.md
│   │   └── advanced.md
│   └── reference/
│       └── api.md
├── mkdocs.yml                 # Generated MkDocs config
├── hooks/
│   └── nav_post_gen_v2.py     # Navigation generation hook
└── setup-links.py             # Links management script
```

## Troubleshooting

### Links Not Appearing
- Check that `enable_custom_links` is `true` in your Copier configuration
- Validate your links file with `python setup-links.py validate`
- Ensure the links file path matches the `links_file` configuration

### Template Variable Errors
- Make sure Jinja variables in your links file match your Copier configuration
- Use `{{ variable_name }}` syntax for template variables

### YAML/JSON Syntax Errors
- Use the validation command to check syntax: `python setup-links.py validate`
- Ensure proper indentation for YAML files
- Check for missing quotes around URLs in YAML

### Navigation Order Issues
- Links section appears after all documentation content
- Within categories, links maintain the order from your file
- Root-level links appear before categorized links
