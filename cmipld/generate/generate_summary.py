

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
                            ['/Users/daniel.ellis/WIPwork/WCRP-universe/src-data/', repo.io.replace('CMIP7-CVs','WCRP-universe'), 'universal'],
                            ], override='y')

    localhost = localserver.start_server(8084)
    
    
    
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
