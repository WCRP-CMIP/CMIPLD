
# python -m cmipld.tests.elements
import cmipld.tests.elements
import cmipld.utils.git as gitutils
from cmipld.utils.git.actions import parse_md,dispatch
import configparser
# from . import activity
import json,sys,os,re


def action():
    issue_body = os.environ.get('ISSUE_BODY')
    print(issue_body)
    conf = parse_md(issue_body)
    print(conf)
    main(conf)




def main(config):
    errors = []

    for section in config.keys():
        try: 
            # data 
            entry = config[section]
            # library
            section = section.replace('-',"_")
            entrylib = getattr(cmipld.tests.elements,section)
            # class + data
            entryclass = getattr(entrylib,section)()
            
            # print(entry)
            
            if not entryclass.create_jsonld(entry,write=True):
                continue
            
            # otherwise write to file and save repo on git. 
        
            # Set up repo
            gitutils.update_issue_title(f"{entryclass.pullname}")
            branch = f'{entrylib.elementtype}-{entryclass.getid}'
            branch = gitutils.prepare_pull(branch)
            
            
            
            # write to file
            json.dump(entryclass.json, open(entryclass.path, 'w') , indent=4)
            

            # update issue status
            now = cmipld.utils.get_datetime()
            gitutils.update_issue(f'Issue updated: {now} \n\nBranch: {branch} \n\n ```json \n {entryclass.jsonstr} \n```',False)
            
            # commit the file. 
            print(f"Committing {entryclass.path}")
            author = os.environ.get('ISSUE_SUBMITTER','cmip-ipo')
            gitutils.commit_one(entryclass.path,author,f"New entry {entryclass.getid} to the {entrylib.elementpath} LD file",branch)
                
                
                
            gitutils.pull_req(branch, author, entryclass.jsonstr, entryclass.pullname)

        except ModuleNotFoundError as e:
            errors.append(f"No such module {section} in cmipld. Please check the congifuration file template.")
            continue
        

        if errors:
            print(errors)  
            

        
    # git add one file. 
    # git commit with user
    # git push 
    
    
    

# conf = '''
# [institution]
#     Acronym = CMIP-IPO
#     Full_Name = CMIP Model Intercomparison Project Office
#     ROR = 000fg4e24
    
#     # only change the item below to "update" if you are submitting a correction. 
#     action = new    
    
# [activity]
#     Name = CMIP
#     Long_Name =  Coupled Model Intercomparison Project
#     URL = https://wcrp-cmip.org
    
#     # only change the item below to "update" if you are submitting a correction. 
#     action = new
    
# [sub-experiment-id]
#     name =  new-sub-experiment
#     description = A sample sub-experiment id
    
#     # only change the item below to "update" if you are submitting a correction. 
#     action = new
# ''' 
