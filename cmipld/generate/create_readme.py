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


def extract_bullets_with_brackets(html_text):
    """Extract bullet points with brackets from HTML text."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_text, "html.parser")
        results = {}

        bullet_pattern = re.compile(r"\s*-\s*(\w+):\s*([^\(]+?)(?:\s*\((.*?)\))?\.")

        for details in soup.find_all("details"):
            lines = details.get_text().splitlines()
            for line in lines:
                match = bullet_pattern.match(line)
                if match:
                    symbol, description, bracket_info = match.groups()
                    results[symbol] = {
                        "text1": description.strip(),
                        "text2": bracket_info.strip() if bracket_info else None
                    }

        return results
    except ImportError:
        print("Warning: BeautifulSoup not available. HTML parsing will be skipped.")
        return {}


def bullet_pydantic(pm):
    """Generate bullet points from Pydantic model."""
    if not pm:
        return ""
    
    keys = ""
    for key, value in pm.__pydantic_fields__.items():
        typename = getattr(value.annotation, '__name__', str(value.annotation))
        description = value.description or '<< No description in pydantic model (see esgvoc) >>'
        keys += f"- **`{key}`** (**{typename}**) \n  {description.rstrip()}\n"
    
    return keys


def bullet_names(keynames):
    """Generate bullet points from key names."""
    keys = ""
    for key in keynames:
        print(f"- **`{key}`**")
        keys += f"- **`{key}`**  \n  ? (**NoType**)\n  No Linked Pydantic Model \n"
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
        
        # Create info section
        info = f'''

<section id="info">


| Item | Reference |
| --- | --- |
| Type | `wrcp:{name}` |
| Pydantic class | [`{pydantic}`](https://github.com/ESGF/esgf-vocab/blob/main/src/esgvoc/api/data_descriptors/{pydantic}.py): {DATA_DESCRIPTOR_CLASS_MAPPING[pydantic].__name__ if pydantic and DATA_DESCRIPTOR_CLASS_MAPPING else ' Not yet implemented'} |
| | |
| JSON-LD | `{short}` |
| Content | [{io}]({io}) |
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
        readme = f'''{description}{info}{schema}{usage}'''
        
        # Write README file
        with open(f'{dir_path}README.md', 'w') as f:
            f.write(readme)
        
        print(f"Created README for {dir_path}")
    
    print(f"\nProcessing complete. Missing pydantic models: {missing_pydantic}")


if __name__ == "__main__":

    main()
