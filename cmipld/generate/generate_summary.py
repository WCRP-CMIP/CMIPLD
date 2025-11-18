#!/usr/bin/env python3
"""
Generate summary runner with data normalization.

Usage:
    python generate_summary.py <script_directory>
"""

import os
import glob
import importlib.util
import tqdm
import cmipld
from cmipld.utils.git.repo_info import cmip_info
# from cmipld.utils.server_tools.offline import LD_server
from cmipld.utils.checksum import version
from cmipld.utils import io  # explicit import for jr/jw
from p_tqdm import p_map

OUTDIR = ".summaries"
os.makedirs(OUTDIR, exist_ok=True)


def normalize_jsonld_data(data):
    """
    Convert expanded JSON-LD to a simplified key-value format.
    Examples:
        {"@id": "http://example.org/item/123"} → {"id": "123"}
        {"http://example.org/name": [{"@value": "Alice"}]} → {"name": "Alice"}
    """
    if not isinstance(data, dict):
        return data

    normalized = {}
    for key, value in data.items():
        # Convert @id → id (short form)
        if key == "@id":
            normalized["id"] = value.split("/")[-1] if isinstance(value, str) else value
            continue

        # Skip @type entirely
        if key == "@type":
            continue

        # Simplify long URLs to their last path component
        simple_key = key.split("/")[-1] if isinstance(key, str) and key.startswith("http") else key

        # Handle single-item lists and JSON-LD structures
        if isinstance(value, list) and len(value) == 1:
            item = value[0]
            if isinstance(item, dict) and "@value" in item:
                normalized[simple_key] = item["@value"]
            elif isinstance(item, dict) and "@list" in item:
                items = item["@list"]
                if isinstance(items, list):
                    normalized[simple_key] = [
                        i["@value"] if isinstance(i, dict) and "@value" in i else i
                        for i in items
                    ]
                else:
                    normalized[simple_key] = items
            else:
                normalized[simple_key] = item
        else:
            normalized[simple_key] = value

    return normalized


def write(location, me, data):
    
    """Write summary file with version header and checksum."""
    
    summary = version(data, me, os.path.basename(location))

    if os.path.exists(location):
        old = io.jr(location)
        if old.get("Header", {}).get("checksum") == summary.get("Header", {}).get("checksum"):
            print(f"📄 {me}: No update needed (unchanged)")
            return "no update - file already exists"

    io.jw(summary, location)
    print(f"💾 {me}: Written to {location}")


def run_script(script_path, repo_info):
    """Load and run a script with JSON-LD normalization temporarily applied."""
    try:
        spec = importlib.util.spec_from_file_location("module.name", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Monkey-patch cmipld.get to normalize JSON-LD responses
        original_get = cmipld.get

        def normalizing_get(url, **kwargs):
            data = original_get(url, **kwargs)
            if isinstance(data, dict) and "@graph" in data:
                data["@graph"] = [normalize_jsonld_data(item) for item in data["@graph"]]
            return data

        cmipld.get = normalizing_get

        processed = module.run(**repo_info)
        # location, me , data
        
        
     
        if processed and len(processed) == 3:
            # processed[0] = os.path.join(OUTDIR, processed[0])
            # print(processed[0],OUTDIR)
            
            write(*processed)
            print(f"✅ {os.path.basename(script_path)}: Success")
            return True
        else:
            print(f"❌ {os.path.basename(script_path)}: No output")
            return False

    except Exception as e:
        print(f"❌ {os.path.basename(script_path)}: {e}")
        return False

    finally:
        cmipld.get = original_get


def main():
    
    import sys

    if len(sys.argv) != 2:
        print("Usage: generate_summary <script_directory>")
        sys.exit(1)

    script_dir = sys.argv[1]




    print("🔍 Getting repository information...")
    repo = cmip_info()
    # # repo['path'] = f"{repo['path']}/{OUTDIR}"
    # print('aaaaa',repo['path'])

    print("🖥️  Setting up local LD server...")
    location = repo.path
    prefix = repo.whoami
    # localmap = {location, cmipld.mapping[prefix], prefix)]

    # server = LD_server(copy=local, use_ssl=False)


    # # True if NOT running in GitHub Actions
    # if os.getenv("GITHUB_ACTIONS") != "true":
    #     print("Running locally (not on GitHub Actions). Running ld2graph to generate latest data...")
    #     print(f"updating all folders in {server.temp_dir.name}/{prefix}")
    #     for folder in tqdm.tqdm(glob.glob(f"{server.temp_dir.name}/{prefix}/*/")):
    #         os.popen(f"ld2graph {folder}  > /dev/null 2>&1").read()
        
    # else:
    #     print("Running on GitHub Actions")
    
    # import sys
    # print(prefixlocal)
    # sys.error(local)
    # print(local)
    
    cmipld.map_current(prefix)

    try:
        # base_url = server.start_server(port=8081)
        # print(f"✅ LD server started at {base_url}")
        
        

        scripts = [
            s for s in glob.glob(f"{script_dir}/*.py")
            if not os.path.basename(s).startswith("x_")
        ]
        print(f"🚀 Running {len(scripts)} summary scripts...\n")


        # append the output directory only for the write function
        repo['path'] = f"{repo['path']}/{OUTDIR}"
        
        

        
        # go write 
        success = sum(run_script(s, dict(repo)) for s in tqdm.tqdm(scripts))
        
        # success_list = p_map(lambda s: run_script(s, dict(repo)), scripts)
        
        # success = sum(1 for result in success_list if result is True)
        
        
        print(f"\n✅ Summary: {success}/{len(scripts)} scripts successful")

    finally:
        print( "ending..." )
        # server.stop_server()


if __name__ == "__main__":
    main()
