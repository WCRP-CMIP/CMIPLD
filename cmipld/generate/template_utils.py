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
from typing import Optional, Dict, List, Any, OrderedDict

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
    branch: str = DATA_BRANCH
) -> List[Dict[str, str]]:
    """
    Generate prefill links for all JSON files in a folder.
    
    This can be used in template .py files to generate dynamic DATA content.
    
    Args:
        folder: The data folder name (matches template name)
        repo_url: Repository URL (auto-detected if None)
        branch: Git branch containing data files
        
    Returns:
        List of dicts with 'id', 'url', and 'markdown' keys
    """
    if repo_url is None:
        repo_url, _, _ = get_repo_info()
        if not repo_url:
            return []
    
    json_files = get_json_files_from_branch(folder, branch)
    if not json_files:
        return []
    
    ids, dropdown, multi, dropdown_options = get_template_fields_and_options(folder)
    if not ids:
        return []
    
    links = []
    template_name = f"{folder}.yml"
    display_name = folder.replace('_', ' ').title()
    
    for filepath in json_files:
        content = get_file_content_from_branch(filepath, branch)
        if not content:
            continue
        
        try:
            jd = json.loads(content)
        except:
            continue
        
        item_id = jd.get('validation_key', jd.get('id', jd.get('@id', f'Unknown')))
        
        data = {}
        for key in ids:
            if key in jd:
                value = jd.get(key)
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
        
        url = generate_prefill_link(
            repo_url=repo_url,
            template_name=template_name,
            data=data,
            title=f"Modify: {display_name}: {item_id}",
            issue_kind="Modify"
        )
        
        links.append({
            'id': item_id,
            'url': url,
            'markdown': f"- [{item_id}]({url})"
        })
    
    return sorted(links, key=lambda x: x['id'])


def get_existing_entries_markdown(folder: str, repo_url: Optional[str] = None) -> str:
    """
    Generate markdown content listing all existing entries with prefill links.
    
    Useful for including in template DATA for dynamic guidance.
    
    Args:
        folder: The data folder name
        repo_url: Repository URL (auto-detected if None)
        
    Returns:
        Markdown string with links, or empty string if no entries
    """
    links = generate_prefill_links_for_folder(folder, repo_url)
    if not links:
        return ""
    
    return "\n".join(link['markdown'] for link in links)
