#!/usr/bin/env python3
"""
Template Prefill Link Generator

Generates CONTRIBUTING.md with prefilled GitHub issue links for modifying
existing data entries. Reads JSON files from src-data branch and creates
links that pre-populate the issue form fields.

Uses shared utilities from template_utils.py.
"""

import subprocess
import yaml
import glob, os, json
from urllib.parse import urlencode
from typing import OrderedDict
from tqdm import tqdm

# Import shared utilities
from .template_utils import (
    get_repo_info,
    get_folders_from_branch,
    get_json_files_from_branch,
    get_file_content_from_branch,
    get_template_fields_and_options,
    find_matching_option,
    extract_value,
    generate_prefill_link,
    generate_prefill_links_for_folder,
    DATA_BRANCH
)


def print_red(*args, sep=' ', end='\n', flush=False):
    """Print text in red (ANSI) in Jupyter or terminal output."""
    RED = '\033[31m'
    RESET = '\033[0m'
    print(RED + sep.join(map(str, args)) + RESET, end=end, flush=flush)


CONTRIBUTING_FILE = '.github/CONTRIBUTING.md'
DESCRIPTION_FILE = '.github/description.md'
ISSUES_FILE = '.github/issues.md'


def get_template_categories():
    """Get categories from issue templates (CSV files in GEN_ISSUE_TEMPLATE or YAML in ISSUE_TEMPLATE)."""
    categories = []
    
    # First try GEN_ISSUE_TEMPLATE (source of truth)
    gen_template_dir = ".github/GEN_ISSUE_TEMPLATE"
    if os.path.exists(gen_template_dir):
        for csv_file in glob.glob(f"{gen_template_dir}/*.csv"):
            name = os.path.basename(csv_file).replace('.csv', '')
            # Skip general_issue as it's not an entity type
            if name not in ['general_issue']:
                categories.append(name)
    
    # Fallback to ISSUE_TEMPLATE if no GEN_ISSUE_TEMPLATE
    if not categories:
        issue_template_dir = ".github/ISSUE_TEMPLATE"
        if os.path.exists(issue_template_dir):
            for yml_file in glob.glob(f"{issue_template_dir}/*.yml"):
                name = os.path.basename(yml_file).replace('.yml', '')
                # Skip config.yml and general_issue
                if name not in ['config', 'general_issue']:
                    categories.append(name)
    
    return sorted(categories)


# Fetch from origin (but don't fail if it doesn't work)
try:
    subprocess.run(
        ["git", "fetch", "origin"],
        capture_output=True,
        text=True,
        check=True
    )
    print(f"Fetched from origin (including {DATA_BRANCH} branch)")
except:
    print_red("Could not fetch from origin, using local files only")


def process_category(category, repo_url, repo_name):
    '''
    Process a category (template) and generate modification links if data exists.
    
    Uses the shared utility functions for link generation.
    '''
    
    display_name = category.replace('_', ' ').title()
    folder = category  # folder name matches template name
    
    # Check for JSON files on src-data branch
    json_files = get_json_files_from_branch(folder, DATA_BRANCH)
    
    if not json_files:
        # No data yet - skip this category
        return None

    # Get template fields and dropdown options
    ids, dropdown, multi, dropdown_options = get_template_fields_and_options(category)
    
    if not ids:
        print_red(f"No template found for {category}")
        return None

    urls = []

    for filepath in tqdm(json_files, desc=category):
        print(f"Processing file: {filepath}")
        
        # Get file content from branch
        content = get_file_content_from_branch(filepath, DATA_BRANCH)
        if not content:
            continue
            
        try:
            jd = json.loads(content)
        except Exception as e:
            print_red(f"Error parsing {filepath}: {e}")
            continue

        match = OrderedDict()
        
        match['template'] = f"{category}.yml"
        
        # Get the ID for the title
        item_id = jd.get('validation_key', jd.get('id', jd.get('@id', f'Unknown ({filepath})')))
        match['title'] = f"Modify: {display_name}: {item_id}"
        match['issue_kind'] = '"Modify"'
        
        for key in ids:
            try:
                if key in jd:
                    value = jd.get(key)
                    entry = extract_value(value)
                    
                    if key in multi:
                        # Multi-select: handle list of values
                        if isinstance(entry, str):
                            # Single value - find matching option
                            matched = find_matching_option(entry, dropdown_options.get(key, []))
                            entry = f'"{matched}"'
                        else:
                            # Multiple values - find matching options for each
                            matched_entries = []
                            for e in list(entry):
                                matched = find_matching_option(e, dropdown_options.get(key, []))
                                matched_entries.append(f'"{matched}"')
                            entry = ','.join(matched_entries)
                    elif key in dropdown:
                        # Single dropdown - find matching option
                        matched = find_matching_option(entry, dropdown_options.get(key, []))
                        entry = f'"{matched}"'
                    elif isinstance(entry, list): 
                        entry = ', '.join(str(e) for e in entry)
                    
                    match[key] = entry
            except Exception as ex:
                print_red(f"Error processing {filepath} [{key}]: {ex}")
                continue

        query_string = f'{repo_url}/issues/new?' + urlencode(match)
        print(query_string)
        
        mdlink = "- [" + str(item_id) + "](" + query_string + ")\n"
        print(mdlink)
        
        urls.append(mdlink)
    
    if not urls:
        return None
    
    urlgroup = "\n".join(sorted(urls))
        
    entry = f'''
<details markdown="1" name="{category}">
<summary>{display_name} ({len(urls)} entries)</summary>

{urlgroup}
</details>
'''

    return entry


def read_file_if_exists(filepath):
    """Read a file if it exists, return empty string otherwise."""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"📄 Found {filepath}")
            return content
    return ""


def main():
    # Get repository info
    repo_info = get_repo_info()
    if repo_info[0] is None:
        print_red("Could not get repository info")
        return
    
    repo_url, owner, repo_name = repo_info
    print(f"Repository: {repo_url}")
    print(f"Owner: {owner}, Repo: {repo_name}")
    
    # Get categories from templates (on current branch, usually main)
    categories = get_template_categories()
    print(f"Found template categories: {categories}")
    
    # Get data folders from src-data branch
    data_folders = get_folders_from_branch(DATA_BRANCH)
    print(f"Found data folders on {DATA_BRANCH}: {data_folders}")
    
    # Merge: templates + any data folders not in templates
    all_categories = sorted(set(categories + data_folders))
    print(f"All categories to process: {all_categories}")
    
    # Build modification links content
    modifications_entries = []
    for category in all_categories:
        print(f"\nProcessing category: {category}")
        entry = process_category(category, repo_url, repo_name)
        if entry:
            modifications_entries.append(entry)
    
    # Start building CONTRIBUTING.md
    contributing_content = ""
    
    # 1. Add description.md content (unchanged)
    description_content = read_file_if_exists(DESCRIPTION_FILE)
    if description_content:
        contributing_content += description_content
        if not contributing_content.endswith('\n'):
            contributing_content += '\n'
    
    # 2. Add issues.md content (unchanged)
    issues_content = read_file_if_exists(ISSUES_FILE)
    if issues_content:
        contributing_content += issues_content
        if not contributing_content.endswith('\n'):
            contributing_content += '\n'
    
    # 3. Add modification links at the end
    if modifications_entries:
        contributing_content += f'''
## 2. Modifying or reusing existing entries

The following links will open pre-filled GitHub issues with content from the selected files. These can be used to update entries or make new ones. 
'''
        for entry in modifications_entries:
            contributing_content += entry
    
    # Write CONTRIBUTING.md
    with open(CONTRIBUTING_FILE, 'w', encoding='utf-8') as f:
        f.write(contributing_content)
    print(f"\n✅ Output written to {CONTRIBUTING_FILE}")


if __name__ == "__main__":
    main()
