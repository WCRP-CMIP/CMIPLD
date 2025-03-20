# # from . import git 
# from .file_io import CMIPFileUtils,LatestFiles,sync
# from .frame_ld import Frame,get_frame,key_only,key_value,value_only
from .locations import *
from .browse import *

processor = JsonLdProcessor()


def reload(module=None):
    # nowork
    import sys
    if not module: 
        module = sys.modules[__name__]
        
    import importlib
    del sys.modules[module.__name__]
    importlib.invalidate_caches()
    module = importlib.import_module(module.__name__)
    importlib.reload(module)
    print('Reloaded',module)
    


def get(a,kwargs):
    return processor.get(a,**kwargs)


def expand(u):
    return jsonld.expand(resolve_url(u))

def getall(l):
    '''
    Get multiple items
    '''
    assert isinstance(l,list)
    return [expand(a) for a in l]



# getall auto depend. -. is this the same as processor get?




# # for CLI purposes. To develop further

# import argparse,os
# import subprocess



# # import the library

# async def quicklook(graphpath,clean=True):
#     ''' Quickly load the files from a CMIPLD repo using the frame inside. '''
#     import cmipld,json
#     print('----',graphpath)
#     if graphpath[-1] != '/': graphpath += '/'
#     latest = await cmipld.CMIPFileUtils.load(f'{graphpath}graph.jsonld')
#     frame = json.load(open(f'{graphpath}frame.jsonld','r'))
#     print(frame,graphpath)
#     del frame['@context']
#     return cmipld.Frame(latest['@graph'], frame).clean().json if clean else cmipld.Frame(latest['@graph'], frame).json

# # await quicklook(['JSONLD/organisations/institutions/graph.jsonld'])






# def run_bash_script(script_name):
#     script_path = os.path.join(os.path.dirname(__file__), 'scripts', script_name)
#     try:
#         result = subprocess.run(['bash', script_path], check=True, capture_output=True, text=True)
#         print(result.stdout)
#     except subprocess.CalledProcessError as e:
#         print(f"Error running script: {e}")
#         print(e.stderr)

# def main():
#     parser = argparse.ArgumentParser(description="CMIP Utilities")
#     parser.add_argument('--run-script', help="Run a bash script from the scripts directory")
#     args = parser.parse_args()

#     if args.run_script:
#         run_bash_script(args.run_script)
#     else:
#         parser.print_help()

# if __name__ == "__main__":
#     main()