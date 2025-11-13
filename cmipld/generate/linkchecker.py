import cmipld,glob,sys,json,os
from pyld import jsonld
from cmipld.utils.git.repo_info import cmip_info




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


# def check_individual(file):
    


def compact(log):
    reverse = {}
    for k,v in log.items():
        for b in v['broken_links']:
            if b not in reverse:
                reverse[b] = []
            reverse[b].append(k)

    return cmipld.compact_direct_url(str(reverse))



def broken_links_summary(url):
    result = json.loads(compact(check(url)).replace("'", '"'))
    summary = ''
    for k,v in result.items():
        summary += f"#### Broken: {k}\n"
        for ref in v:
            summary += f" - Referenced by: {ref}\n"
        summary += '\n'
    return summary


def main():
    # file = 'cmip7:experiment/graph.json'
    
    summary_file = os.environ.get('GITHUB_STEP_SUMMARY')
    
    summary = open(summary_file, 'a')
    
    prefix = cmip_info()['whoami']
    
    if sys.argv[1] == 'project':
        
        
        
        for file in glob.glob('project/*.json'):
            file = file.split('/')[-1]
            print(f"Checking {file}...")
            try:
                broken = broken_links_summary(f'cmip7:project/{file}')
            except Exception as ex:
                broken = f"#### Error checking file: {file}"
                
            if broken:
                summary.write(broken)
                summary.write('\n\n')
    
    
    else:
        file = f'{prefix}:{sys.argv[1]}/graph.jsonld'
        print(f"Checking {file}...")
        
        try:
            broken = broken_links_summary(file)
        except Exception as ex:
            broken = f"#### Error checking file: {file}\n\n"
            

        if broken:
            summary.write(broken)
            
                
    print("Finished.")
