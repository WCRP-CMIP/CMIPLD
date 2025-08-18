#!/usr/bin/env python3
"""
Setup script for MkDocs with custom links
Helps configure and validate the links file
"""

import argparse
import json
import yaml
import sys
from pathlib import Path

def validate_links_file(file_path):
    """Validate the structure of a links file."""
    if not file_path.exists():
        print(f"❌ Links file {file_path} does not exist")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        if not content:
            print(f"⚠️  Links file {file_path} is empty")
            return True
        
        # Try parsing as YAML first
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            print(f"❌ Invalid YAML format: {e}")
            # Try JSON
            try:
                data = json.loads(content)
                print("✅ Valid JSON format detected")
            except json.JSONDecodeError as json_e:
                print(f"❌ Invalid JSON format: {json_e}")
                return False
        else:
            print("✅ Valid YAML format detected")
        
        # Validate structure
        links = data.get('links', data.get('external_links', []))
        
        if not isinstance(links, list):
            print(f"❌ 'links' should be a list, got {type(links)}")
            return False
        
        # Validate each link
        for i, link in enumerate(links):
            if not isinstance(link, dict):
                print(f"❌ Link {i+1} should be an object, got {type(link)}")
                return False
                
            if 'title' not in link:
                print(f"❌ Link {i+1} missing required 'title' field")
                return False
                
            if 'url' not in link and 'link' not in link:
                print(f"❌ Link {i+1} missing required 'url' or 'link' field")
                return False
        
        print(f"✅ Links file validated successfully ({len(links)} links found)")
        
        # Show structure summary
        categories = {}
        root_links = 0
        
        for link in links:
            category = link.get('category')
            if category:
                if category not in categories:
                    categories[category] = 0
                categories[category] += 1
            else:
                root_links += 1
        
        print(f"📊 Structure: {root_links} root links, {len(categories)} categories")
        for cat, count in categories.items():
            print(f"   - {cat}: {count} links")
        
        return True
        
    except Exception as e:
        print(f"❌ Error validating links file: {e}")
        return False

def create_sample_links_file(file_path, format_type='yaml'):
    """Create a sample links file."""
    
    sample_data = {
        'links': [
            {
                'title': 'Project Website',
                'url': 'https://example.com',
                'description': 'Main project website'
            },
            {
                'title': 'Documentation',
                'url': 'https://docs.example.com',
                'category': 'Resources',
                'description': 'Complete documentation'
            },
            {
                'title': 'API Reference',
                'url': 'https://api.example.com',
                'category': 'Resources',
                'description': 'API documentation'
            },
            {
                'title': 'GitHub Issues',
                'url': 'https://github.com/user/repo/issues',
                'category': 'Development',
                'description': 'Bug reports and feature requests'
            }
        ]
    }
    
    if format_type.lower() == 'json':
        content = json.dumps(sample_data, indent=2)
    else:  # YAML
        content = f"""# Custom Links Configuration
# Add your external links and custom menu items here

{yaml.dump(sample_data, default_flow_style=False, sort_keys=False)}

# Format guidelines:
# - title: Required - Display name for the link
# - url (or link): Required - Target URL  
# - category: Optional - Groups links under subsections
# - description: Optional - Adds a comment to the navigation
"""
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Created sample links file: {file_path}")

def list_links(file_path):
    """List all links from the file in a readable format."""
    if not validate_links_file(file_path):
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()
    
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError:
        data = json.loads(content)
    
    links = data.get('links', data.get('external_links', []))
    
    print(f"\n📋 Links in {file_path}:")
    print("=" * 50)
    
    # Group by category
    categories = {}
    root_links = []
    
    for link in links:
        category = link.get('category')
        if category:
            if category not in categories:
                categories[category] = []
            categories[category].append(link)
        else:
            root_links.append(link)
    
    # Display root links
    if root_links:
        print("\nRoot Links:")
        for link in root_links:
            desc = f" - {link['description']}" if link.get('description') else ""
            url = link.get('url', link.get('link', ''))
            print(f"  • {link['title']}: {url}{desc}")
    
    # Display categorized links
    for category in sorted(categories.keys()):
        print(f"\n{category}:")
        for link in categories[category]:
            desc = f" - {link['description']}" if link.get('description') else ""
            url = link.get('url', link.get('link', ''))
            print(f"  • {link['title']}: {url}{desc}")

def main():
    parser = argparse.ArgumentParser(description='Setup and manage MkDocs custom links')
    parser.add_argument('command', choices=['validate', 'create', 'list'], 
                       help='Command to execute')
    parser.add_argument('--file', '-f', default='docs/links.yml',
                       help='Path to links file (default: docs/links.yml)')
    parser.add_argument('--format', choices=['yaml', 'json'], default='yaml',
                       help='Format for created files (default: yaml)')
    
    args = parser.parse_args()
    
    file_path = Path(args.file)
    
    if args.command == 'validate':
        if validate_links_file(file_path):
            print("✅ Validation passed")
            sys.exit(0)
        else:
            print("❌ Validation failed")
            sys.exit(1)
    
    elif args.command == 'create':
        if file_path.exists():
            response = input(f"File {file_path} already exists. Overwrite? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled")
                sys.exit(0)
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        create_sample_links_file(file_path, args.format)
    
    elif args.command == 'list':
        list_links(file_path)

if __name__ == '__main__':
    main()
