#!/usr/bin/env python3
"""
Per-File Template Generator - Fixed for Select Multiple Fields

Handles select fields properly without value attributes.
"""

import csv,os,json
import sys
import yaml
import argparse
from pathlib import Path
import random
import subprocess

# GitHub reserved words that cannot be used in issue template options
GITHUB_RESERVED_WORDS = {'None', 'none', 'True', 'true', 'False', 'false'}

def sanitize_option(option):
    """Replace GitHub reserved words with safe alternatives."""
    if option in GITHUB_RESERVED_WORDS:
        if option.lower() == 'none':
            return 'no-value'
        elif option.lower() == 'true':
            return 'yes'
        elif option.lower() == 'false':
            return 'no'
        else:
            return f'{option}-value'
    return option

def random_color():
    return f"{random.randint(0, 0xFFFFFF):06X}"

failed = []

def load_template_data(py_file):
    """Load configuration and data from Python file."""
    namespace = {}
    with open(py_file, 'r', encoding='utf-8') as f:
        exec(f.read(), namespace)
    
    config = namespace.get('TEMPLATE_CONFIG', {})
    data = namespace.get('DATA', {})
    return config, data

def load_csv_fields(csv_file):
    """Load field definitions from CSV."""
    fields = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fields.append(row)
    
    fields.sort(key=lambda x: int(x['field_order']))
    
    # Move issue_kind and collaborators to the end (in that order)
    # This ensures consistent placement across all templates
    end_fields = []
    remaining_fields = []
    
    issue_kind_field = None
    collaborators_field = None
    
    for field in fields:
        if field['field_id'] == 'issue_kind':
            issue_kind_field = field
        elif field['field_id'] == 'collaborators':
            collaborators_field = field
        else:
            remaining_fields.append(field)
    
    # Build final list: regular fields, then issue_kind, then collaborators
    final_fields = remaining_fields
    if issue_kind_field:
        final_fields.append(issue_kind_field)
    if collaborators_field:
        final_fields.append(collaborators_field)
    
    return final_fields

def generate_field_yaml(field_def, data):
    """Generate YAML for a single field."""
    
    field_type = field_def['field_type']
    field_id = field_def['field_id']
    label = field_def['label']
    description = field_def['description']
    data_source = field_def['data_source']
    required = field_def['required'].lower() == 'true'
    placeholder = field_def['placeholder']
    options_type = field_def['options_type']
    default_value = field_def['default_value']
    
    # Map multi-select to dropdown with multiple attribute
    actual_field_type = 'dropdown' if field_type == 'multi-select' else field_type
    yaml_lines = [f"  - type: {actual_field_type}"]
    
    # Handle markdown differently
    if field_type == 'markdown':
        yaml_lines.append("    attributes:")
        if '\\n' in description:
            formatted_desc = description.replace('\\n', '\n        ')
            yaml_lines.append("      value: |")
            yaml_lines.append(f"        {formatted_desc}")
        else:
            yaml_lines.append("      value: |")
            yaml_lines.append(f"        {description}")
        return '\n'.join(yaml_lines)
    
    # All fields get an id (including multi-select)
    yaml_lines.append(f"    id: {field_id}")
    
    # For multi-select fields, add multiple attribute
    if field_type == 'multi-select':
        yaml_lines.append("    attributes:")
        yaml_lines.append("      multiple: true")
        yaml_lines.append(f"      label: {label}")
    else:
        # Regular fields
        yaml_lines.append("    attributes:")
        yaml_lines.append(f"      label: {label}")
    
    # Add description if present
    if description:
        if '\\n' in description:
            formatted_desc = description.replace('\\n', '\n        ')
            yaml_lines.append("      description: |")
            yaml_lines.append(f"        {formatted_desc}")
        elif len(description) > 80:
            yaml_lines.append("      description: |")
            yaml_lines.append(f"        {description}")
        else:
            yaml_lines.append(f"      description: {description}")
    
    # Add placeholder for inputs
    if field_type in ['input', 'textarea'] and placeholder:
        yaml_lines.append(f"      placeholder: \"{placeholder}\"")
    
    # Add options for dropdowns and multi-selects
    if field_type in ['dropdown', 'multi-select']:
        yaml_lines.append("      options:")
        
        if data_source != 'none' and data_source in data:
            source_data = data[data_source]
            
            if options_type == 'dict_keys':
                for key in source_data.keys():
                    safe_key = sanitize_option(key)
                    yaml_lines.append(f"        - \"{safe_key}\"")
            
            elif options_type == 'list':
                for item in source_data:
                    safe_item = sanitize_option(item)
                    yaml_lines.append(f"        - \"{safe_item}\"")
            
            elif options_type in ['dict_multiple']:
                # For multi-select, use simple string options (no label needed)
                for key in source_data.keys():
                    safe_key = sanitize_option(key)
                    yaml_lines.append(f"        - \"{safe_key}\"")
            
            elif options_type == 'dict_with_extra':
                for key in source_data.keys():
                    safe_key = sanitize_option(key)
                    yaml_lines.append(f"        - \"{safe_key}\"")
                yaml_lines.append("        - \"Open Source\"")
                yaml_lines.append("        - \"Registration Required\"")
                yaml_lines.append("        - \"Proprietary\"")
            
            elif options_type == 'list_with_na':
                # Don't add "Not specified" for issue_kind - it should only have New/Modify
                if field_id != 'issue_kind':
                    yaml_lines.append("        - \"Not specified\"")
                for item in source_data:
                    safe_item = sanitize_option(item)
                    yaml_lines.append(f"        - \"{safe_item}\"")

    
    # Only add default for dropdown types (not input/textarea)
    if default_value and field_type in ['dropdown', 'multi-select']:
        yaml_lines.append(f"      default: {default_value}")
    
    if required:
        yaml_lines.append("    validations:")
        yaml_lines.append("      required: true")
    
    return '\n'.join(yaml_lines)

def generate_template_yaml(config, fields, data):
    """Generate complete YAML template."""
    
    # Properly format the name and description - quote if contains special chars
    name = config['name']
    if ':' in name or '/' in name:
        name = f'"{name}"'
    
    description = config['description']
    if ':' in description:
        description = f'"{description}"'
    
    yaml_content = f"""name: {name}
description: {description}
title: "{config['title']}"
labels: {config['labels']}
body:
"""
    
    for field_def in fields:
        
        # merge the config defaults into data if needed (e.g. issue category)
        if field_def['field_id'] not in data and field_def['field_id'] in config: 
            data[field_def['field_id']] = config[field_def['field_id']]
            
        field_yaml = generate_field_yaml(field_def, data)
        yaml_content += field_yaml + "\n\n"
    
    return yaml_content.rstrip() + "\n"

def validate_yaml(content):
    """Validate YAML syntax."""
    try:
        parsed = yaml.safe_load(content)
        return isinstance(parsed, dict) and 'name' in parsed and 'body' in parsed
    except Exception as e:
        print(f"    YAML Parse Error: {e}")
        return False

def process_template_pair(template_name, csv_file, py_file, output_dir):
    """Process a single template pair."""
    
    print(f"Processing {template_name}...")
    
    try:
        config, data = load_template_data(py_file)
        if not config:
            print(f"    No TEMPLATE_CONFIG found")
            return False
        
        
        
        
        print(f"    Loaded: {config['name']}")
        makelabel(config)
        
        
        fields = load_csv_fields(csv_file)
        
        print(f"    Fields: {len(fields)}")
        
        yaml_content = generate_template_yaml(config, fields, data)
        
        if not validate_yaml(yaml_content):
            print(f"    Invalid YAML generated")
            failed.append(yaml_content)
            return False
        
        output_file = output_dir / f"{template_name}.yml"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        print(f"    Generated {template_name}.yml at {output_file}")
        return True
        
    except Exception as e:
        print(f"    Error: {e}")
        return False

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate GitHub issue templates')
    parser.add_argument('-t', '--template-dir', type=Path, help='Template directory')
    parser.add_argument('-o', '--output-dir', type=Path, help='Output directory')
    parser.add_argument('--template', type=str, help='Generate specific template')
    parser.add_argument('--no-docs', action='store_false', help='Disable documentation generation')
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_arguments()
    
    print("Per-File Template Generator")
    
    # script_dir = Path(__file__).parent
    
    script_dir = Path.cwd()
    template_dir = args.template_dir or script_dir / ".github" / "GEN_ISSUE_TEMPLATE" 
    output_dir = args.output_dir or script_dir / ".github" / "ISSUE_TEMPLATE" 

    print(f"Template dir: {template_dir}")
    print(f"Output dir: {output_dir}")
    print(script_dir)


    if not template_dir.exists():
        import sys
        sys.exit(f"Template directory not found: {template_dir}")
        return False
    
    output_dir.mkdir(exist_ok=True)
    
    csv_files = list(template_dir.glob('*.csv'))
    
    
    if args.template:
        csv_files = [f for f in csv_files if f.stem == args.template]
    
    if not csv_files:
        print("No CSV files found")
        return False
    
    print(f"Processing {len(csv_files)} templates")
    
    
    created = []
    
    success_count = 0
    for csv_file in csv_files:
        template_name = csv_file.stem
        py_file = template_dir / f"{template_name}.py"
        
        
        
        if py_file.exists():
            if process_template_pair(template_name, csv_file, py_file, output_dir):
                success_count += 1
                
            created.append(template_name)
    
    print(f"Results: {success_count}/{len(csv_files)} successful")
    
    for i in range(len(failed)):
        print(f"\nFailed YAML {i+1}:\n")
        print(failed[i])
        
    
    
    # other functions 
    print('MAKE THIS OPTIONAL')

    import subprocess
    # Get repo info using gh
    output = subprocess.check_output(["gh", "repo", "view", "--json", "url,name,owner"], text=True)
    data = json.loads(output)

    repo_url = data["url"]
    io_url = f"https://{data['owner']['login']}.github.io/{data['name']}/"

    print("Repo URL:", repo_url)
    print("GitHub Pages URL:", io_url)

#     if not args.no_docs:
#         contributing = '''

# ## Contribution Guidelines
# Links to the issues used in submitting new files can be found below

# '''
#     else:


            
        
    contributing = f'''


## 1. Submitting New Controlled Vocabularies

The following forms are available for this repository, and can be used to add or modify entries. The complete submission pipeline (if applicable) will be outlined in the section above.


'''
    
    if os.path.exists(f'{template_dir}/_config.json'):
        with open(f'{template_dir}/_config.json', 'r') as f:
            config_data = json.load(f)
            
        for group_name,v in config_data.get('grouping',{}).items():
            contributing += f"### {group_name}\n\n"
            for t in v:
                template_file = output_dir / f"{t}.yml"
                if template_file.exists():
                    templateurl = f"{repo_url}/issues/new?template={t}.yml"
                    contributing += f"- [{t}]({templateurl})\n"
                    created.remove(t)

        
        # Create config.yml for GitHub
        output_file = Path(output_dir) / "config.yml"
        # Build dictionary for YAML
        yaml_data = {
            "blank_issues_enabled": False,
            "contact_links": config_data.get("links", [])
        }
        # Write YAML file
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(
                yaml_data,
                f,
                sort_keys=False,      # keep order
                default_flow_style=False,  # use block style
                allow_unicode=True
            )
                

    if len(created) > 0:
        contributing += f"### Ungrouped Forms\n\n"

        for t in created:
                templateurl = f"{repo_url}/issues/new?template={t}.yml"
                contributing += f"- [{t}]({templateurl})\n"

    
    with open( output_dir / "../issues.md", 'w', encoding='utf-8') as f:
        f.write(contributing)
        print('💾 issues.md written')
        

        # ##### make links file 
        # with open( output_dir / "../config.yml", 'w', encoding='utf-8') as f:
        #     f.write("blank_issues_enabled: false\n")
        #     f.write("contact_links:\n")
        #     for t in config_data.get('links',[]):
        #         f.write(f"  - name: {t['name']}\n")
        #         f.write(f"    url: {t['url']}\n")
        #         f.write(f"    description: {t['description']}\n")
        
        # import yaml
        # from pathlib import Path


    
    
    # templateurl = f"{repo.url}//issues/new?template={template_name}.yml"
    
    
    
    return success_count > 0

try:
    existing = subprocess.run(
        ["gh", "label", "list", "--json", "name"],
        capture_output=True,
        text=True
    )
    existing_labels = [l["name"] for l in json.loads(existing.stdout)]
except Exception as e:
    print(f"Error fetching existing labels: {e}")
    existing_labels = []

def makelabel(config):

    for label in config.get('labels', []):
        if label in existing_labels:
            continue
        try:
            color = random_color()
            subprocess.run([
                "gh", "label", "create",
                label,
                "--color", color,
                "--description", label
            ])
            print(f"Created label: {label} with color #{color}")
        except subprocess.CalledProcessError:
            pass


if __name__ == '__main__':
    success = main()
    
    # sys.exit(0 if success else 1)
