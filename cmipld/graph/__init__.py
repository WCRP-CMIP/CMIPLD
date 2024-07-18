

from collections import Counter
from pyld import jsonld
from cmipld import CMIPFileUtils
import re,json,sys

class JSONLDProcessor:
    """
    A class to process JSON-LD files and extract information.

    Attributes:
    - latest_data: The latest JSON-LD data.
    """
    
    # def __init__(self):
    #     ...

    async def make_graph(self,loaditems):
        """ create the graph. """
        
        self.lddata = await CMIPFileUtils.load(loaditems)

        # print(len(self.lddata))

        # classic id extraction for checks
        ids = set(re.findall(r'"@id"\s*:\s*"([^"]+)"', json.dumps(self.lddata)))

        # get the triplets
        triplets = jsonld.to_rdf(self.lddata)

        # grab all the types and ids
        type_map = {}
        self.nodes = []
        self.links = []

        clink = lambda s: '/'.join(s.split('/')[:-1])
        prefix = lambda s: s.split(':')[0]


        for group in triplets.values():
            for t in group:
                s = str(t)
                if 'literal' not in s and '_:' not in s:
                    if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type' in s:
                        type_map[t['subject']['value']] = t['object']['value']
                        
                        node = dict(id=clink(t['subject']['value']),type=t['object']['value'], origin=prefix(t['subject']['value']))
                        if node['origin']!='https':
                            self.nodes.append(node)
                    else:
                        try:
                            link = dict(source=clink(t['subject']['value']),target=clink(t['object']['value']),predicate=t['predicate']['value'])
                            self.links.append(link)
                            
                            # additional origin links
                            src  = link['source']
                            path = re.split(r'[:/]',src)
                            for i in range(1,len(path)):
                                me = path[i-1]
                                n2 = dict(id=me,type='directory',origin=path[0])
                                self.nodes.append(n2)
                                l2= dict(source=path[i-1],target=path[i],predicate='_')
                                self.links.append(l2)
                            # dont forget the final node. 
                            me = path[i]
                            n2 = dict(id=me,type='directory-path',origin=path[0])
                            self.nodes.append(n2)
                            # link up to original
                            l2= dict(source=path[i],target=src,predicate='_')
                            self.links.append(l2)
                            
                        except:
                            # skips out the blank nodes
                            print(t)
                            ...
                                    
        directories = list(set(triplets.keys()))
        # find missing and problem keys 
        self.missing = list(set(ids) - set(type_map.keys()) - set(directories))
        from collections import Counter

        nodeweights = Counter([i['id'] for i in self.nodes])
        linkweights = Counter([f"{i['source']} -> {i['target']}" for i in self.links])

        for i in self.nodes:
            i['weight'] = nodeweights[i['id']]
            
        for i in self.links: 
            i['weight'] = linkweights[f"{i['source']} -> {i['target']}"]


        self.nodes = list(dict([(i['id'],i) for i in self.nodes]).values())
        self.links = list(dict([((i['source'],i['target'],i['predicate']),i) for i in self.links]).values())



        self.types = dict([[v,clink(k)] for k,v in type_map.items()])


        # since the types are defined by the vocab
        self.vocab = {v: k.replace('mip:','') for k, v in self.types.items() if 'https' not in v}

        self.graph = dict(nodes=self.nodes,links=self.links,types=self.types,vocab=self.vocab, missing = self.missing)
        
    def read_graph(self,location = 'network.json'):
        """ read the graph from a file. """
        self.graph = json.load(open(location,'r'))
        
    def write(self,location = 'network.json'):
        """ write the graph to a file. """
        with open(location,'w') as f:
            json.dump(self.graph,f,indent=2)


    def walk_graph(self,sid):
        links = [link for link in self.graph['links'] if link['source'] == sid]
        if len(links) == 0:
            return {  "@context": {
                "@extend": True
            } }
        
        output = {}
        for link in links:
            output[link['predicate']] = self.walk_graph(link['target'])
            
        return output


    def get_context(self,selection):
    # selection = 'mip:source-id'
        sid = self.graph['types'][selection]
        structure = self.walk_graph(sid)
        return json.dumps({"@context":{"@vocab":selection.replace('mip:',''),**structure}}, indent=2)
            



if __name__ == "__main__":
    import argparse

    def context():
        parser = argparse.ArgumentParser(description='Uses the graph.json to generate a context for a type.')
        parser.add_argument('type', type=str, help='type you want to check')
        parser.add_argument('graph', type=str, help='The file(s) to use to generate the context network.json')
        args = parser.parse_args()
        
        print(args)
        
    