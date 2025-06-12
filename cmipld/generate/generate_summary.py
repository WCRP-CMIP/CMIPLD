

'''
This file starts the server runs all the files in the generate_scripts repository. 

generate_summary .github/GENERATE_SUMMARY/ '{"https://wcrp-cmip.github.io/WCRP-universe/":"universal"}'



'''

# %%
import cmipld
import importlib
import json
from collections import OrderedDict
import glob
import os
import sys
import re
# from p_tqdm import p_map
import tqdm
import json
import urllib.parse
from collections import defaultdict

from cmipld.utils.server_tools.offline import LD_server
from cmipld.utils.checksum import version
from cmipld.utils.git.repo_info import cmip_info


from cmipld.utils.logging.unique import UniqueLogger,Panel, box
log = UniqueLogger()


def write(location, me, data):
    # print(f'AWriting to {location}',data)
    summary = version(data, me, location.split("/")[-1])

    if os.path.exists(location):
        old = cmipld.utils.io.jr(location)
        if old['Header']['checksum'] == summary['Header']['checksum']:
            return 'no update - file already exists'

    cmipld.utils.io.jw(summary, location)
    log.debug(f'Written to {location}')

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

    jsonld_context = json.load(open(ctxloc, 'r', encoding='utf-8'))
    # Generate mappings and breakdowns
    mappings, repo_breakdown = extract_external_contexts(jsonld_context)

    # Build the markdown output
    markdown_output = []

    # Section: External Contexts and Key Mappings
    markdown_output.append("## 🔑 External Contexts and Key Mappings\n")
    for m in mappings:
        markdown_output.append(f"- **{m['key']}** → `@type: {m['type']}`")
        markdown_output.append(f"  - Context: [{m['context_url']}]({m['context_url']})")
        markdown_output.append(f"  - Source: `{m['organization']}/{m['repository']}{m['path']}`\n")

    # Section: Organization and Repository Breakdown
    markdown_output.append("\n## 🏛️ Organization and Repository Breakdown\n")
    for (org, repo), paths in repo_breakdown.items():
        markdown_output.append(f"- **Organization:** `{org}`")
        markdown_output.append(f"  - Repository: `{repo}`")
        for path in sorted(paths):
            markdown_output.append(f"    - Path: `{path}`")
        markdown_output.append("")  # for spacing

    # Print the complete markdown string
    final_markdown = "\n".join(markdown_output)
    return final_markdown

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Process a file path.")
    parser.add_argument(
        "dir", type=str, help="Path to the generate scripts directory")
    # parser.add_argument("repos", type=json.loads,
    #                     help="JSON string containing repositories")

    args = parser.parse_args()

    log.debug(f"File path provided: {args.dir}")

    # relpath = __file__.replace('__main__.py', '')
    relpath = args.dir



    repo = cmip_info()

    ldpath = cmipld.utils.io.ldpath() 



    print('We should read all rep dependencies and pre-load them here.')

    localserver = LD_server( copy=[
                            [ldpath, repo.io, repo.whoami],
                            # ['/Users/daniel.ellis/WIPwork/WCRP-universe/src-data/', repo.io.replace('CMIP7-CVs','WCRP-universe'), 'universal'],
                            ], override='y')

    localhost = localserver.start_server()
    
    
    
    # input('wait')
    
    # cmipld.processor.replace_loader(
    #     localhost,[[cmipld.mapping[whoami], whoami]],
    #     )
        # [list(i) for i in repos.items()])
    # print(cmipld.processor.loader)
    # input('wait')

    files = glob.glob(relpath+'*.py')
    
    
    def run(file):
        if file == __file__:
            return

        cmipld.utils.git.update_summary(f'Executing: {file}')

        try:
            # this = importlib.import_module(os.path.abspath(file))
            log.print(
                Panel.fit(
                    f"Starting to run {file.split('/')[-1].replace('.py','')}",
                    box=box.ROUNDED,
                    padding=(1, 2),
                    title=f"{file}",
                    border_style="bright_blue",
                ),
                justify="center",
            )
        
            
            spec = importlib.util.spec_from_file_location("module.name", file)
            this = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(this)  # Load the module

            processed = this.run(**repo)
            
            if len(processed) == 3:
                write(*processed)

        except Exception as e:
            cmipld.utils.git.update_summary(f"Error in {file} : {e}")

        return

        
    # for each file run the function
    for file in tqdm.tqdm(files):
        
        if os.path.basename(file).lower().startswith('x_'):
            # skip files that start with x
            continue
        run(file)

    localserver.stop_server()





# %%
