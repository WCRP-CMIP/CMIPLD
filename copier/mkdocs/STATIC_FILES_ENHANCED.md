# Static Files Generator - Enhanced Features

## Overview

The static files generator script has been enhanced with two major improvements:

1. **Non-destructive generation**: Existing files are never overwritten
2. **Visual sitemap**: Generates an interactive HTML sitemap in addition to XML

## Features

### 1. Skip Existing Files

The generator now checks if files already exist before creating them. This allows you to:
- Manually customize generated files without losing changes
- Incrementally add new static files without regenerating everything
- Preserve custom modifications between builds

When a file already exists, you'll see:
```
⏭️  Skipping existing file: static_output/api_manifest.json
```

### 2. Visual Sitemap

In addition to the standard `sitemap.xml`, the generator creates `sitemap.html` - an interactive visual representation of your site structure.

#### Features of the Visual Sitemap:
- **Hierarchical tree view** of all pages
- **Collapsible directories** (click folder names to expand/collapse)
- **Direct links** to all pages
- **Visual icons** for files (📄) and folders (📁/📂)
- **Statistics bar** showing site URL and generation time
- **Responsive design** that works on all devices
- **Theme integration** using your selected header color

### Usage

1. Run the static file generator:
   ```bash
   python scripts/generate_static.py
   ```

2. View the visual sitemap:
   - Open `static_output/sitemap.html` in a browser
   - Or after deployment, visit: `https://yoursite.com/static_output/sitemap.html`

### Generated Files

The script generates these files (only if they don't already exist):

| File | Description | Overwrite Protection |
|------|-------------|---------------------|
| `api_manifest.json` | API endpoints and metadata | ✅ Protected |
| `sitemap.xml` | Standard XML sitemap for search engines | ✅ Protected |
| `sitemap.html` | Visual interactive sitemap | ✅ Protected |
| `robots.txt` | Search engine directives | ✅ Protected |
| `json_index.json` | Index of JSON data files | ✅ Protected |
| `build_info.json` | Build metadata | ✅ Protected |
| `theme_colors.css` | CSS variables for theme | ✅ Protected |

### Customization

To force regeneration of specific files:
1. Delete the existing file(s) you want to regenerate
2. Run the generator script again

To customize generated files:
1. Run the generator once to create initial files
2. Edit the files as needed
3. Future runs will preserve your changes

### Visual Sitemap Customization

The visual sitemap uses your project's theme color and can be customized by editing the generated HTML file. The interactive JavaScript makes directories collapsible for better navigation of large sites.

## Integration with MkDocs

Add the static output directory to your MkDocs extra directories to make the visual sitemap accessible:

```yaml
# In mkdocs.yml
extra:
  static_dirs:
    - static_output
```

Then users can access the visual sitemap at `/static_output/sitemap.html` on your published site.
