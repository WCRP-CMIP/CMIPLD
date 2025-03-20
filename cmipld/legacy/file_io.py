# cmip_utils.py
import requests
import json
import base64
import asyncio
import sys,os,re
from .locations import LatestFiles

'''
Use main CMIP class to get data from CMIP JSON-LD files
- stored in GitHub repositories and paths based on keys.
- self merging. 

'''



def ldname(path):
    return re.sub(r'([^/]+)$', lambda m: m.group(1).replace('_', '-').lower(), path)
    



async def gh_read_file(owner, repo, file_path, branch='main'):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={branch}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        content = response.json()['content']
        
        if content == '':
            print(f"[Switching to using gh_read_raw] Empty contents received from API, this might be because file is too big.")
            return await gh_read_raw(owner, repo, file_path, branch)
        else:
            return json.loads(base64.b64decode(content).decode('utf-8'))
    
    except requests.RequestException as e:
        print(f"Error reading file: {e}")
        if '403' in str(e):
            try:
                return await gh_read_raw(owner, repo, file_path, branch)
            except:
                raise AssertionError(e)
        return None
        
        
async def gh_read_raw(owner, repo, file_path, branch='main'):
    url = f"https://github.com/{owner}/{repo}/raw/refs/heads/{branch}/{file_path}"    
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error reading file: {e}")
        return None


class CMIPFileUtils:
    @staticmethod
    async def gh_list_files(owner, repo, path='', branch='main'):
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            files = response.json()
            for file in files:
                print(file['name'])
            return files
        except requests.RequestException as e:
            print(f"Error fetching files: {e}")
            return None



    @staticmethod
    async def read_file_fs(filename):
        try:
            with open(filename, 'r') as file:
                return json.load(file)
        except Exception as e:
            print(f"Error reading file {filename}: {e}")
            return None

    @staticmethod
    async def read_file_url(url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching JSON from {url}: {e}")
            return None
        
    # @staticmethod
    # async def merge_files(promises,):
    #     try:
    #         results = await asyncio.gather(*promises)
    #         return [item for sublist in results for item in sublist]
    #     except Exception as e:
    #         print(f"Error merging files: {e}")
    #         raise
    @staticmethod
    def merge_files(*args):
        return args
        
    # @property
    @staticmethod
    async def load_latest():
        print("Loading latest CMIP6Plus and MIP-CMOR-Tables files...")
        latest = [LatestFiles.mip_cmor_tabes, LatestFiles.cmip6plus]
        
        return sum([await gh_read_file(*f) for f in latest],[])
        
        

    @staticmethod
    def write_file(content, file):
        try:
            with open(file, 'w') as f:
                json.dump(content, f, indent=4)
            print(f"JSON data has been written to {file}")
        except Exception as e:
            print(f"Error writing to file: {e}")
            
            
    @staticmethod
    async def load(lddata:list):
        read = []
        for f in lddata:
            if 'http' in f:
                read.append(await CMIPFileUtils.read_file_url(f))
            elif f in LatestFiles.entries:
                read.append(await gh_read_file(*LatestFiles.entries[f]))
            elif os.path.exists(f):
                read.append(await CMIPFileUtils.read_file_fs(f))
            else:
                sys.exit(f"File {f} not found. Make sure you are supplying a list to the load function.")
                
        if len(read)>1:    
            return sum(read,[])
        else:
            return read[0]
        


def sync(item):
    import asyncio
    # return asyncio.run(item)
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(item)


