import json
import sys
import os
import re
import argparse
import importlib.util
import subprocess


from cmipld.utils.validate_json import JSONValidator


HANDLER_PATH = '.github/ISSUE_SCRIPT/'
DATA_PATH = './'

# Labels to ignore when determining issue type
IGNORE_LABELS = {'review', 'alpha', 'keep-open', 'delta', 'Review', 'universal', 'universe', 'pull_req', 'Pull_req'}

# Map issue types to output folders (if different from type name)
FOLDER_MAPPING = {
    'institution': 'organisation',
}


def get_issue_from_env():
    """Get issue data from environment variables (default behavior)"""
    return {
        'body': os.environ.get('ISSUE_BODY'),
        "labels_full": os.environ.get('ISSUE_LABELS'),
        'number': os.environ.get('ISSUE_NUMBER'),
        'title': os.environ.get('ISSUE_TITLE'),
        'author': os.environ.get('ISSUE_SUBMITTER')
    }


def get_issue_from_gh(issue_number):
    """Get issue data from GitHub using gh CLI"""
    try:
        result = subprocess.run(
            ['gh', 'issue', 'view', str(issue_number), '--json', 'title,body,author,labels,number'],
            capture_output=True,
            text=True,
            check=True
        )
        
        data = json.loads(result.stdout)
        labels = [label.get('name', '') for label in data.get('labels', [])]
        
        return {
            'body': data.get('body', ''),
            'labels_full': json.dumps(labels),
            'number': str(data.get('number', issue_number)),
            'title': data.get('title', ''),
            'author': data.get('author', {}).get('login', '')
        }
        
    except subprocess.CalledProcessError as e:
        print(f"Error fetching issue {issue_number}: {e.stderr}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing issue data: {e}")
        sys.exit(1)


def get_issue(issue_number=None):
    """Get issue data either from gh CLI or environment variables"""
    if issue_number:
        print(f"Fetching latest issue data for #{issue_number} from GitHub...")
        issue = get_issue_from_gh(issue_number)
        print(f"  ✓ Fetched: {issue['title']}")
        
        # Set environment variables for compatibility
        os.environ['ISSUE_BODY'] = issue['body'] or ''
        os.environ['ISSUE_LABELS'] = issue['labels_full'] or ''
        os.environ['ISSUE_NUMBER'] = issue['number'] or ''
        os.environ['ISSUE_TITLE'] = issue['title'] or ''
        os.environ['ISSUE_SUBMITTER'] = issue['author'] or ''
        
        return issue
    else:
        return get_issue_from_env()


def parse_issue_body(issue_body):
    """Parse issue body extracting ### Header sections"""
    if not issue_body:
        return {}
        
    lines = issue_body.split('\n')
    issue_data = {}
    current_key = None

    for line in lines:
        if line.startswith('### '):
            current_key = line[4:].strip().replace(' ', '_').replace('-', '_').lower()
            issue_data[current_key] = ''
        elif current_key:
            issue_data[current_key] += line.strip() + ' '

    for key in issue_data:
        issue_data[key] = issue_data[key].strip()
        if issue_data[key] == "\"none\"":
            issue_data[key] = issue_data[key].replace("\"none\"", "none")

    return issue_data


def parse_labels(labels_str):
    """Parse labels string and return relevant labels (excluding ignored ones)"""
    if not labels_str:
        return []
    
    if isinstance(labels_str, str):
        try:
            labels = json.loads(labels_str)
        except json.JSONDecodeError:
            labels = [l.strip() for l in labels_str.split(',')]
    else:
        labels = labels_str
    
    return [l for l in labels if l.lower() not in {i.lower() for i in IGNORE_LABELS}]


def get_issue_type_from_labels(labels):
    """Determine the primary issue type from labels"""
    relevant_labels = parse_labels(labels)
    if relevant_labels:
        return relevant_labels[0]
    return None


def clean_id(value):
    """Clean a value to be used as an @id"""
    if not value:
        return ''
    return value.lower().strip().replace(' ', '-').replace('_', '-')


def get_output_folder(issue_type):
    """Get the output folder for a given issue type"""
    folder = FOLDER_MAPPING.get(issue_type, issue_type)
    return os.path.join(DATA_PATH, folder)


def build_type_array(labels, issue_type):
    """Build the @type array from labels"""
    relevant_labels = parse_labels(labels)
    types = []
    for label in relevant_labels:
        types.append(f"wcrp:{label}")
    if not types:
        types.append(f"wcrp:{issue_type}")
    return types


def build_data_from_issue(parsed_issue, issue_type, labels):
    """Build data object from parsed issue content"""
    
    # Get validation key / ID
    validation_key = (parsed_issue.get('validation_key') or 
                      parsed_issue.get('consortium_name') or
                      parsed_issue.get('acronym') or 
                      parsed_issue.get('label') or '')
    
    data_id = clean_id(validation_key)
    
    if not data_id:
        return None, "No validation key or ID found"
    
    # Build base data with JSON-LD fields
    data = {
        "@context": "_context",
        "@id": data_id,
        "@type": build_type_array(labels, issue_type),
    }
    
    # Map common fields
    field_mapping = {
        'ui_label': ['ui_label', 'full_name', 'full_name_of_the_organisation', 'long_label'],
        'description': ['description'],
        'url': ['url', 'activity_webpage_/_citation', 'webpage', 'website'],
    }
    
    for data_field, issue_fields in field_mapping.items():
        for issue_field in issue_fields:
            value = parsed_issue.get(issue_field)
            if value and value.lower() not in {'_no response_', 'none', ''}:
                data[data_field] = value.strip()
                break
    
    # Copy additional fields (excluding known control fields)
    ignore_fields = {'issue_type', 'issue_kind', 'validation_key',
                     'additional_collaborators', 'collaborators', 'consortium_name', 
                     'acronym', 'label', 'long_label', 'full_name_of_the_organisation'}
    
    for key, value in parsed_issue.items():
        if key.lower() not in ignore_fields and key not in data:
            if isinstance(value, str):
                value = value.strip()
                if value and value.lower() not in {'_no response_', 'none', ''}:
                    data[key] = value
    
    return data, None


def write_summary(title, output_path, data, branch_name, author_info, issue_number, dry_run=False):
    """Write summary to GitHub Actions job summary if available"""
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    if not summary_file:
        return
    
    prefix = "[DRY RUN] " if dry_run else ""
    
    summary = f"""## {prefix}Issue Processing Summary

| Field | Value |
|-------|-------|
| **Title** | {title} |
| **Output File** | `{output_path}` |
| **Branch** | `{branch_name}` |
| **Author** | @{author_info['primary']['login']} |
| **Issue** | #{issue_number} |

"""
    
    if author_info['coauthors']:
        coauthors_str = ', '.join(f"@{c['login']}" for c in author_info['coauthors'])
        summary += f"**Co-authors:** {coauthors_str}\n\n"
    
    summary += f"""### Data to be written

```json
{json.dumps(data, indent=2, ensure_ascii=False)}
```
"""
    
    try:
        with open(summary_file, 'a') as f:
            f.write(summary)
    except Exception as e:
        print(f"Warning: Could not write to summary: {e}")


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Process GitHub issues for CMIP-LD repositories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  new_issue                     # Use environment variables (GitHub Actions)
  new_issue --issue 42          # Fetch and process issue #42
  new_issue -i 42 --dry-run     # Show what would be done without making changes
"""
    )
    
    parser.add_argument('-i', '--issue', type=int, metavar='NUMBER',
                        help='Issue number to fetch from GitHub using gh CLI')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be done without making changes')
    
    return parser.parse_args()


def main():
    from cmipld.utils import git
    from cmipld.utils.git import coauthors
    
    args = parse_args()
    dry_run = args.dry_run
    prefix = "[DRY RUN] " if dry_run else ""
    
    # Ensure we're on the src-data branch before making any changes (skip for dry run)
    if not dry_run:
        current_branch = git.getbranch()
        if current_branch != 'src-data':
            sys.exit(f"❌ Error: Must be on 'src-data' branch to write files.\n"
                     f"   Current branch: {current_branch}\n"
                     f"   Please checkout src-data branch first.")
    
    # Get issue data
    issue = get_issue(args.issue)
    parsed_issue = parse_issue_body(issue['body'])
    
    # Determine issue type from labels
    labels = issue.get('labels_full') or os.environ.get('ISSUE_LABELS', '')
    issue_type = get_issue_type_from_labels(labels)
    
    print(f"Issue #{issue.get('number')}: {issue.get('title')}")
    print(f"Author: {issue.get('author')}")
    print(f"Labels: {labels}")
    print(f"Determined issue type: {issue_type}")
    print(f"\nParsed issue content:\n{json.dumps(parsed_issue, indent=4, ensure_ascii=False)}")

    if not issue_type:
        print("\nWarning: No issue type could be determined")
        sys.exit('No issue type selected. Exiting')

    # Check for specific handler script
    script_path = f"{HANDLER_PATH}{issue_type}.py"
    data = None
    
    if os.path.exists(script_path):
        # Use specific handler
        spec = importlib.util.spec_from_file_location(issue_type, script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"\n{prefix}Loaded handler: {script_path}")
        
        if hasattr(module, 'run'):
            result = module.run(parsed_issue, issue, dry_run=dry_run)
            
            if result is None:
                print(f"\n{prefix}Handler returned None - no file will be written")
                return
            elif isinstance(result, tuple):
                data, _ = result  # Ignore handler's output_path, we set it here
            else:
                data = result
    else:
        # Build data directly from parsed issue
        print(f"\n{prefix}No specific handler for '{issue_type}', building data from issue")
        data, error = build_data_from_issue(parsed_issue, issue_type, labels)
        
        if error:
            print(f"\n{prefix}❌ Error: {error}")
            return
    
    if data is None:
        print(f"\n{prefix}No data returned - nothing to write")
        return
    
    # Ensure basic JSON-LD fields are present before validation
    if '@context' not in data:
        data['@context'] = '_context'
    if '@id' not in data and 'id' in data:
        data['@id'] = data.pop('id')
    if '@type' not in data and 'type' in data:
        data['@type'] = data.pop('type')
    
    # Determine output path first (needed for validation)
    output_folder = get_output_folder(issue_type)
    data_id = data.get('@id', clean_id(parsed_issue.get('validation_key', 
                      parsed_issue.get('acronym', 'unknown'))))
    output_path = os.path.join(output_folder, f"{data_id}.json")
    
    # Write initial data to temp file for validation
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    
    # Run JSONValidator to fix and sort the file (always run, not dry_run)
    validator = JSONValidator(output_folder, dry_run=False)
    validator.validate_and_fix_json(output_path)
    
    # Read back the validated/sorted data
    with open(output_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # If there's a handler with an update() function, call it to enrich the data
    script_path = f"{HANDLER_PATH}{issue_type}.py"
    if os.path.exists(script_path):
        spec = importlib.util.spec_from_file_location(issue_type, script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        if hasattr(module, 'update'):
            print(f"{prefix}Running handler update: {script_path}")
            data = module.update(data, parsed_issue, issue, dry_run=dry_run)
            
            # Write updated data back to file
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
                f.write('\n')
    
    # Clean up file if dry run (we created it just to validate)
    if dry_run:
        os.remove(output_path)
        # Remove empty directory if we created it
        try:
            os.rmdir(output_folder)
        except OSError:
            pass  # Directory not empty or doesn't exist
    
    # Build title
    relevant_labels = parse_labels(labels)
    issue_kind = parsed_issue.get('issue_kind', 'new').lower()
    if issue_kind not in ['new', 'modify']:
        issue_kind = 'new'
    issue_kind_cap = issue_kind.capitalize()
    types_joined = ' | '.join([t.capitalize() for t in relevant_labels]) if relevant_labels else issue_type.capitalize()
    validation_key = data.get('validation_key', data.get('@id', 'unknown'))
    title = f"{issue_kind_cap} {types_joined} : {validation_key}"
    
    branch_name = f"{issue_kind}_{issue_type}_{data_id}".replace(' ', '_').lower()
    
    # Parse author and coauthors
    author_login = issue.get('author') or os.environ.get('ISSUE_SUBMITTER', 'unknown')
    collab_string = parsed_issue.get('additional_collaborators', 
                    parsed_issue.get('collaborators', ''))
    
    author_info = coauthors.parse_issue_authors(author_login, collab_string)
    
    # Build commit message
    commit_msg = f"{issue_kind_cap} {issue_type}: {data_id}"
    commit_msg = coauthors.build_commit_message(commit_msg, author_info['coauthor_lines'])
    
    # Display summary
    print(f"\n{'='*60}")
    print(f"{prefix}Processing Summary")
    print(f"{'='*60}")
    print(f"{prefix}Title: {title}")
    print(f"{prefix}Branch: {branch_name}")
    print(f"{prefix}Output file: {output_path}")
    print(f"{prefix}Author: {author_info['primary']['login']}")
    if author_info['coauthors']:
        print(f"{prefix}Co-authors: {', '.join(c['login'] for c in author_info['coauthors'])}")
    print(f"\n{prefix}Data to write:")
    print(json.dumps(data, indent=4, ensure_ascii=False))
    print(f"\n{prefix}Commit message:")
    print(commit_msg)
    print(f"{'='*60}")
    
    # Write to GitHub Actions summary
    write_summary(title, output_path, data, branch_name, author_info, 
                  issue.get('number', 'N/A'), dry_run=dry_run)
    
    if dry_run:
        print(f"\n[DRY RUN] Would perform:")
        print(f"  1. Update issue title to: {title}")
        print(f"  2. Create branch: {branch_name}")
        print(f"  3. Write file: {output_path}")
        print(f"  4. Commit as: {author_info['primary']['login']}")
        if author_info['coauthors']:
            print(f"     With co-authors: {', '.join(c['login'] for c in author_info['coauthors'])}")
        print(f"  5. Create PR targeting src-data, linked to issue #{issue.get('number', 'N/A')}")
        print(f"\n[DRY RUN] No changes made.")
        return
    
    # Perform the actual operations
    print(f"\nUpdating issue title...")
    git.update_issue_title(title)
    
    print(f"Creating branch: {branch_name}")
    git.newbranch(branch_name)
    
    # File already written and validated by JSONValidator above
    print(f"File ready: {output_path}")
    
    print(f"Committing...")
    git.commit_one(output_path, author_info['primary'], comment=commit_msg, branch=branch_name)
    
    print(f"Creating pull request targeting src-data...")
    git.newpull(branch_name, author_info['primary'], json.dumps(data, indent=4, ensure_ascii=False), title, 
                os.environ.get('ISSUE_NUMBER', ''), base_branch='src-data')
    
    print(f"\n✅ Successfully processed: {title}")


if __name__ == '__main__':
    main()
