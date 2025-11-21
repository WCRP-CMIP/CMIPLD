
import subprocess
import yaml
import glob,os,json
from urllib.parse import urlencode
from typing import OrderedDict
import cmipld
from tqdm import tqdm

def extract(val):
    ''' Extract the relevant value from a field '''
    if isinstance(val, list):
        return [extract(v) for v in val]
    if isinstance(val, dict):
        val = next(iter(val.values()))
        print(val.get('validation_key'))
        return val.get('validation_key', val.get('@id'))
    return val



def print_red(*args, sep=' ', end='\n', flush=False):
    """Print text in red (ANSI) in Jupyter or terminal output."""
    RED = '\033[31m'
    RESET = '\033[0m'
    print(RED + sep.join(map(str, args)) + RESET, end=end, flush=flush)

OUTFILE = '.github/modifications.md'


subprocess.run(
        ["git", "fetch", "origin"],
        capture_output=True,
        text=True,
        check=True  # Raises exception on error
    )



def process_folder(f):

    '''
    YAML ISSUE TEMPLATE FORMAT
    '''

    # get yaml 
    yresult = subprocess.run(
        ["git", "show", "refs/remotes/origin/main:.github/ISSUE_TEMPLATE/experiment.yml"],
        capture_output=True,
        text=True,
        check=True  # Raises exception on error
    )
    # Parse YAML
    dyaml = yaml.safe_load(yresult.stdout)


    # get the field id and type for the issue entries. 
    ids = set([item['id'] for item in dyaml['body'] if 'id' in item])
    dropdown = []
    multi=[]

    for entry in dyaml['body']:
        if entry['type'] == 'dropdown':
            dropdown.append(entry['id'])
            if entry['attributes'].get('multiple',False) :
                multi.append(entry['id'])

    '''
    Parse files
    '''


    # FUCNTION GLOBALS 
    urls = []

    # get all json files in the folder
    for myfile in tqdm(glob.glob(f'{f}/*.json')):
        print(f"Processing file: {entry}")
        jd = cmipld.get(myfile,depth=2)

        match = OrderedDict()
        
        match['template'] = f'{f}.yml'
        
        match['title'] = f"Modify: {f.title()}: {jd.get('validation_key',jd.get('@id',f'NO ID NO ID NO ID ({myfile})'))}"
        match['issue_kind'] = '"Modify"'
        
        

        for key in ids:
            try:
                if key in jd:
                    value = jd.get(key)
                    entry = extract(value)
                    
                    if key in multi:
                        if isinstance(entry, str):
                            entry = f'"{entry}"'
                        else:
                            entry = ','.join([f'"{e}"' for e in list(entry)])
                    elif key in dropdown:
                        entry = f'"{entry}"'
                    elif isinstance(entry, list): 
                        # not sure when this will happen, but just in case
                        entry = ', '.join(entry)
                    
                    match[key] = entry
            except Exception as ex:
                print_red(f"Error processing {myfile} [{key}]: {ex}")
                continue


        query_string = 'https://github.com/WCRP-CMIP/CMIP7-CVs/issues/new?' + urlencode(match)
        print(query_string)
        
        mdlink = "- [" + jd.get('validation_key',jd['@id']) + "](" + query_string + ")\n"
        print(mdlink)
        
        urls.append(mdlink)
        
    urlgroup = "\n".join(sorted(urls) )
        
    entry = f'''
<details name={f}>
<summary>{f.capitalize()}</summary>

{urlgroup}
</details>
    '''

    return entry






def main():
    # get the folders
    
    with open(OUTFILE,'w') as outfile:
        outfile.write('# Modify existing:\n\n')
        outfile.write('''
The following links will open pre-filled GitHub issues to modify existing entries in the CMIP7-CVs. Please expand your relevant category and select the file you are interested in modifying by clicking the hyperlink.
        ''')
        
        folders = glob.glob('*/')

        for f in folders:   
            f = f.strip('/')
            if f in ['project','cmor','content_summaries']:
                continue
            
            entry = process_folder(f)
            outfile.write(entry)
        
        
        