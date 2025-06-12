#!/usr/bin/env python3
"""
Create README files for WCRP universe data directories.
Converts Jupyter notebook functionality to standalone script.
"""

import os
import re
import json
import glob
import sys
import argparse
import numpy as np
from pathlib import Path
import urllib.parse
from collections import defaultdict


parser = argparse.ArgumentParser(description='Create README files for WCRP universe data directories')
parser.add_argument('directory', help='Directory path to process')

try:
    import esgvoc
    from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
except ImportError:
    print("Warning: esgvoc not available. Pydantic models will not be used.")
    DATA_DESCRIPTOR_CLASS_MAPPING = {}

try:
    from cmipld.utils.git import get_path_url, get_repo_url, get_relative_path, url2io
    from cmipld import prefix_url
except ImportError:
    print("Warning: cmipld not available. Git utilities will not be used.")
    def get_path_url(path): return f"https://github.com/WCRP-CMIP/your-repo/tree/main/src-data/{path}"
    def get_repo_url(): return "https://github.com/WCRP-CMIP/your-repo"
    def get_relative_path(path): return f"src-data/{path}"
    def url2io(repo, branch, path): return f"https://wcrp-cmip.github.io/your-repo/{path.replace('src-data/', '')}"
    def prefix_url(url): return url.replace('https://wcrp-cmip.github.io/your-repo/', 'your-prefix:')


# def extract_bullets_with_brackets(html_text):
#     """Extract bullet points with brackets from HTML text."""
#     try:
#         from bs4 import BeautifulSoup
#         soup = BeautifulSoup(html_text, "html.parser")
#         results = {}

#         bullet_pattern = re.compile(r"\s*-\s*(\w+):\s*([^\(]+?)(?:\s*\((.*?)\))?\.")

#         for details in soup.find_all("details"):
#             lines = details.get_text().splitlines()
#             for line in lines:
#                 match = bullet_pattern.match(line)
#                 if match:
#                     symbol, description, bracket_info = match.groups()
#                     results[symbol] = {
#                         "text1": description.strip(),
#                         "text2": bracket_info.strip() if bracket_info else None
#                     }

#         return results
#     except ImportError:
#         print("Warning: BeautifulSoup not available. HTML parsing will be skipped.")
#         return {}


def sort_keys_like_json(keys):
    """
    Sort keys in the same order as JSON files:
    1. id
    2. validation-key
    3. ui-label  
    4. description
    5. All other keys (alphabetically)
    6. @context
    7. type
    """
    priority_keys = ['id', 'validation-key', 'ui-label', 'description']
    end_keys = ['@context', 'type']
    
    sorted_keys = []
    
    # Add priority keys in order
    for key in priority_keys:
        if key in keys:
            sorted_keys.append(key)
    
    # Add remaining keys alphabetically (excluding priority and end keys)
    remaining_keys = [k for k in keys if k not in priority_keys and k not in end_keys]
    sorted_keys.extend(sorted(remaining_keys))
    
    # Add end keys
    for key in end_keys:
        if key in keys:
            sorted_keys.append(key)
    
    return sorted_keys


def bullet_pydantic(pm):
    """Generate bullet points from Pydantic model."""
    if not pm:
        return ""
    
    # Get all field names and sort them
    field_names = list(pm.__pydantic_fields__.keys())
    sorted_fields = sort_keys_like_json(field_names)
    
    keys = ""
    for key in sorted_fields:
        if key in pm.__pydantic_fields__:
            value = pm.__pydantic_fields__[key]
            typename = getattr(value.annotation, '__name__', str(value.annotation))
            description = value.description or '<< No description in pydantic model (see esgvoc) >>'
            keys += f"- **`{key}`** (**{typename}**) \n  {description.rstrip()}\n"
    
    return keys


def bullet_names(keynames):
    """Generate bullet points from key names."""
    sorted_keynames = sort_keys_like_json(keynames)
    
    keys = ""
    for key in sorted_keynames:
        print(f"- **`{key}`**")
        keys += f"- **`{key}`**  \n   [**unknown**]\n  No Pydantic model found.\n"
    
    return keys


def extract_description(readme_content):
    """Extract description from README file content."""
    # Pattern to match the description section
    pattern = r'<section id="description">(.*?)</section>'
    match = re.search(pattern, readme_content, re.DOTALL)
    
    if not match:
        return None
    
    section_content = match.group(1).strip()
    
    # Extract just the description text after "## Description"
    desc_pattern = r'## Description\s*(.*?)(?=\n\n|\Z)'
    desc_match = re.search(desc_pattern, section_content, re.DOTALL)
    
    return desc_match.group(1).strip() if desc_match else None


def extract_external_contexts(context):
    mappings = []
    repos = defaultdict(set)

    inner_context = context["@context"][1] if isinstance(context["@context"], list) else context["@context"]

    for key, value in inner_context.items():
        if key.startswith("@"):
            continue

        ext_context = value.get("@context") if isinstance(value, dict) else None
        key_type = value.get("@type") if isinstance(value, dict) else None

        if ext_context:
            parsed = urllib.parse.urlparse(ext_context)
            path_parts = parsed.path.strip("/").split("/")
            org = path_parts[0] if len(path_parts) > 1 else "unknown"
            repo = path_parts[1] if len(path_parts) > 2 else "unknown"
            path = "/" + "/".join(path_parts[2:]) if len(path_parts) > 2 else parsed.path

            mappings.append({
                "key": key,
                "type": key_type,
                "context_url": ext_context,
                "organization": org,
                "repository": repo,
                "path": path
            })

            repos[(org, repo)].add(path)

    return mappings, repos


def links(ctxloc):

    try:
        jsonld_context = json.load(open(ctxloc, 'r', encoding='utf-8'))
    except FileNotFoundError:
        print(f"Error: JSON-LD context file {ctxloc} not found.")
        return "<section id='links'>\n\n## 🔗 Links\n\nNo context file found!!!</section> \n\n"
    # Generate mappings and breakdowns
    mappings, repo_breakdown = extract_external_contexts(jsonld_context)

    # Build the markdown output
    markdown_output = ['<section id="links">\n']

    # Section: External Contexts and Key Mappings
    markdown_output.append("## External Contexts and Key Mappings\n")
    ctxrp = r'\_context\_'
    for m in mappings:
        markdown_output.append(f"- **{m['key']}** → `@type: {m['type']}`")
        markdown_output.append(f"- - Context: [{m['context_url'].replace('_context_', ctxrp)}]({m['context_url']})")
        markdown_output.append(f"- - Source: `{m['organization']}/{m['repository']}{m['path']}`\n")

    # Section: Organization and Repository Breakdown
    markdown_output.append("\n## Organisation and Repository Breakdown\n")
    for (org, repo), paths in repo_breakdown.items():
        markdown_output.append(f"- **Organisation:** `{org}`")
        markdown_output.append(f"  - Repository: `{repo}`")
        # for path in sorted(paths):
        #     markdown_output.append(f"    - Path: `{name}{path}`")
        markdown_output.append("")  # for spacing

    if len(markdown_output) < 4:
        return 'No external links found. '

    # Print the complete markdown string
    final_markdown = "\n </section>\n\n".join(markdown_output)
    
    return final_markdown


def main():
    """Main function to process directory and create README files."""

    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"Error: Directory {args.directory} does not exist")
        sys.exit(1)
    
    directory_path = args.directory
    
    # Change to the specified directory
    os.chdir(directory_path)
    
    # Get all subdirectories
    folders = glob.glob('*/')
    missing_pydantic = []
    
    for dir_path in folders:
        print(f"Processing {dir_path}")
        name = dir_path.strip('/')
        
        if name == 'project':
            print("Skipping 'project' directory.")
            continue
        
        # Skip if no JSON files
        json_files = [f for f in os.listdir(dir_path) if f.endswith('.json')]
        if not json_files:
            print(f"Skipping {dir_path} as it does not contain any JSON files.")
            continue
        
        # Get the first JSON file alphabetically
        select = sorted(json_files, key=lambda x: x.lower())[0].strip('.json')
        
        # Analyze JSON keys
        try:
            keys_output = os.popen(f"jq -r 'recurse(.[]? // empty) | objects | keys_unsorted[]' {dir_path}*.json | sort | uniq -c | sort -nr").read()
            keynames = [i.split(' ')[-1] for i in keys_output.split('\n') if i.strip()]
            
            if keynames:
                keynumbers = [int(i.split(' ')[-2]) for i in keys_output.split('\n') if i.strip()]
                avg = int(np.median(keynumbers))
                different = [keynames[i] for i, x in enumerate(keynumbers) if x != avg]
                
                if different:
                    print('The following keys are not present in all files:', different)
                    print( '<<add these to an issue>>')
            
        except (ValueError, IndexError) as e:
            print(f"Error processing {dir_path}: {e}")
            continue
        
        # Check for Pydantic model
        dname = dir_path.strip('/').replace('-', '_')
        pydantic = False
        
        if dname in DATA_DESCRIPTOR_CLASS_MAPPING:
            pydantic = dname
        elif dname + '_new' in DATA_DESCRIPTOR_CLASS_MAPPING:
            pydantic = dname + '_new'
        elif dir_path.strip('/') in DATA_DESCRIPTOR_CLASS_MAPPING:
            pydantic = dir_path.strip('/')
        else:
            missing_pydantic.append(dname)
            print(f"------ \n Adding {dname} to DATA_DESCRIPTOR_CLASS_MAPPING")
        
        # Generate bullet points
        if pydantic and DATA_DESCRIPTOR_CLASS_MAPPING:
            bullets = bullet_pydantic(DATA_DESCRIPTOR_CLASS_MAPPING[pydantic])
        else:
            bullets = bullet_names(keynames)
        
        # Generate URLs
        content = get_path_url(dir_path).replace('wolfiex', 'wcrp-cmip')
        repo = get_repo_url().replace('wolfiex', 'wcrp-cmip')
        relpath = get_relative_path(dir_path)
        
        io = relpath.replace('src-data/', url2io(repo, 'main', relpath))
        short = prefix_url(io)
        
        link_content = links(f"{dir_path}_context_")
        
        # Create info section
        info = f'''

<section id="info">


| Item | Reference |
| --- | --- |
| Type | `wrcp:{name}` |
| Pydantic class | [`{pydantic}`](https://github.com/ESGF/esgf-vocab/blob/main/src/esgvoc/api/data_descriptors/{pydantic}.py): {DATA_DESCRIPTOR_CLASS_MAPPING[pydantic].__name__ if pydantic and DATA_DESCRIPTOR_CLASS_MAPPING else ' Not yet implemented'} |
| | |
| JSON-LD | `{short}` |
| Expanded reference link | [{io}]({io}) |
| Developer Repo | [![Open in GitHub](https://img.shields.io/badge/Open-GitHub-blue?logo=github&style=flat-square)]({content}) |


</section>
    '''
        
        # Try to extract existing description from README file
        existing_description = ""
        readme_path = f"{dir_path}README.md"
        if os.path.exists(readme_path):
            with open(readme_path, 'r') as f:
                existing_content = f.read()
            existing_description = extract_description(existing_content)
        
        # Create description section
        description = f'''

<section id="description">

# {name.title().replace('-', ' ').replace(':', ' : ')}  (universal)



## Description
{existing_description or ""}

[View in HTML]({io}/{relpath.replace('src-data/', '')})

</section>

'''
        
        # Create schema section
        schema = f'''
<section id="schema">

## Content Schema

{bullets}




</section>   
'''
        
        # Create usage section
        usage = f'''
<section id="usage">

## Usage

### Online Viewer 
To view a file in a browser use the content link with `.json` appended. 
eg. {content}/{select}.json

### Getting a File. 

A short example of how to integrate the computed ld file into your code. 

```python

import cmipld
cmipld.get( "{short}/{select}")

```

### Framing
Framing is a way we can filter the downloaded data to match what we want. 
```js
frame = {{
            "@context": "{io}/_context_",
            "@type": "wcrp:{name}",
            "keys we want": "",
            "@explicit": True

        }}
        
```

```python

import cmipld
cmipld.frame( "{short}/{select}" , frame)

```
</section>

    '''
        
        # Combine all sections
        readme = f'''{description}{info}{link_content}{schema}{usage}'''
        
        # Write README file
        with open(f'{dir_path}README.md', 'w') as f:
            f.write(readme)
        
        print(f"Created README for {dir_path}")
    
    print(f"\nProcessing complete. Missing pydantic models: {missing_pydantic}")


if __name__ == "__main__":

    main()
