

import cmipld
import json,re
# from cmipld.tests.jsonld import organisation
# from pydantic import  ValidationError

# from . import upgrade

# repopath = './src-data/organisation/'


def search_ror(query,acronym = None,filter_value=None):
    
    
    from urllib.parse import quote

    ror_template = 'https://api.ror.org/v2/organizations?query={}'
    url = ror_template.format(quote(query, safe=''))
    # ror_template = 'https://api.ror.org/v2/organizations?query={}'
    # url = ror_template.format(query.replace(' ','%20'))
    ror_data = cmipld.utils.read_url(url)['items']
    
    if filter_value:
        ror_data = [item for item in ror_data if re.search(r'\b{}\b'.format(filter_value), json.dumps(item))]
        

        ror_data = [item for item in ror_data if '"country_code": "{}"'.format(filter_value) in  json.dumps(item) or '"country_name": "{}"'.format(filter_value )in  json.dumps(item)]

        if len(ror_data)!=1 and acronym:
            ror_data = [item for item in ror_data if re.search(r'\b{}\b'.format(acronym.replace('_','-')), json.dumps(item))]
            
        if len(ror_data)!=1:
            return query+'_'+filter_value

    return ror_data



def format_institution(ror_data, acronym,mytype='institution'):
    
    # ensure the acronym has no _
    cmip_acronym = acronym.replace('_','-')
    
    if 'names' in ror_data:
        for name in ror_data['names']:
            if 'ror_display' in name.get('types',''):
                ror_data['name'] = name['value']
                break
                
        if ror_data.get('aliases', [])== []:
            ror_data['aliases'] = []
        for name in ror_data['names']:
            if 'alias' in name.get('types',''):
                ror_data['aliases'].append(name['value'])
                    
        if ror_data.get('acronyms', [])== []:
            ror_data['acronyms'] = []
        for name in ror_data['names']:
            if 'acronym' in name.get('types',''):
                ror_data['acronyms'].append(name['value'])
                
        if ror_data.get('labels', [])== []:
            ror_data['labels'] = []
        for name in ror_data['names']:
            if 'label' in name.get('types',''):
                ror_data['labels'].append(name['value'])
            
    
    ror_data =  {
        "@id": f"{cmip_acronym.lower()}",
        "@type": ['wcrp:organisation',f'wcrp:{mytype}','universal'],
        "validation-key": cmip_acronym,
        "ror": ror_data['id'].split('/')[-1],
        "ui-label": ror_data['name'],
        "url": [i['value'] for i in ror_data.get('links', []) ],
        "established": ror_data.get('established'),
        "kind": ror_data.get('types', [])[0] if ror_data.get('types') else None,
        "labels": ror_data.get('labels', []),
        "aliases": ror_data.get('aliases', []),
        "acronyms": ror_data.get('acronyms', []),
        "location": [{
            "@id": f"universal:location/{ror_data['id'].split('/')[-1]}",
            "@type": "wcrp:location",
            **content['geonames_details']} for content in ror_data.get('locations', [])]
        #  can reverse match consortiums or members from here.    
    }
    return ror_data




def get_institution(ror, acronym):

    mytype = 'institution'

    ror_template = 'https://api.ror.org/organizations/{}'

    url = ror_template.format(ror)

    ror_data = cmipld.utils.read_url(url)

    assert ror_data, f"ROR data not found for {ror},{acronym} in {url}. Exiting Now."
    
    ror_data = format_institution(ror_data, acronym,mytype=mytype)
    
    return ror_data

    
# def update(file):
    
#     data = json.load(open(file))
    
#     match data:
#         case {"type":ldtypes} if 'wcrp:institution' in ldtypes:
#             try:
#                 data = get_institution(data['ror'],data['validation-key'])
#                 organisation.institution(**data)
#             except ValidationError as err:
#                 return 'institution',data['ror'],data['validation-key'],err.errors()[0]
                
            
#         case {"type":ldtypes} if 'wcrp:consortium' in ldtypes:
#             errors = []
#             return errors
            
#     with open(file,'w') as f:
#         json.dump(data,f,indent=4) 
    
        
        
#     if __name__ == '__main__':
# #     from p_tqdm import p_map
# #     import glob
    
# #     files = glob.glob(repopath+'*.json')    
#     # run on all files
#     errors = p_map(update,files)
#     errors = [i for i in errors if i]
        
#     if errors: 
#         from rich.console import Console
#         from rich.table import Table
#         from rich.text import Text
#         console = Console()
            
#         console.print(Text("Validation Errors", style="bold red underline"))

#         # Create a table
#         table = Table(show_header=True, header_style="bold white")
        
#         table.add_column("Type", style="bold green")  # Green
#         table.add_column("Item", style="bold blue")  # Blue
#         table.add_column("Warnings", style="red")  # Red for errors (bullet points)


#         for kind,ror,validation_key,err in errors:
#             # print('eee',err)
#             table.add_row(
#                 kind,
#                 f"{ror}: {validation_key}",
#                 f"[{err['loc'][0]}]:\n {err['msg']}"
#             )


#         console.print(table)
            
