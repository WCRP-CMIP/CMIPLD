# Navigation and Existing Files - Troubleshooting Guide

## The Issue

When using `literate-nav` plugin with a generated `SUMMARY.md`, it completely replaces the navigation structure. This can cause existing files in your `docs/` directory to not appear in the built site.

## Solutions

### Solution 1: Use the Updated Script (Recommended)

The updated `gen_wcrp_content.py` script now:
1. **Scans existing documentation files** in your `docs/` directory
2. **Includes them in the generated navigation** along with the WCRP content
3. **Preserves your existing site structure**

The script will:
- Find all `.md` files in your `docs/` directory
- Organize them hierarchically
- Include them in the generated `SUMMARY.md`
- Add the WCRP generated content as a separate section

### Solution 2: Use Manual Navigation

If you prefer more control, you can:

1. Remove the `literate-nav` plugin from `mkdocs.yml`
2. Define your navigation manually
3. Let `gen-files` generate content without affecting navigation

Example `mkdocs.yml`:
```yaml
plugins:
  - search
  - gen-files:
      scripts:
        - scripts/gen_wcrp_content.py
  # Remove literate-nav

nav:
  - Home: index.md
  - Getting Started: getting-started.md
  - User Guide:
    - Overview: guide/overview.md
    - Installation: guide/installation.md
  # Your existing structure
  # Generated files will still be accessible
```

### Solution 3: Use awesome-pages Plugin

Replace `literate-nav` with `awesome-pages` for automatic navigation:

```yaml
plugins:
  - search
  - gen-files:
      scripts:
        - scripts/gen_wcrp_content.py
  - awesome-pages
```

Then create `.pages` files in directories to control order:
```yaml
# docs/.pages
nav:
  - index.md
  - getting-started.md
  - guide
  - wcrp-content
```

## How the Updated Script Works

The new script:

1. **Scans existing files**:
   ```python
   existing_files = scan_existing_docs()
   ```

2. **Builds a hierarchy** of your existing documentation

3. **Generates navigation** that includes both:
   - Your existing files (preserved)
   - Generated WCRP content (added)

4. **Creates SUMMARY.md** with complete navigation

## Verification

To verify your files are included:

1. Run `mkdocs build`
2. Check the console output for: `📚 Found X existing files`
3. Open `SUMMARY.md` - it should list all your files
4. Run `mkdocs serve` and check the navigation

## File Structure Example

```
docs/
├── index.md                 # ✅ Included
├── getting-started.md       # ✅ Included
├── guide/
│   ├── overview.md         # ✅ Included
│   └── installation.md     # ✅ Included
└── wcrp-content/           # 🆕 Generated
    ├── index.md
    ├── projects/
    └── news/
```

All files are preserved and included in navigation!

## Debug Tips

If files are still missing:

1. **Check the docs_dir setting**:
   ```yaml
   docs_dir: docs  # Should point to your docs folder
   ```

2. **Look for scan output**:
   ```
   📂 Scanning existing docs in: docs
   📚 Found 15 existing files
   ```

3. **Examine SUMMARY.md** after build to see what's included

4. **Try without literate-nav** temporarily to isolate the issue

## Alternative: Partial Navigation

You can also use literate-nav for only part of your navigation:

```yaml
nav:
  - Home: index.md
  - User Guide: guide/
  - WCRP Content: "*auto*"  # Only this section uses literate-nav
```

This gives you the best of both worlds - manual control over main navigation with automatic generation for specific sections.
