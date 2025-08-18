# CMIP-LD MkDocs Copier Template

A copier template for generating CMIP-LD documentation projects that use the centralized CMIP-LD actions library.

## Features

- 📚 **MkDocs Documentation**: Complete setup with Material theme
- 🏗️ **Reusable Actions**: Uses CMIP-LD/actions for consistency and maintainability  
- 🔗 **JSON-LD Processing**: Automated JSON-LD validation and processing
- 📋 **Issue Management**: Automated issue processing
- 🚀 **GitHub Pages**: Direct deployment to GitHub Pages
- ⚙️ **Configurable**: Choose which workflows to generate

## Generated Workflows

All workflows use the centralized **CMIP-LD/actions** library for consistency and maintainability.

### 1. Build Documentation (`build-docs.yml`)
**When enabled**: `enable_build_docs: true`

- **Uses**: `CMIP-LD/actions/build-docs@main`
- **Triggers**: Push to `build_trigger_branch` + manual dispatch
- **Purpose**: Build MkDocs documentation and deploy to target branch

### 2. Static Pages (`static.yml`)
**When enabled**: `enable_static_pages: true`

- **Uses**: Standard GitHub Pages actions
- **Triggers**: Manual dispatch + push to target branch
- **Purpose**: Deploy `src-data/` directly to GitHub Pages

### 3. Update JSON-LD (`update-jsonld.yml`)
**When enabled**: `enable_jsonld_workflows: true`

- **Uses**: Multiple CMIP-LD actions:
  - `CMIP-LD/actions/cmipld@main` - Install CMIP-LD
  - `CMIP-LD/actions/updated-dirs@main` - Detect changes
  - `CMIP-LD/actions/process_jsonld@main` - Process JSON-LD
  - `CMIP-LD/actions/commit-all@main` - Commit changes
  - `CMIP-LD/actions/pushpr@main` - Create pull requests
  - `CMIP-LD/actions/publish2pages@main` - Publish to pages

### 4. Check JSON-LD (`check-jsonld.yml`) 
**When enabled**: `enable_jsonld_workflows: true`

- **Uses**: `CMIP-LD/actions/check-graph@main`
- **Triggers**: After static pages deployment
- **Purpose**: Validate JSON-LD graph from deployed pages

### 5. New Issue Processing (`new-issue.yml`)
**When enabled**: `enable_new_issue: true`

- **Uses**: `CMIP-LD/actions/new-issue@main`
- **Triggers**: Issues opened/edited
- **Purpose**: Automated issue processing and labeling

## Usage

### Quick Start

```bash
copier copy /path/to/CMIP-LD/copier/mkdocs ./my-project
```

### Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `enable_build_docs` | `true` | Use CMIP-LD/actions/build-docs |
| `enable_static_pages` | `true` | GitHub Pages deployment |
| `enable_jsonld_workflows` | `true` | JSON-LD processing actions |
| `enable_new_issue` | `true` | Use CMIP-LD/actions/new-issue |
| `build_trigger_branch` | `published` | Branch that triggers builds |
| `build_target_branch` | `production` | Where docs are deployed |

### Example Configuration

```yaml
project_name: "Variable Registry"
repo_name: "Variable-Registry"
github_username: "WCRP-CMIP"
enable_build_docs: true
enable_static_pages: true  
enable_jsonld_workflows: true
enable_new_issue: true
build_trigger_branch: "published"
build_target_branch: "production"
```

## Generated Structure

```
your-project/
├── .github/workflows/
│   ├── build-docs.yml          # Uses CMIP-LD/actions/build-docs
│   ├── static.yml              # Standard GitHub Pages
│   ├── update-jsonld.yml       # Uses multiple CMIP-LD actions
│   ├── check-jsonld.yml        # Uses CMIP-LD/actions/check-graph
│   └── new-issue.yml           # Uses CMIP-LD/actions/new-issue
├── .src/mkdocs/
│   ├── mkdocs.yml             # MkDocs configuration
│   └── requirements.txt        # Python dependencies
├── docs/                       # Documentation source
├── src-data/                   # JSON-LD data files
└── README.md
```

## Why Use CMIP-LD Actions?

### ✅ **Centralized Maintenance**
- Actions are maintained in one place
- Bug fixes and improvements benefit all projects
- Consistent behavior across projects

### ✅ **Simplified Workflows**
- Workflows are short and focused
- Complex logic is encapsulated in actions
- Easy to understand and maintain

### ✅ **Version Control**
- Use specific action versions with `@main`, `@v1`, etc.
- Can pin to specific commits for stability
- Easy rollback if needed

### ✅ **Reusability**
- Same actions used across multiple projects
- Reduces duplication of workflow code
- Easier to onboard new projects

## Available CMIP-LD Actions

The template uses these actions from the CMIP-LD actions library:

| Action | Purpose |
|--------|---------|
| `CMIP-LD/actions/build-docs@main` | Build and deploy MkDocs documentation |
| `CMIP-LD/actions/cmipld@main` | Install CMIP-LD Python package |
| `CMIP-LD/actions/updated-dirs@main` | Detect changed directories |
| `CMIP-LD/actions/process_jsonld@main` | Process JSON-LD files |
| `CMIP-LD/actions/commit-all@main` | Commit all changes |
| `CMIP-LD/actions/pushpr@main` | Create pull requests |
| `CMIP-LD/actions/publish2pages@main` | Publish to GitHub Pages |
| `CMIP-LD/actions/check-graph@main` | Validate JSON-LD graphs |
| `CMIP-LD/actions/new-issue@main` | Process new issues |

## Requirements

- **Repository**: GitHub repository with Actions enabled
- **Secrets**: May need `API_KEY` for some publishing actions
- **Permissions**: GitHub Pages enabled for static deployment

## Workflow Dependencies

Some workflows depend on others:
- `check-jsonld.yml` runs after `static.yml` completes
- `update-jsonld.yml` triggers on changes to `src-data/`
- `build-docs.yml` triggers on changes to documentation branch

## Customization

### Disable Workflows

```yaml
enable_build_docs: false       # No documentation building
enable_static_pages: false     # No GitHub Pages
enable_jsonld_workflows: false # No JSON-LD processing
enable_new_issue: false        # No issue processing
```

### Custom Branches

```yaml
build_trigger_branch: "main"     # Build from main
build_target_branch: "gh-pages" # Deploy to gh-pages
```

## Testing

The template generates workflows that use well-tested, centralized actions, reducing the need for extensive testing of individual workflows.

## Updating Projects

Update existing projects with template changes:

```bash
copier update
```

This will update workflow files while preserving your configuration.

## Contributing

To contribute:
1. **For workflow logic**: Contribute to the CMIP-LD actions library
2. **For template structure**: Modify this copier template
3. **For new workflows**: Add new action to CMIP-LD/actions, then add template here

## Benefits of This Approach

- 🎯 **Single source of truth**: Copier generates all workflows  
- 🔧 **Reusable components**: Actions are shared across projects
- 📋 **Consistent**: All projects use same tested actions
- 🚀 **Maintainable**: Updates to actions benefit all projects
- 📚 **Simple**: Workflows are clean and easy to understand

## License

Part of the CMIP-LD project.
