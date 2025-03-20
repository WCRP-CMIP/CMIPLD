import glob, re, json, os
from cmipld import reverse_mapping


def main():

    rmap = reverse_mapping()

    repo = os.popen("git remote get-url origin").read().replace('.git','').strip('\n').split('/')[-2:]
    base = f'https://{repo[0].lower()}.github.io/{repo[1]}/'

    prefix = rmap[base]
    
    print(prefix)
    
    

    for dir in glob.glob('./src-data/*/'):
            
        try:
        
            dname = dir.split('/')[-2]
            
            for f in glob.glob(f'{dir}/*.json'):
                data = json.load(open(f))
            
                data = json.load(open(f))

                data['type'] = [f"wcrp:{dname}",prefix]

                json.dump(data,open(f,'w'),indent=4)
        except Exception as e:
            print(dname)
            pass