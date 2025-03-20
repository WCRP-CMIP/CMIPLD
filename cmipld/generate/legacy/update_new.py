"""
CMIP6Plus JSON-LD File Extractor and Organizer

This script traverses through a directory structure, processes JSON-LD files, and organizes
them into graph, context, and version categories. It supports parallel execution for faster
processing and allows exclusion of specific directories and files.

Key Features:
- Parallel file reading using ThreadPoolExecutor
- Customizable file and directory exclusion
- Generation of graph and version data
- Minified JSON output for efficient storage
- Base directory specification
- JSON-LD conformance testing
- Override flag to process all non-skipped repos

Dependencies:
- All libraries are from Python's standard library, except:
- pyld: For JSON-LD conformance testing

Usage:
python cmip6plus_jsonld_extractor.py [--base-dir DIR] [--exclude-dirs DIR1,DIR2] [--exclude-files FILE1,FILE2] [--override]
"""

import argparse
import concurrent.futures
import json
import mmap
import os
import re
import subprocess
# from  cmipld.locations import rmap, namesplit
from cmipld.utils.git import update_env,get_cmip_repo_info
from cmipld.utils import bprint, errprint
from typing import List, Dict, Any, Tuple

from pyld import jsonld

# Constants
SHORTHAND = ""
DEFAULT_SKIP_FILES = ['schema.jsonld', 'graph.jsonld', ".DS_Store", "create.ipynb", "version.jsonld"]
DEFAULT_SKIP_DIRS = ['JSONLD/archive', 'JSONLD/scripts']

graphfile = './compiled/graph_data.json'

REPO, CVTAG, MIPTAG = get_cmip_repo_info()


def read_json_file_mmap(file: str, directory: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Read a JSON file using memory mapping for efficiency."""
    file_path = os.path.join(directory, file)
    with open(file_path, 'r+b') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            version_data = githistory(file_path, False) 
            return json.loads(mm.read().decode('utf-8')), version_data




def read_all_json_files(directory: str, base_dir: str, typeprefix: str) -> Tuple[str, str]:
    """Read and process all JSON files in a directory."""
    # skipped = [f"{directory}/{f}" for f in DEFAULT_SKIP_FILES]
    try:
        files = [f for f in os.listdir(directory) if f.endswith('.json') and f not in DEFAULT_SKIP_FILES]
        # print(files)
    except FileNotFoundError:
        errprint('<<<   Dir does not exist:', directory)
        return None,None
    
    
    if not os.path.exists(f"{directory}/frame.jsonld"):
        bprint('\t >>>   SKIP ', directory)
        return None, None
    
    try:
        frame = json.load(open(f"{directory}/frame.jsonld", 'r'))
        prefix = frame['@context']['@vocab'].replace('_','-')
        if prefix[-1] != ':':
            prefix += ':'
        context = frame['@context']
        # print('>>>   PASS ', directory)
    except Exception as e:
        errprint('<<<  Error',e,  directory)
        return None, None
    
    
    

    
    # files.remove("frame.json")
    all_data = []
    versioning = []
    
    def add_prefix_to_keys(data, prefix, typeprefix):
        if isinstance(data, dict):
            return {prefix + k if not k.startswith('@') else k: add_prefix_to_keys(v, prefix,typeprefix) for k, v in data.items()}
        elif isinstance(data, list):
            return [add_prefix_to_keys(item, prefix, typeprefix) for item in data]
        else:
            return data

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_file = {executor.submit(read_json_file_mmap, file, directory): file for file in files}

        for future in concurrent.futures.as_completed(future_to_file):
            try:
                data, v = future.result()
                
                data['@type'] = f"{typeprefix}:{data['@type']}"
                all_data.append(data)
                versioning.append(v)
            except Exception as exc:
                errprint(f'File {future_to_file[future]} generated an exception: {exc}')
                
                
    # write prefix to all_data
    # write context to graph 
    # all_data = [{prefix + k if not k.startswith('@') else k: v for k, v in z.items()} for z in all_data]
    
    
    all_data = [add_prefix_to_keys(item, prefix, typeprefix) for item in all_data]
    
    ldroot = directory.removeprefix(base_dir).removeprefix('/./')
    
    
    complete_graph = {
        "@id": 'graph:'+context['@vocab'].replace('_','-'),
            # ldroot.replace('JSONLD/',rmap[namesplit(REPO)]),

        "@type": "mip:graph",
        "@context": context,
        ':url': REPO.removesuffix('JSONLD')+ldroot,
        ":ldroot": ldroot,
        "@graph": all_data,
        ":files": files
    }

    # JSON-LD conformance test
    
    
    try:
        jsonld.expand(complete_graph)
        print(f" \t PASS JSON-LD conformance: {directory}")
    except jsonld.JsonLdError as e:
        errprint(f"<<< FAIL JSON-LD conformance test: {directory}: {e}")
        

    # Write graph and versioning
    gpath = f"{directory}/graph.jsonld"
    json.dump(complete_graph, open(gpath, 'w'),indent=4)  # Minified for efficiency
    vpath = f"{directory}/version.jsonld"
    json.dump(versioning, open(vpath, 'w'),indent=4)  # Minified for efficiency
    
    return gpath, vpath

def githistory(file: str, rstr: bool = True) -> Dict[str, Any] | str:
    """Retrieve Git history information for a given file."""
    cmd = rf"""git log -n 1 --pretty=format:'{{
        "version:date": "%cd",
        "version:commit": {{
            "hash": "%H",
            "message": "%s",
            "author": {{
                "name": "%an",
                "email": "%ae"
            }}
        }}
    }}' --date=iso-strict -- {file}"""
    
    rtn = subprocess.getoutput(cmd).strip()
    ncommits = int(subprocess.getoutput(f'git log --oneline -- "{file}" | wc -l').strip() or 0)

    update = {}
    if rtn:
        try:
            update = json.loads(rtn)
        except json.JSONDecodeError:
            print(f"Error decoding JSON from git log for {file}: {rtn}")

    if rstr:
        return f'{file.ljust(30)} - {update.get("version:date", "Unknown date")}'
    else:
        return {
            "@id": file.replace(f'JSONLD', REPO),
            "@type": "version",
            "version:file": file,
            "version:release": {"mip-cmor-tables": MIPTAG, "cmip6plus": CVTAG},
            "version:previous_updates": ncommits,
            **update,
            "version:data": {"@id": file.replace("JSONLD/", SHORTHAND).removesuffix('.json')}
        }

def get_directories_to_process(base_dir: str, skip_dirs: set, override: bool) -> set:
    """Get the set of directories to process based on Git status or override flag."""
    if override:
        all_dirs = set()
        for root, dirs, _ in os.walk(base_dir):
            for d in dirs:
                if d not in skip_dirs :
                    
                    # full_path = os.path.join(root, d)
                    newd =  root.replace('../../','')+ '/' +   d
                    all_dirs.add(newd.replace('//','/'))
                # if full_path.startswith(base_dir) and not any(full_path.startswith(i) for i in skip_dirs):
                #     all_dirs.add(full_path.removeprefix(base_dir))


        return all_dirs

    cmd = f'git diff --name-only $(git log -1 --pretty=format:%H -- {graphfile})^ HEAD'
    output = subprocess.getoutput(cmd)
    
    if not output:
        # Remove graph and version files from the output
        output = re.sub(r'^JSONLD/.+(?:graph|version)\.json.*\n', "", output, flags=re.MULTILINE)
        
    # Get unique directories that need updating
    return set(re.findall(r'^JSONLD.*(?=/)', output, re.MULTILINE)) - skip_dirs

def main(base_dir: str, exclude_dirs: List[str], exclude_files: List[str], override: bool,matched = False, typeprefix = 'mip') -> None:
    """
    Main function to orchestrate the JSON-LD file processing.

    :param base_dir: Base directory to start from
    :param exclude_dirs: List of directories to exclude
    :param exclude_files: List of files to exclude
    :param override: Flag to process all non-skipped repos
    """
    # skip_files = DEFAULT_SKIP_FILES + exclude_files d
    skip_dirs = set(DEFAULT_SKIP_DIRS + exclude_dirs)



    if not matched:
    # Get directories to process if not supplied already
        matched = get_directories_to_process(base_dir, skip_dirs, override)
    
    print(base_dir, matched)
    if not matched:
        if override:
            print('No directories found in the base directory.')
        else:
            print('EXIT: No new files found! Use --override to process all directories.')
        return
    
    for full_path in matched:
        print(full_path)
        # full_path = os.path.join(base_dir, directory)
        graph_data, _ = read_all_json_files(full_path, base_dir,typeprefix)
        # print(graph_data)
        
        if not graph_data: 
            continue
        # print('<<<', directory)



def init():
    parser = argparse.ArgumentParser(description="Process CMIP6Plus JSON-LD files.")
    parser.add_argument("--base-dir", type=str, default="./JSONLD", help="Base directory to start from")
    parser.add_argument("--exclude-dirs", type=str, help="Comma-separated list of directories to exclude")
    parser.add_argument("--exclude-files", type=str, help="Comma-separated list of files to exclude")
    
    parser.add_argument("--output-dir", type=str, default="", help="where to save output")
    parser.add_argument("--type-prefix", type=str, default="mip", help="the bit before the type-name")
    
    parser.add_argument("--override", action="store_true", help="Process all non-skipped repos, ignoring Git status")
    
    parser.add_argument("--updated", nargs="+", help="If we want to run specific directories")
    
    
    
    args = parser.parse_args()
    
    
    if args.updated:
        args.updated = [ i for i in args.updated ] #if 'JSONLD/' in i]
        if len(args.updated) == 0:
            import sys
            update_env("needs_update",0)
            sys.exit('No directories found in the base directory. Skipping... ')
            return
        else:
            update_env("needs_update",len(args.updated))
        
    print (args)

    base_dir = args.base_dir.rstrip('/')  # Remove trailing slash for consistency
    exclude_dirs = args.exclude_dirs.split(',') if args.exclude_dirs else []
    exclude_files = args.exclude_files.split(',') if args.exclude_files else []

    main(base_dir, exclude_dirs, exclude_files, args.override, args.updated, args.type_prefix)
        
        
if __name__ == "__main__":
    init()