'''
Generation script for creating a CV from the CMIP6Plus and MIP tables.

python -m cmipld.cvs.generate

'''
# python -m cmipld.cvs.generate

# Import the library
from cmipld import *
import asyncio,json,os
from collections import OrderedDict
from parse import process
from datetime import datetime


async def main():

    # latest = await sum([mip,cmip6plus],[])
    latest = await CMIPFileUtils.load(['/Users/daniel.ellis/WIPwork/CMIP6Plus_CVs/compiled/graph_data.json','/Users/daniel.ellis/WIPwork/mip-cmor-tables/compiled/graph_data.json'])

    CV = {}
    # OrderedDict()


    ##################################
    ### MIP Entries #####
    ##################################

    # mip entries
    for key in 'source-type frequency realm grid-label nominal-resolution'.split():
        
        # run the frame. 
        frame = get_frame('mip-cmor-tables',key)
        
        # get results using frame
        data = Frame(latest,frame)
        
        # any additional processing?
        print(key)
        add_new = await process('mip-cmor-tables',key,data)
        
        CV[key.replace('-','_')] = add_new
    

    ##################################
    ### CMIP6Plus Core #####
    ##################################
    
        
    frame = get_frame('cmip6plus','descriptors')
    data = Frame(latest,frame,False).clean(['rmld','missing','untag','lower'])
    
    add_new = await process('cmip6plus','descriptors',data,clean=['rmld','missing','untag','lower'])

    
    CV.update(add_new)

    # ##################################
    # ### CMIP6Plus #####
    # ##################################
    # # organisations
    # # native-nominal-resolution
    for key in 'organisations activity-id sub-experiment-id experiment-id source-id'.split():
        
        # run the frame. 
        frame = get_frame('cmip6plus',key)
        # get results using frame
        data = Frame(latest,frame)
        
        add_new = await process('cmip6plus',key,data)

        CV[key.replace('-','_')] = add_new
        
    
    print('concluding')
    ##################################
    ### fix the file #####
    ##################################
    
    CV['version_metadata'] = {
        "file_modified" : datetime.now().date().isoformat(),
        "CV": {
            "version": os.popen('git describe --tags --abbrev=0').read().strip() or 'version tag read from repo running  - currently not in it. ', 
            "git_commit":os.popen('git rev-parse HEAD').read().strip(), 
            "gitbranch" : os.popen('git rev-parse --abbrev-ref HEAD').read().strip() } ,
        "future": 'miptables, checksum, etc'}
    
  
            
    CV = OrderedDict(sorted((k, (v)) for k, v in CV.items()))
    
    # import pprint
    # pprint.pprint(CV)
    # print(CV)
    with open('CV.json','w') as f:
            json.dump(dict(CV = CV),f,indent=4)    
            print('written to ',f.name )    
        
        
        







if __name__ == "__main__":
    asyncio.run(main())