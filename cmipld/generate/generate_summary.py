

'''
This file starts the server runs all the files in the generate_scripts repository. 
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
from cmipld.utils.offline import LD_server
from cmipld.utils.checksum import version


def write(location, me, data):
    summary = version(data, me, location.split("/")[-1])

    if os.path.exists(location):
        old = cmipld.utils.io.rjson(location)
        if old['Header']['checksum'] == summary['Header']['checksum']:
            return 'no update - file already exists'

    cmipld.utils.io.wjsn(summary, location)


def run(file):
    if file == __file__:
        return

    cmipld.utils.git.update_summary(f'Executing: {file}')

    try:
        # this = importlib.import_module(os.path.abspath(file))

        spec = importlib.util.spec_from_file_location("module.name", file)
        this = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(this)  # Load the module

        processed = this.run(localhost, whoami, repopath, reponame)
        write(*processed)

    except Exception as e:
        cmipld.utils.git.update_summary(f"Error in {file} : {e}")

    return


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Process a file path.")
    parser.add_argument(
        "dir", type=str, help="Path to the generate scripts directory")
    parser.add_argument("repos", type=json.loads,
                        help="JSON string containing repositories")

    args = parser.parse_args()

    print(f"File path provided: {args.dir}")

    # relpath = __file__.replace('__main__.py', '')
    relpath = args.dir

    repo_url = cmipld.utils.git.url()
    io_url = cmipld.utils.git.url2io(repo_url)

    # branch = cmipld.utils.git.getbranch()
    repopath = cmipld.utils.git.toplevel()
    reponame = cmipld.utils.git.getreponame()

    whoami = cmipld.reverse_mapping()[io_url]

    print('-'*50)
    print(f'Parsing repo: {whoami}')
    print(f'Location: {repo_url}')
    print(f'Github IO link: {io_url}')
    print('-'*50)

    ldpath = cmipld.utils.git.ldpath()

    repos = args.repos

    # {
    #     'https://wcrp-cmip.github.io/WCRP-universe/': 'universal',
    #     # 'https://wcrp-cmip.github.io/MIP-variables/': 'variables',
    #     # 'https://wcrp-cmip.github.io/CMIP6Plus_CVs/': 'cmip6plus'
    # }

    localserver = LD_server(repos=repos.items(), copy=[
                            [ldpath, whoami]], override='y')

    localhost = localserver.start_server(8084)
    cmipld.processor.replace_loader(
        localhost, [list(i) for i in repos.items()])

    files = glob.glob(relpath+'*.py')

    for file in tqdm.tqdm(files):
        run(file)

    localserver.stop_server()

    if __name__ == '__main__':
        main()
