#!/usr/bin/env python3
"""
Per-File Template Generator

Generates GitHub Issue Form YAML templates from:
- .json: Configuration (name, description, title, labels, field_guidance)
- .csv: Field definitions (type, label, description, etc.)
- .py: Dynamic data (dropdown options from external sources)

All three files must exist for a template to be processed.

Template Substitution:
- Use {key} in field_guidance OR description to substitute values from DATA
- Lists become bullet points
- Dicts have their keys listed as bullet points
- Strings are inserted directly

Substitution Format Specifiers:
- {key} - default bullet list format
- {key:comma} - comma-separated format
- {key:plain} - plain newline-separated format
- {key:bullet} - explicit bullet list format
"""

import csv, os, json
import sys
import yaml
import argparse
from pathlib import Path
import random
import subprocess
import re

# GitHub reserved words that cannot be used in issue template options
GITHUB_RESERVED_WORDS = {'None', 'none', 'True', 'true', 'False', 'false'}

# Default dropdown title for collapsible sections
DEFAULT_DROPDOWN_TITLE = "Detailed Guidance"

# Indentation for YAML literal blocks
YAML_INDENT = "        "  # 8 spaces for value content

failed = []


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


def indent_multiline(text, indent=YAML_INDENT):
    """
    Properly indent all lines of a multi-line string for YAML literal blocks.
    
    Args:
        text: The text to indent
        indent: The indentation string to use
    
    Returns:
        Text with all lines properly indented
    """
    if not text:
        return text
    
    # First, normalize any escaped newlines to actual newlines
    text = text.replace('\\n', '\n')
    
    # Split into lines and indent each one
    lines = text.split('\n')
    indented_lines = [indent + line if i > 0 else line for i, line in enumerate(lines)]
    
    return '\n'.join(indented_lines)


def format_data_value(value, format_type='bullet'):
    """
    Format a DATA value for insertion into guidance text.
    
    Args:
        value: The value from DATA (can be list, dict, or string)
        format_type: How to format the output ('bullet', 'comma', 'plain')
    
    Returns:
        Formatted string representation
    """
    if value is None:
        return ''
    
    if isinstance(value, str):
        return value
    
    if isinstance(value, dict):
        # For dicts, list the keys
        items = list(value.keys())
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        return str(value)
    
    if not items:
        return ''
    
    if format_type == 'comma':
        return ', '.join(str(item) for item in items)
    elif format_type == 'plain':
        return '\n'.join(str(item) for item in items)
    else:  # bullet (default)
        return '\n'.join(f'- {item}' for item in items)


def substitute_data_placeholders(text, data):
    """
    Substitute {key} placeholders in text with values from DATA.
    
    Supports format specifiers:
    - {key} - default bullet list format
    - {key:comma} - comma-separated format
    - {key:plain} - plain newline-separated format
    - {key:bullet} - explicit bullet list format
    
    Args:
        text: The text containing {key} placeholders
        data: The DATA dictionary from the Python file
    
    Returns:
        Text with placeholders substituted
    """
    if not text or not data:
        return text
    
    # Pattern matches {key} or {key:format}
    pattern = r'\{(\w+)(?::(\w+))?\}'
    
    def replace_match(match):
        key = match.group(1)
        format_type = match.group(2) or 'bullet'
        
        if key in data:
            return format_data_value(data[key], format_type)
        else:
            # Leave unmatched placeholders as-is (might be intentional)
            return match.group(0)
    
    return re.sub(pattern, replace_match, text)


def load_json_config(json_file):
    """Load configuration from JSON file."""
    with open(json_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_template_data(py_file):
    """Load data from Python file."""
    namespace = {}
    with open(py_file, 'r', encoding='utf-8') as f:
        exec(f.read(), namespace)
    
    # For backwards compatibility, also check for TEMPLATE_CONFIG
    # but prefer JSON config
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
    
    final_fields = remaining_fields
    if issue_kind_field:
        final_fields.append(issue_kind_field)
    if collaborators_field:
        final_fields.append(collaborators_field)
    
    return final_fields


def build_description_with_guidance(base_description, field_id, field_type, config, data):
    """
    Build the field description, adding guidance section if available.
    
    For markdown fields: guidance is appended directly
    For other fields: guidance is wrapped in a collapsible <details> section
    
    DATA substitution is applied to BOTH the base description AND guidance.
    
    Args:
        base_description: The base description from CSV
        field_id: The field identifier
        field_type: The field type (markdown, dropdown, etc.)
        config: The JSON config containing field_guidance and dropdown_title
        data: The DATA dictionary for template substitution
    
    Returns:
        Description string with optional guidance section
    """
    field_guidance = config.get('field_guidance', {})
    dropdown_title = config.get('dropdown_title', DEFAULT_DROPDOWN_TITLE)
    
    # Apply DATA substitution to base description first
    base_description = substitute_data_placeholders(base_description, data)
    
    # Check if there's guidance for this field
    if field_id not in field_guidance:
        return base_description
    
    guidance_content = field_guidance[field_id]
    if not guidance_content:
        return base_description
    
    # Substitute {key} placeholders with DATA values in guidance
    guidance_content = substitute_data_placeholders(guidance_content, data)
    
    # For markdown fields, append guidance directly (no collapsible section)
    if field_type == 'markdown':
        if base_description:
            return f"{base_description}\n\n{guidance_content}"
        else:
            return guidance_content
    
    # For other fields, build the description with collapsible section
    if base_description:
        description = f"{base_description}\n\n<details markdown=\"1\">\n<summary>{dropdown_title}</summary>\n\n{guidance_content}\n\n</details>"
    else:
        description = f"<details markdown=\"1\">\n<summary>{dropdown_title}</summary>\n\n{guidance_content}\n\n</details>"
    
    return description


def generate_field_yaml(field_def, data, config):
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
    
    # Build description with guidance from JSON if available
    # This now also applies DATA substitution to the description
    description = build_description_with_guidance(description, field_id, field_type, config, data)
    
    # Map multi-select to dropdown with multiple attribute
    actual_field_type = 'dropdown' if field_type == 'multi-select' else field_type
    yaml_lines = [f"  - type: {actual_field_type}"]
    
    # Handle markdown differently
    if field_type == 'markdown':
        yaml_lines.append("    attributes:")
        # Also substitute placeholders in markdown descriptions
        description = substitute_data_placeholders(description, data)
        # Properly indent all lines for YAML literal block
        formatted_desc = indent_multiline(description)
        yaml_lines.append("      value: |")
        yaml_lines.append(f"        {formatted_desc}")
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
        # Check if description needs literal block (has newlines or is long)
        has_newlines = '\\n' in description or '\n' in description
        if has_newlines or len(description) > 80:
            # Use literal block for multi-line or long descriptions
            formatted_desc = indent_multiline(description)
            yaml_lines.append("      description: |")
            yaml_lines.append(f"        {formatted_desc}")
        else:
            yaml_lines.append(f"      description: {description}")
    
    # Add placeholder for inputs (also apply DATA substitution)
    if field_type in ['input', 'textarea'] and placeholder:
        placeholder = substitute_data_placeholders(placeholder, data)
        yaml_lines.append(f"      placeholder: \"{placeholder}\"")
    
    # Add options for dropdowns and multi-selects
    if field_type in ['dropdown', 'multi-select']:
        options_available = False
        
        if data_source != 'none' and data_source in data:
            source_data = data[data_source]
            
            # Check if source_data has any options
            if source_data:
                options_available = True
                yaml_lines.append("      options:")
                
                if options_type == 'dict_keys':
                    for key in source_data.keys():
                        safe_key = sanitize_option(key)
                        yaml_lines.append(f"        - \"{safe_key}\"")
                
                elif options_type == 'list':
                    for item in source_data:
                        safe_item = sanitize_option(item)
                        yaml_lines.append(f"        - \"{safe_item}\"")
                
                elif options_type in ['dict_multiple']:
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
                    if field_id != 'issue_kind':
                        yaml_lines.append("        - \"Not specified\"")
                    for item in source_data:
                        safe_item = sanitize_option(item)
                        yaml_lines.append(f"        - \"{safe_item}\"")
        
        # Warning if no options available for dropdown/multi-select
        if not options_available:
            print(f"    ⚠️  WARNING: No options available for dropdown field '{field_id}' (data_source: '{data_source}')")
            # Add a placeholder option to prevent YAML errors
            yaml_lines.append("      options:")
            yaml_lines.append("        - \"No options available\"")
    
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
        # Merge the config defaults into data if needed (e.g. issue category)
        if field_def['field_id'] not in data and field_def['field_id'] in config: 
            data[field_def['field_id']] = config[field_def['field_id']]
            
        field_yaml = generate_field_yaml(field_def, data, config)
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


def check_template_files(template_name, template_dir):
    """
    Check that all required files exist for a template.
    
    Returns:
        tuple: (csv_file, py_file, json_file) if all exist, None otherwise
    """
    csv_file = template_dir / f"{template_name}.csv"
    py_file = template_dir / f"{template_name}.py"
    json_file = template_dir / f"{template_name}.json"
    
    missing = []
    if not csv_file.exists():
        missing.append(f"{template_name}.csv")
    if not py_file.exists():
        missing.append(f"{template_name}.py")
    if not json_file.exists():
        missing.append(f"{template_name}.json")
    
    if missing:
        print(f"  ⚠️  Skipping {template_name}: missing files: {', '.join(missing)}")
        return None
    
    return csv_file, py_file, json_file


def process_template(template_name, csv_file, py_file, json_file, output_dir):
    """Process a single template from its three source files."""
    
    print(f"Processing {template_name}...")
    
    try:
        # Load configuration from JSON (primary source)
        config = load_json_config(json_file)
        
        # Load data from Python file
        py_config, data = load_template_data(py_file)
        
        # For backwards compatibility: if JSON config is missing fields,
        # fall back to Python config
        for key in ['name', 'description', 'title', 'labels']:
            if key not in config and key in py_config:
                config[key] = py_config[key]
        
        if 'name' not in config:
            print(f"    No 'name' found in config")
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
        
        print(f"    ✓ Generated {template_name}.yml")
        return True
        
    except Exception as e:
        print(f"    ✗ Error: {e}")
        import traceback
        traceback.print_exc()
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
    
    print("=" * 60)
    print("Per-File Template Generator")
    print("=" * 60)
    
    script_dir = Path.cwd()
    template_dir = args.template_dir or script_dir / ".github" / "GEN_ISSUE_TEMPLATE" 
    output_dir = args.output_dir or script_dir / ".github" / "ISSUE_TEMPLATE" 

    print(f"Template dir: {template_dir}")
    print(f"Output dir: {output_dir}")

    if not template_dir.exists():
        sys.exit(f"Template directory not found: {template_dir}")
        return False
    
    output_dir.mkdir(exist_ok=True)
    
    # Find all CSV files (primary indicator of a template)
    csv_files = list(template_dir.glob('*.csv'))
    
    if args.template:
        csv_files = [f for f in csv_files if f.stem == args.template]
    
    if not csv_files:
        print("No CSV files found")
        return False
    
    print(f"\nFound {len(csv_files)} template CSV files")
    print("-" * 40)
    
    created = []
    success_count = 0
    skipped_count = 0
    
    for csv_file in csv_files:
        template_name = csv_file.stem
        
        # Check all three files exist
        files = check_template_files(template_name, template_dir)
        if files is None:
            skipped_count += 1
            continue
        
        csv_file, py_file, json_file = files
        
        if process_template(template_name, csv_file, py_file, json_file, output_dir):
            success_count += 1
            created.append(template_name)
    
    print("-" * 40)
    print(f"Results: {success_count} successful, {skipped_count} skipped, {len(csv_files) - success_count - skipped_count} failed")
    
    for i in range(len(failed)):
        print(f"\nFailed YAML {i+1}:\n")
        print(failed[i])
    
    # Generate documentation
    print("\n" + "=" * 60)
    print("Generating documentation...")
    
    try:
        output = subprocess.check_output(["gh", "repo", "view", "--json", "url,name,owner"], text=True)
        data = json.loads(output)
        repo_url = data["url"]
        io_url = f"https://{data['owner']['login']}.github.io/{data['name']}/"
        print(f"Repo URL: {repo_url}")
        print(f"GitHub Pages URL: {io_url}")
    except Exception as e:
        print(f"Warning: Could not get repo info: {e}")
        repo_url = "https://github.com/EXAMPLE/REPO"
    
    contributing = '''

## 1. Submitting New Controlled Vocabularies

The following forms are available for this repository, and can be used to add or modify entries. The complete submission pipeline (if applicable) will be outlined in the section above.

'''
    
    config_file = template_dir / "_config.json"
    if config_file.exists():
        with open(config_file, 'r') as f:
            config_data = json.load(f)
            
        for group_name, v in config_data.get('grouping', {}).items():
            contributing += f"### {group_name}\n\n"
            for t in v:
                template_file = output_dir / f"{t}.yml"
                if template_file.exists():
                    templateurl = f"{repo_url}/issues/new?template={t}.yml"
                    contributing += f"- [{t}]({templateurl})\n"
                    if t in created:
                        created.remove(t)
        
        # Create config.yml for GitHub
        output_file = output_dir / "config.yml"
        yaml_data = {
            "blank_issues_enabled": False,
            "contact_links": config_data.get("links", [])
        }
        with open(output_file, "w", encoding="utf-8") as f:
            yaml.dump(yaml_data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)

    if len(created) > 0:
        contributing += f"### Ungrouped Forms\n\n"
        for t in created:
            templateurl = f"{repo_url}/issues/new?template={t}.yml"
            contributing += f"- [{t}]({templateurl})\n"
    
    issues_file = output_dir / "../issues.md"
    with open(issues_file, 'w', encoding='utf-8') as f:
        f.write(contributing)
    print(f"💾 issues.md written to {issues_file}")
    
    return success_count > 0


# Label management
try:
    existing = subprocess.run(
        ["gh", "label", "list", "--json", "name"],
        capture_output=True,
        text=True
    )
    existing_labels = [l["name"] for l in json.loads(existing.stdout)]
except Exception as e:
    print(f"Note: Could not fetch existing labels: {e}")
    existing_labels = []


def makelabel(config):
    """Create GitHub labels if they don't exist."""
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
            ], capture_output=True)
            print(f"    Created label: {label} with color #{color}")
            existing_labels.append(label)
        except subprocess.CalledProcessError:
            pass


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
