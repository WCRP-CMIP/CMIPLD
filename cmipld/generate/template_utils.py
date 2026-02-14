#!/usr/bin/env python3
"""
Template Utilities

Shared functions for template generation and prefill link creation.
Can be imported by template .py files to generate dynamic content.
"""

import subprocess
import json
import os
import glob
import yaml
from urllib.parse import urlencode
from typing import Optional, Dict, List, Any, OrderedDict, Union

# Default branch for data files
DATA_BRANCH = 'src-data'


def get_repo_info() -> tuple:
    """
    Get repository URL, owner and name from git remote.
    
    Returns:
        tuple: (repo_url, owner, repo_name)
    """
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        
        if remote_url.startswith('https://'):
            parts = remote_url.replace('.git', '').split('/')
            owner = parts[-2]
            repo = parts[-1]
        elif remote_url.startswith('git@'):
            parts = remote_url.replace('.git', '').split(':')[-1].split('/')
            owner = parts[0]
            repo = parts[1]
        else:
            owner = 'UNKNOWN'
            repo = 'UNKNOWN'
        
        repo_url = f"https://github.com/{owner}/{repo}"
        return repo_url, owner, repo
    except Exception as e:
        return None, None, None


def get_folders_from_branch(branch: str = DATA_BRANCH) -> List[str]:
    """
    Get list of data folders from a specific git branch.
    
    Args:
        branch: The git branch to check
        
    Returns:
        List of folder names
    """
    folders = []
    skip_folders = ['project', 'cmor', 'content_summaries', 'docs', 'summaries', 
                    '.git', '.github', '.src', '__pycache__']
    
    try:
        result = subprocess.run(
            ["git", "ls-tree", "-d", "--name-only", f"origin/{branch}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in result.stdout.strip().split('\n'):
            folder = line.strip()
            if folder and folder not in skip_folders and not folder.startswith('.'):
                folders.append(folder)
                
    except subprocess.CalledProcessError:
        pass
    
    return sorted(folders)


def get_json_files_from_branch(folder: str, branch: str = DATA_BRANCH) -> List[str]:
    """
    Get list of JSON files in a folder from a specific branch.
    
    Args:
        folder: The folder name to check
        branch: The git branch to check
        
    Returns:
        List of JSON file paths
    """
    json_files = []
    
    try:
        result = subprocess.run(
            ["git", "ls-tree", "--name-only", f"origin/{branch}", f"{folder}/"],
            capture_output=True,
            text=True,
            check=True
        )
        
        for line in result.stdout.strip().split('\n'):
            filename = line.strip()
            if filename.endswith('.json') and 'graph.jsonld' not in filename:
                json_files.append(filename)
                
    except subprocess.CalledProcessError:
        pass
    
    return json_files


def get_file_content_from_branch(filepath: str, branch: str = DATA_BRANCH) -> Optional[str]:
    """
    Get file content from a specific branch.
    
    Args:
        filepath: Path to the file
        branch: The git branch to check
        
    Returns:
        File content as string, or None if not found
    """
    try:
        result = subprocess.run(
            ["git", "show", f"origin/{branch}:{filepath}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None


def normalize_value(val: Any) -> Optional[str]:
    """Normalize a value for comparison (lowercase, hyphens to underscores)."""
    if val is None:
        return None
    return str(val).lower().replace('-', '_').replace(' ', '_')


def find_matching_option(value: str, options: List[str]) -> str:
    """
    Find the matching option from a list of dropdown options.
    
    Handles case-insensitivity and hyphen/underscore differences.
    
    Args:
        value: The value to match
        options: List of available options
        
    Returns:
        The exact option text if found, otherwise the original value
    """
    if not options or not value:
        return value
    
    normalized_value = normalize_value(value)
    
    for option in options:
        if normalize_value(option) == normalized_value:
            return option
    
    return value


def extract_value(val: Any) -> Any:
    """
    Extract the relevant value from a field (handles nested dicts/lists).
    
    Args:
        val: The value to extract from
        
    Returns:
        Extracted value (string or list of strings)
    """
    if isinstance(val, list):
        return [extract_value(v) for v in val]
    if isinstance(val, dict):
        val = next(iter(val.values()))
        return val.get('validation_key', val.get('@id'))
    return val


def get_template_fields_and_options(folder: str) -> tuple:
    """
    Get field IDs, types, and dropdown options from the YAML issue template.
    
    Args:
        folder: The template name (without extension)
        
    Returns:
        tuple: (field_ids, dropdown_fields, multi_select_fields, dropdown_options)
    """
    template_name = f"{folder}.yml"
    dyaml = None
    
    # Try local file first
    try:
        with open(f".github/ISSUE_TEMPLATE/{template_name}", 'r') as f:
            dyaml = yaml.safe_load(f)
    except:
        pass
    
    # Try git if local failed
    if dyaml is None:
        try:
            result = subprocess.run(
                ["git", "show", f"refs/remotes/origin/main:.github/ISSUE_TEMPLATE/{template_name}"],
                capture_output=True,
                text=True,
                check=True
            )
            dyaml = yaml.safe_load(result.stdout)
        except:
            return set(), [], [], {}
    
    ids = set([item['id'] for item in dyaml['body'] if 'id' in item])
    dropdown = []
    multi = []
    dropdown_options = {}

    for entry in dyaml['body']:
        if entry['type'] == 'dropdown':
            if 'id' in entry:
                field_id = entry['id']
                dropdown.append(field_id)
                options = entry.get('attributes', {}).get('options', [])
                dropdown_options[field_id] = options
                
                if entry['attributes'].get('multiple', False):
                    multi.append(field_id)

    return ids, dropdown, multi, dropdown_options


def load_template_config(template_name: str) -> Optional[Dict]:
    """
    Load template JSON configuration file.
    
    Args:
        template_name: Template name (without extension)
        
    Returns:
        Config dictionary or None if not found
    """
    config_paths = [
        f".github/GEN_ISSUE_TEMPLATE/{template_name}.json",
        f".github/ISSUE_TEMPLATE/{template_name}.json",
    ]
    
    for path in config_paths:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            continue
    
    return None


def resolve_prefill_sources(config: Dict) -> Dict[str, Dict]:
    """
    Resolve prefill_sources from template config into normalized format.
    
    Supports multiple formats:
    - Not set / "all": Use folder matching issue_category with all fields
    - {"folder": "all"}: All fields from folder
    - {"folder": {...}}: Custom config for folder
    
    Config options per folder:
    - display_name: JSON key to use as link text (default: "name" or "@id")
    - subtitle: JSON key for secondary info (optional)
    - section_title: Header text for this group (optional)
    - fields: "all" or list of field names (default: "all")
    - field_mapping: {json_key: template_field_id} for renaming
    - link_type: "prefill" (default), "reference", or "view"
    
    Args:
        config: Template configuration dictionary
        
    Returns:
        Dictionary of folder -> resolved config
    """
    sources = config.get("prefill_sources")
    category = config.get("issue_category", "")
    
    # Default config for a folder
    def default_config(folder: str) -> Dict:
        return {
            "folder": folder,
            "display_name": "name",
            "subtitle": None,
            "section_title": None,
            "fields": "all",
            "field_mapping": {},
            "link_type": "prefill"
        }
    
    # Case 1: Not set or "all" string - use issue_category folder
    if sources is None or sources == "all":
        if category:
            return {category: default_config(category)}
        return {}
    
    # Case 2: Dictionary of folder configs
    resolved = {}
    for folder, folder_config in sources.items():
        if folder_config == "all":
            resolved[folder] = default_config(folder)
        elif isinstance(folder_config, dict):
            resolved[folder] = {
                "folder": folder,
                "display_name": folder_config.get("display_name", "name"),
                "subtitle": folder_config.get("subtitle"),
                "section_title": folder_config.get("section_title"),
                "fields": folder_config.get("fields", "all"),
                "field_mapping": folder_config.get("field_mapping", {}),
                "link_type": folder_config.get("link_type", "prefill")
            }
        else:
            resolved[folder] = default_config(folder)
    
    return resolved


def apply_field_mapping(data: Dict, config: Dict) -> Dict:
    """
    Apply field selection and mapping to JSON data for prefill.
    
    Args:
        data: Original JSON data from file
        config: Resolved prefill source config for this folder
        
    Returns:
        Mapped data dictionary ready for prefill
    """
    fields = config.get("fields", "all")
    mapping = config.get("field_mapping", {})
    
    # Start with all or selected fields
    if fields == "all":
        result = dict(data)
    else:
        result = {k: v for k, v in data.items() if k in fields}
    
    # Apply renames: json_key -> template_field_id
    for json_key, template_field in mapping.items():
        if json_key in result:
            value = result.pop(json_key)
            result[template_field] = value
        elif json_key in data:
            # Field wasn't in result but exists in original - add with new name
            result[template_field] = data[json_key]
    
    return result


def generate_prefill_link(
    repo_url: str,
    template_name: str,
    data: Dict[str, Any],
    title: Optional[str] = None,
    issue_kind: str = "Modify"
) -> str:
    """
    Generate a GitHub issue prefill link.
    
    Args:
        repo_url: The repository URL (e.g., https://github.com/owner/repo)
        template_name: The template filename (e.g., model.yml)
        data: Dictionary of field_id -> value pairs
        title: Optional issue title
        issue_kind: "New" or "Modify"
        
    Returns:
        Full URL with prefilled parameters
    """
    params = OrderedDict()
    params['template'] = template_name
    
    if title:
        params['title'] = title
    
    params['issue_kind'] = f'"{issue_kind}"'
    
    # Add data fields
    for key, value in data.items():
        if value is not None:
            params[key] = value
    
    return f'{repo_url}/issues/new?' + urlencode(params)


def generate_prefill_links_for_folder(
    folder: str,
    repo_url: Optional[str] = None,
    branch: str = DATA_BRANCH,
    template_name: Optional[str] = None,
    source_config: Optional[Dict] = None
) -> List[Dict[str, str]]:
    """
    Generate prefill links for all JSON files in a folder.
    
    Args:
        folder: The data folder name
        repo_url: Repository URL (auto-detected if None)
        branch: Git branch containing data files
        template_name: Target template (defaults to folder name)
        source_config: Prefill source config (from resolve_prefill_sources)
        
    Returns:
        List of dicts with 'id', 'name', 'subtitle', 'url', 'markdown', 'link_type'
    """
    if repo_url is None:
        repo_url, _, _ = get_repo_info()
        if not repo_url:
            return []
    
    if template_name is None:
        template_name = folder
    
    json_files = get_json_files_from_branch(folder, branch)
    if not json_files:
        return []
    
    ids, dropdown, multi, dropdown_options = get_template_fields_and_options(template_name)
    if not ids:
        return []
    
    # Default source config
    if source_config is None:
        source_config = {
            "folder": folder,
            "display_name": "name",
            "subtitle": None,
            "fields": "all",
            "field_mapping": {},
            "link_type": "prefill"
        }
    
    links = []
    yaml_template = f"{template_name}.yml"
    display_folder = folder.replace('_', ' ').title()
    
    for filepath in json_files:
        content = get_file_content_from_branch(filepath, branch)
        if not content:
            continue
        
        try:
            jd = json.loads(content)
        except:
            continue
        
        # Get display values
        item_id = jd.get('validation_key', jd.get('id', jd.get('@id', 'Unknown')))
        display_name_key = source_config.get("display_name", "name")
        display_name = jd.get(display_name_key, jd.get('name', item_id))
        
        subtitle_key = source_config.get("subtitle")
        subtitle = jd.get(subtitle_key) if subtitle_key else None
        
        link_type = source_config.get("link_type", "prefill")
        
        # Apply field mapping
        mapped_data = apply_field_mapping(jd, source_config)
        
        # Build prefill data
        data = {}
        for key in ids:
            # Check both original key and mapped keys
            value = mapped_data.get(key)
            if value is None:
                continue
                
            entry = extract_value(value)
            
            if key in multi:
                if isinstance(entry, str):
                    matched = find_matching_option(entry, dropdown_options.get(key, []))
                    entry = f'"{matched}"'
                else:
                    matched_entries = []
                    for e in list(entry):
                        matched = find_matching_option(e, dropdown_options.get(key, []))
                        matched_entries.append(f'"{matched}"')
                    entry = ','.join(matched_entries)
            elif key in dropdown:
                matched = find_matching_option(entry, dropdown_options.get(key, []))
                entry = f'"{matched}"'
            elif isinstance(entry, list):
                entry = ', '.join(str(e) for e in entry)
            
            data[key] = entry
        
        # Generate URL based on link type
        if link_type == "prefill":
            url = generate_prefill_link(
                repo_url=repo_url,
                template_name=yaml_template,
                data=data,
                title=f"Modify: {display_folder}: {item_id}",
                issue_kind="Modify"
            )
        elif link_type == "view":
            url = f"{repo_url}/blob/{branch}/{filepath}"
        else:  # reference
            url = None
        
        # Build markdown
        if subtitle:
            label = f"{display_name} ({subtitle})"
        else:
            label = str(display_name)
        
        if url:
            markdown = f"- [{label}]({url})"
        else:
            markdown = f"- `{item_id}`: {label}"
        
        links.append({
            'id': item_id,
            'name': display_name,
            'subtitle': subtitle,
            'url': url,
            'markdown': markdown,
            'link_type': link_type,
            'folder': folder
        })
    
    return sorted(links, key=lambda x: str(x.get('name', x['id'])))


def get_existing_entries_markdown(
    template_or_folder: str,
    repo_url: Optional[str] = None,
    branch: str = DATA_BRANCH
) -> str:
    """
    Generate markdown content listing existing entries with prefill links.
    
    Supports:
    - Single folder name (backwards compatible)
    - Template name with prefill_sources config
    
    Args:
        template_or_folder: Template name or folder name
        repo_url: Repository URL (auto-detected if None)
        branch: Git branch containing data
        
    Returns:
        Markdown string with links grouped by section, or empty string
    """
    if repo_url is None:
        repo_url, _, _ = get_repo_info()
        if not repo_url:
            return ""
    
    # Try to load template config
    config = load_template_config(template_or_folder)
    
    if config:
        # Use prefill_sources from config
        sources = resolve_prefill_sources(config)
        template_name = template_or_folder
    else:
        # Backwards compatible: single folder
        sources = {
            template_or_folder: {
                "folder": template_or_folder,
                "display_name": "name",
                "subtitle": None,
                "section_title": None,
                "fields": "all",
                "field_mapping": {},
                "link_type": "prefill"
            }
        }
        template_name = template_or_folder
    
    # Generate links for each source folder
    sections = []
    
    for folder, source_config in sources.items():
        links = generate_prefill_links_for_folder(
            folder=folder,
            repo_url=repo_url,
            branch=branch,
            template_name=template_name,
            source_config=source_config
        )
        
        if not links:
            continue
        
        section_title = source_config.get("section_title")
        link_markdown = "\n".join(link['markdown'] for link in links)
        
        if section_title:
            sections.append(f"**{section_title}**\n\n{link_markdown}")
        else:
            sections.append(link_markdown)
    
    if not sections:
        return ""
    
    return "\n\n".join(sections)


def get_prefill_links_by_folder(
    template_name: str,
    repo_url: Optional[str] = None,
    branch: str = DATA_BRANCH
) -> Dict[str, List[Dict]]:
    """
    Get prefill links organized by source folder.
    
    Useful when you need programmatic access to links by folder.
    
    Args:
        template_name: Template name
        repo_url: Repository URL
        branch: Git branch
        
    Returns:
        Dictionary of folder -> list of link dicts
    """
    if repo_url is None:
        repo_url, _, _ = get_repo_info()
        if not repo_url:
            return {}
    
    config = load_template_config(template_name)
    if not config:
        return {}
    
    sources = resolve_prefill_sources(config)
    result = {}
    
    for folder, source_config in sources.items():
        links = generate_prefill_links_for_folder(
            folder=folder,
            repo_url=repo_url,
            branch=branch,
            template_name=template_name,
            source_config=source_config
        )
        if links:
            result[folder] = links
    
    return result
