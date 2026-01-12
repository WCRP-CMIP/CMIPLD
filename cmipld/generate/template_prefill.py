
import subprocess
import yaml
import glob,os,json
from urllib.parse import urlencode
from typing import OrderedDict
import cmipld
from tqdm import tqdm
import tempfile
import shutil

def extract(val):
    ''' Extract the relevant value from a field '''
    if isinstance(val, list):
        return [extract(v) for v in val]
    if isinstance(val, dict):
        val = next(iter(val.values()))
        print(val.get('validation_key'))
        return val.get('validation_key', val.get('@id'))
    return val


def print_red(*args, sep=' ', end='\n', flush=False):
    """Print text in red (ANSI) in Jupyter or terminal output."""
    RED = '\033[31m'
    RESET = '\033[0m'
    print(RED + sep.join(map(str, args)) + RESET, end=end, flush=flush)

OUTFILE = '.github/modifications.md'
DATA_BRANCH = 'src-data'


def get_repo_info():
    """Get repository URL and name from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        
        # Parse the URL to get owner/repo
        if remote_url.startswith('https://'):
            parts = remote_url.replace('.git', '').split('/')
            owner = parts[-2]
            repo = parts[-1]
        elif remote_url.startswith('git@'):
            parts = remote_url.replace('.git', '').split(':')[-1].split('/')
            owner = parts[0]
            repo = parts[1]
        else:
            owner = 'WCRP-CMIP'
            repo = 'Unknown'
        
        repo_url = f"https://github.com/{owner}/{repo}"
        return repo_url, owner, repo
    except Exception as e:
        print_red(f"Error getting repo info: {e}")
        return "https://github.com/WCRP-CMIP/CMIP7-CVs", "WCRP-CMIP", "CMIP7-CVs"


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


def get_folders_from_branch(branch=DATA_BRANCH):
    """Get list of folders from a specific git branch."""
    folders = []
    skip_folders = ['project', 'cmor', 'content_summaries', 'docs', 'summaries', '.git', '.github', '.src', '__pycache__']
    
    try:
        # List tree from the branch
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
                
    except subprocess.CalledProcessError as e:
        print_red(f"Could not list folders from {branch} branch: {e}")
    
    return sorted(folders)


def get_json_files_from_branch(folder, branch=DATA_BRANCH):
    """Get list of JSON files in a folder from a specific branch."""
    json_files = []
    
    try:
        # List files in folder from the branch
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
                
    except subprocess.CalledProcessError as e:
        print_red(f"Could not list files from {folder}/ on {branch}: {e}")
    
    return json_files


def get_file_content_from_branch(filepath, branch=DATA_BRANCH):
    """Get file content from a specific branch."""
    try:
        result = subprocess.run(
            ["git", "show", f"origin/{branch}:{filepath}"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print_red(f"Could not get {filepath} from {branch}: {e}")
        return None


def get_template_name(folder):
    """Convert folder name to template name."""
    return f"{folder}.yml"


def normalize_value(val):
    """Normalize a value for comparison (lowercase, hyphens to underscores)."""
    if val is None:
        return None
    return str(val).lower().replace('-', '_').replace(' ', '_')


def find_matching_option(value, options):
    """Find the matching option from a list of dropdown options.
    
    Handles case-insensitivity and hyphen/underscore differences.
    Returns the exact option text if found, otherwise the original value.
    """
    if not options or not value:
        return value
    
    normalized_value = normalize_value(value)
    
    for option in options:
        if normalize_value(option) == normalized_value:
            return option
    
    # No match found, return original
    return value


def get_template_fields_and_options(folder):
    """Get field IDs, types, and dropdown options from the YAML issue template."""
    template_name = get_template_name(folder)
    dyaml = None
    
    # Try local file first (most up to date)
    try:
        with open(f".github/ISSUE_TEMPLATE/{template_name}", 'r') as f:
            dyaml = yaml.safe_load(f)
    except:
        pass
    
    # Try to get from git if local failed
    if dyaml is None:
        try:
            yresult = subprocess.run(
                ["git", "show", f"refs/remotes/origin/main:.github/ISSUE_TEMPLATE/{template_name}"],
                capture_output=True,
                text=True,
                check=True
            )
            dyaml = yaml.safe_load(yresult.stdout)
        except:
            return set(), [], [], {}
    
    # Get field IDs and types
    ids = set([item['id'] for item in dyaml['body'] if 'id' in item])
    dropdown = []
    multi = []
    dropdown_options = {}  # field_id -> list of options

    for entry in dyaml['body']:
        if entry['type'] == 'dropdown':
            if 'id' in entry:
                field_id = entry['id']
                dropdown.append(field_id)
                
                # Get options for this dropdown
                options = entry.get('attributes', {}).get('options', [])
                dropdown_options[field_id] = options
                
                if entry['attributes'].get('multiple', False):
                    multi.append(field_id)

    return ids, dropdown, multi, dropdown_options


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
    '''
    
    display_name = category.replace('_', ' ').title()
    folder = category  # folder name matches template name
    
    # Check for JSON files on src-data branch
    json_files = get_json_files_from_branch(folder, DATA_BRANCH)
    
    if not json_files:
        # No data yet - show placeholder with link to create new
        new_issue_url = f"{repo_url}/issues/new?template={category}.yml"
        return f'''
<details name="{category}">
<summary>{display_name}</summary>

*No entries registered yet.*

[➕ Register new {display_name}]({new_issue_url})

</details>
'''

    # Get template fields and dropdown options
    ids, dropdown, multi, dropdown_options = get_template_fields_and_options(category)
    
    if not ids:
        print_red(f"No template found for {category}")
        new_issue_url = f"{repo_url}/issues/new?template={category}.yml"
        return f'''
<details name="{category}">
<summary>{display_name}</summary>

*No issue template found for this category.*

</details>
'''

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
        
        match['template'] = get_template_name(category)
        
        # Get the ID for the title
        item_id = jd.get('validation_key', jd.get('id', jd.get('@id', f'Unknown ({filepath})')))
        match['title'] = f"Modify: {display_name}: {item_id}"
        match['issue_kind'] = '"Modify"'
        
        for key in ids:
            try:
                if key in jd:
                    value = jd.get(key)
                    entry = extract(value)
                    
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
    
    urlgroup = "\n".join(sorted(urls))
    new_issue_url = f"{repo_url}/issues/new?template={category}.yml"
        
    entry = f'''
<details name="{category}">
<summary>{display_name} ({len(urls)} entries)</summary>

{urlgroup}
[➕ Register new {display_name}]({new_issue_url})

</details>
'''

    return entry


def main():
    # Get repository info
    repo_url, owner, repo_name = get_repo_info()
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
    
    with open(OUTFILE, 'w') as outfile:
        outfile.write(f'# Modify existing entries in {repo_name}\n\n')
        outfile.write(f'''The following links will open pre-filled GitHub issues to modify existing entries in [{repo_name}]({repo_url}). 

Expand the relevant category and select the file you are interested in modifying by clicking the hyperlink.

''')
        
        if not all_categories:
            outfile.write('\n*No issue templates found. Create templates in `.github/GEN_ISSUE_TEMPLATE/` to enable this feature.*\n')
        else:
            for category in all_categories:
                print(f"\nProcessing category: {category}")
                entry = process_category(category, repo_url, repo_name)
                if entry:
                    outfile.write(entry)
    
    print(f"\n✅ Output written to {OUTFILE}")


if __name__ == "__main__":
    main()
