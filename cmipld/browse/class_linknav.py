import os 
from .class_depends import Depends

class LinkNav(Depends):
    def find_missing(self,url):
        '''
        Get all the references in an LD object, 
        and check if they exist.
        '''
        from tqdm import tqdm
        from ..utils.urltools import url_exists
        
        links = self.depends(url)
        missing = [link for link in tqdm(links) if not url_exists(link)]
        
        return missing

    @staticmethod
    def graphify(path, file = 'graph.jsonld'):
        return os.path.join(os.path.dirname(path), file)
    
    def contextify(self,path):
        return self.graphify(path, '_context_')
