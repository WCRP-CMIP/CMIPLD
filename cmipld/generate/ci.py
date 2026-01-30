#!/usr/bin/env python3
"""
Generate summary runner with data normalization.

Usage:
    python generate_summary.py <script_directory>
"""

import os,json
import glob
import importlib.util
import p_tqdm
import cmipld
from cmipld.utils.git.repo_info import cmip_info
from cmipld.utils.server_tools.offline import LD_server





def check(file):
    expanded = jsonld.expand(file)
    # assert (expanded)<2, "This check is not inten"
    
    results = {}
    
    for entry in expanded:

        values = entry.values()

        ids = set([item['@id'] for elem in values if isinstance(elem, list)
            for item in elem if isinstance(item, dict) and '@id' in item])

        broken = []

        for i in ids: 
            try:
                jsonld.expand(i)
            except Exception as ex:
                # print(f"Broken link: {i} ({ex})")
                broken.append(i)
            
        results[entry.get('@id')] = {'broken_links': broken, 'all_links': ids}
        
    return results


def main():

    print("🖥️  Setting up local LD server...")
    repo = cmip_info()
    location = repo.path
    prefix = repo.prefix
    local = [(location, cmipld.mapping[prefix], prefix)]

    server = LD_server(copy=local, use_ssl=False)

    try:
        server.start_server(port=8081)
    
        directories = glob.glob('*/')
        
        
        def process_directory(directory):
            
            log = check(f"{prefix}:{directory}graph.jsonld")
        
            reverse = {}
            for k,v in log.items():
                for b in v['broken_links']:
                    if b not in reverse:
                        reverse[b] = []
                    reverse[b].append(k)
        
            simplified = cmipld.prefixify(reverse)
            return simplified    
        
        results = p_tqdm.p_map(process_directory, directories)
        




    finally:
        print("🛑 Stopping LD server...")
        server.stop_server()


if __name__ == "__main__":
    main()
