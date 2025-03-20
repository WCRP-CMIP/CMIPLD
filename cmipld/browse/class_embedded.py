import os 
import cmipld
from cmipld import processor
from p_tqdm import p_map
from pyld import jsonld
from .class_depends import Depends
from .contexts import get_context

import signal
# Timeout handler
def handler(signum, frame):
    raise TimeoutError("Function timed out!")
# Set up signal handler for timeout
signal.signal(signal.SIGALRM, handler)


class EmbeddedFrame(Depends):
    def __init__(self,url, timeout = 15):
        self.url = processor.resolve_prefix(url)
        
        self.dependencies = processor.depends(url,graph=True)
        
        self.context_url = processor.contextify(url)
        
        # expand_context here
        self.context = get_context(self.context_url)
        
        self.container = []
        self.me = None
        
        if '@container' in str(self.context):
            print('WARNING: Part of the loaded context contains a "@container" this may mean referenced items become nested in framing.\n Please check output - this is not     corrected for secondary nested items.')
            
            self.dirpath = os.path.dirname(self.url)
            # filter out direct path. 
            
            # index for the corpus item
            self.me = [i for i,u in enumerate(self.dependencies) if self.dirpath in u ] 
            print(self.me,self.dirpath,self.dependencies)
            assert len(self.me) == 1
            self.me = self.me[0]
            
            # get the container items
            self.container = [k for k,v in self.context.items() if '@container' in v ]
                    

        self.urlindex = self.dependencies
        
        
        # if self.corpus takes too long
        signal.alarm(len(self.dependencies)*timeout)
        
        try:
            self.corpus = {'@graph':p_map(jsonld.expand,self.dependencies)}
            
        except TimeoutError:
            print('Extraction took to long', 'extracting files in serial to check for problems.')
            
            self.corpus = {'@graph':[]}
            for i in self.dependencies:
                # if a problem occurs (error) this will tell us which file is responsible. 
                print(f'Loading {i}.')
                self.corpus['@graph'].append(jsonld.expand(i))
                
            print('Serial loading completed sucessfuly. ')
            
        signal.alarm(0)  # Cancel the alarm
        
        
    def frame(self,frame={}):
        if '@context' not in frame:
            frame['@context'] = self.context_url
        if '@embed' not in frame:
            frame['@embed'] = '@always'
        framed = jsonld.frame(self.corpus,frame,options={'embed':'@always','extractAllScripts':True,'expandContest':True})
        
        # multiresult
        if '@graph' in framed:
            framed = framed['@graph']
        # single result
        elif isinstance(framed,dict):
            framed = [framed]
        
        
        # This block of code is iterating over the `framed` data structure and updating its values
        # based on the `container` attribute of the `EmbeddedFrame` class instance.
        ''' 
        When supplying information for framing, additional fields have the same name. This means that all additional information on the fields becoves concatenated. To account for this we overwrite the fields with the optionally provided information. 
        '''
        
        # overwrite results
        if self.container:
            overwrite = dict([[i['id'],i] for i in jsonld.compact(self.corpus['@graph'][self.me],self.context)['@graph']])
            # print(overwrite)
            for id,val in enumerate(framed):

                for cnt in self.container:
                    if cnt not in val: continue
                    item_overwrite = dict([[i['id'],i] for i in overwrite[val.get('id')][cnt]])
                    for setitem in framed[id][cnt]:
                        setitem.update(item_overwrite[setitem.get('id')])



            
        return framed
    
    def iterative_frame(self,frame):
        
        # get referenced ids.
        independant_ids = [f'{self.dirpath}/{i}' for i in jsonld.frame(self.url,{"@explicit":True})['@graph'] if '@type' in i]
        
        framed = jsonld.frame({"@graph":[id]+self.corpus})
        
    
