from collections import Counter
from pyld import jsonld
from cmipld import CMIPFileUtils, Frame, locations
from cmipld.utils.classfn import sorted_dict
import re, json, sys, os, copy
from typing import Dict, Any, List, Optional

# Constant for delimiter used in predicate processing
DELIMITER = ' <~~ '

class JSONLDGraphProcessor:
    """
    A class to process JSON-LD files and extract information.

    Attributes:
    - lddata: The loaded JSON-LD data.
    - graph: The processed graph data.
    - frames: Generated frames from the graph's vocabulary.
    - prefix: The repository prefix.
    - repo_root: The root directory of the repository.
    """

    async def make_graph(self, loaditems):
        """Create the graph from loaded JSON-LD data."""
        self.lddata = await CMIPFileUtils.load(loaditems)
        print(f"Loaded {len(self.lddata)} items")

        # Extract IDs for validation
        ids = set(re.findall(r'"@id"\s*:\s*"([^"]+)"', json.dumps(self.lddata)))

        # Convert JSON-LD to RDF triplets
        triplets = jsonld.to_rdf(self.lddata)

        self.nodes = []
        self.links = []
        type_map = {}
        blank_nodes = {}

        # Helper functions for URL processing
        clink = lambda s: '/'.join(s.split('/')[:-1])
        prefix = lambda s: s.split(':')[0]

        # Process triplets to build nodes and links
        for group in triplets.values():
            self._process_group(group, blank_nodes, type_map, clink, prefix)

        self.blank = blank_nodes

        # Post-processing: Add weights and remove duplicates
        self._post_process_nodes_and_links()

        # Finalize graph data
        self.types = {v: clink(k) for k, v in type_map.items()}
        self.vocab = {v: k.replace('mip:', '') for k, v in self.types.items() if 'https' not in v}
        self.graph = {
            "nodes": self.nodes,
            "links": self.links,
            "types": self.types,
            "vocab": self.vocab,
            "missing": list(set(ids) - set(type_map.keys()) - set(triplets.keys()))
        }

        return self

    def _process_group(self, group, blank_nodes, type_map, clink, prefix):
        """Process a group of triplets to build nodes and links."""
        for t in group:
            self._process_blank_nodes(t, blank_nodes)

        for t in group:
            self._process_triplet(t, type_map, clink, prefix)

    def _process_blank_nodes(self, t, blank_nodes):
        """Process blank nodes in triplets."""
        if '_' in t['subject']['value'] and '_' not in t['object']['value'] and ':' in t['object']['value']:
            subject = t['subject']['value']
            if subject in blank_nodes:
                blank_nodes[subject].append([t['object']['value'], t['predicate']['value']])
            else:
                blank_nodes[subject] = [[t['object']['value'], t['predicate']['value']]]

    def _process_triplet(self, t, type_map, clink, prefix):
        """Process individual triplets to create nodes and links."""
        s = str(t)
        if 'literal' not in s:
            if 'http://www.w3.org/1999/02/22-rdf-syntax-ns#type' in s:
                self._add_type_node(t, type_map, clink, prefix)
            else:
                self._add_link(t, clink)

    def _add_type_node(self, t, type_map, clink, prefix):
        """Add a node based on type information."""
        type_map[t['subject']['value']] = t['object']['value']
        node = {
            "id": clink(t['subject']['value']),
            "type": t['object']['value'],
            "origin": prefix(t['subject']['value'])
        }
        if node['origin'] != 'https':
            self.nodes.append(node)

    def _add_link(self, t, clink):
        """Add a link between nodes."""
        try:
            if '_' in t['object']['value']:
                for item in self.blank[t['object']['value']]:
                    self.links.append({
                        "source": clink(t['subject']['value']),
                        "target": clink(item[0]),
                        "predicate": f"{t['predicate']['value']}{DELIMITER}{item[1]}"
                    })
            else:
                self.links.append({
                    "source": clink(t['subject']['value']),
                    "target": clink(t['object']['value']),
                    "predicate": t['predicate']['value']
                })

            # Add additional origin links
            self._add_origin_links(clink(t['subject']['value']))
        except Exception as e:
            # print(f"Exception in _add_link: {e}, triplet: {t}")
            ...

    def _add_origin_links(self, src):
        """Add links representing the directory structure."""
        path = re.split(r'[:/]', src)
        for i in range(1, len(path)):
            self._add_directory_node(path[i-1], path[0])
            self._add_directory_link(path[i-1], path[i])
        
        self._add_directory_node(path[-1], path[0], 'directory-path')
        self._add_directory_link(path[-1], src)

    def _add_directory_node(self, id, origin, type='directory'):
        """Add a node representing a directory."""
        self.nodes.append({"id": id, "type": type, "origin": origin})

    def _add_directory_link(self, source, target):
        """Add a link between directory nodes."""
        self.links.append({"source": source, "target": target, "predicate": '_'})

    def _post_process_nodes_and_links(self):
        """Add weights to nodes and links, remove duplicates."""
        node_weights = Counter(i['id'] for i in self.nodes)
        link_weights = Counter(f"{i['source']} -> {i['target']}" for i in self.links)

        for node in self.nodes:
            node['weight'] = node_weights[node['id']]
        
        for link in self.links:
            link['weight'] = link_weights[f"{link['source']} -> {link['target']}"]

        # Remove duplicates
        self.nodes = list({i['id']: i for i in self.nodes}.values())
        self.links = list({(i['source'], i['target'], i['predicate']): i for i in self.links}.values())

    @property
    def lddata_debug(self):
        """Print the JSON-LD data for debugging."""
        print(json.dumps(self.lddata, indent=2))

    def read_graph(self, location='network.json'):
        """Read the graph from a file."""
        with open(location, 'r') as f:
            self.graph = json.load(f)
        return self

    def write(self, location='network.json', item='graph'):
        """Write the specified item to a file."""
        data = getattr(self, item, {})
        if not data:
            print(f"No {item} to write")
            return

        with open(location, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"{item.capitalize()} written to {location}")

    def linked(self, selection, direction='source'):
        """Get the linked items for a selection."""
        if direction == 'source':
            return [link for link in self.graph['links'] if link['source'] == selection]
        elif direction == 'target':
            return [link for link in self.graph['links'] if link['target'] == selection]
        else:
            return [link for link in self.graph['links'] if link['source'] == selection or link['target'] == selection]

    def walk_graph(self, sid):
        """Recursively walk the graph starting from a given node."""
        links = self.linked(sid, 'source')
        
        if not links:
            return {"@extend": True}
        
        output = {}
        for link in links:
            output[link['predicate']] = self.walk_graph(link['target'])
            
        return output

    def clean_entry(self, entry: Dict[str, Any], ignore: bool = False) -> Dict[str, Any]:
        """
        Clean an entry by removing certain keys and simplifying the structure.

        Args:
            entry (Dict[str, Any]): The entry to clean.
            ignore (bool): Whether to ignore certain conditions.

        Returns:
            Dict[str, Any]: The cleaned entry.
        """
        if '@id' in entry and not ignore:
            return {}
        
        nentry = {}
        for key, value in entry.items():
            if key.startswith('@'):
                continue
           
            if value in ['no parent', 'none']:
                value = {"@id": value}
                
            if isinstance(value, (str, int, float, bool)) or value is None:
                nentry[key] = ""  
            elif isinstance(value, dict):
                if '@id' in value:
                    nentry[key] = {}
                else:                        
                    cleaned_value = self.clean_entry(value, False)
                    if cleaned_value:  # Only add non-empty dictionaries
                        nentry[key] = cleaned_value
            elif isinstance(value, list):
                nentry[key] = {}
            else:
                print(f'Unexpected type for {key}: {type(value)}')
        
        return nentry

    @property
    def generate_frames(self) -> Dict[str, Dict[str, Any]]:
        """
        Generate frames from the graph's vocabulary.

        Returns:
            Dict[str, Dict[str, Any]]: The generated frames.
        """
        frames = {}
        for k, v in self.graph['vocab'].items():
            if 'graph' in v:
                continue
            
            data = Frame(self.lddata, {"@type": f'mip:{v}', "@embed": "@always"})
            if not data.data:
                continue
            
            cleaned = {}
            for i in [0, -1]:
                single = data.data[0]
                dummy_cleaned = self.clean_entry(single, ignore=True)
                cleaned.update(dummy_cleaned)
            
            cleaned.update({
                '@type': f'mip:{v}',
                '@context': {"@vocab": v, '@base': k},
                '@embed': '@always',
                '@explicit': True 
            })
            frames[k] = cleaned 
        
        self.frames = frames
        return frames

    @property
    def link_frames(self) -> List[Dict[str, Any]]:
        """
        Link frames based on their relationships.

        Returns:
            List[Dict[str, Any]]: List of failed links.
        """
        fail = []
        framefreeze = copy.deepcopy(self.frames)
        for select in self.frames:
            links = self.linked(select, 'source')
            if not links:
                continue
            
            for link in links:
                try:
                    if DELIMITER in link['predicate']:
                        # Handle nested keys
                        pred = link['predicate'].split(DELIMITER)
                        if len(pred) > 2:
                            raise ValueError('Too many delimiters on key. Currently hard coded only for two.')
                        
                        self.frames[select][pred[0]][pred[1]] = framefreeze[link['target']]
                    else:
                        self.frames[select][link['predicate']] = framefreeze[link['target']]
                except Exception as e:
                    fail.append({**link, 'error': str(e)})
        
        print("Failed links:")
        for f in fail:
            print(f"- {f}")
        
        self.failed_links = fail
        return self.frames

    def load_frame(self, frame):
        """Load frames from a file."""
        with open(frame, 'r') as f:
            self.frames = json.load(f)
        return self
    
    @property
    def filter_frames(self):
        """Filter frames to only include those in the current repository."""
        self.get_prefix
        self.frames = {k: v for k, v in self.frames.items() if self.prefix in k}    
    
    def update_frames(self, overwrite=True):
        """Update frame files in the repository."""
        self.get_prefix

        for location, content in self.frames.items():
            if self.prefix not in location:
                continue
            
            file = location.replace(self.prefix, f"{self.repo_root}/JSONLD/") + '/frame.jsonld'
            if not os.path.exists(file):
                print(f"Warning: No file found at {file}")
                continue
            
            if overwrite:
                with open(file, 'r') as f:
                    previous = json.load(f)
                
                content = sorted_dict(content)
                if content != previous and content:
                    with open(file, 'w') as f:   
                        json.dump(content, f, indent=4)
                    print(f'Updated frame: {location} ({file})')

        print('All frames updated successfully.')

    @property
    def get_prefix(self):
        """Get the repository prefix and root directory."""
        if hasattr(self, 'prefix'):
            return 
        
        self.repo_root = os.popen('git rev-parse --show-toplevel').read().strip()
        repo_url = os.popen('git config --get remote.origin.url').read().strip().replace('.git', '')

        namesplit = locations.namesplit(repo_url)

        try:
            assert locations.namesplit(self.repo_root)[1] == namesplit[1]
        except AssertionError:
            print('Repositories must be registered within cmipld.locations file. \nThese are:')
            for s in locations.rmap:
                print(s)
            
            sys.exit(f'You tried to submit: {locations.namesplit(self.repo_root)[1]} whilst expected: {namesplit[1]}')

        self.prefix = locations.rmap[namesplit]

if __name__ == "__main__":
    import argparse

    def context():
        parser = argparse.ArgumentParser(description='Uses the graph.json to generate a context for a type.')
        parser.add_argument('type', type=str, help='type you want to check')
        parser.add_argument('graph', type=str, help='The file(s) to use to generate the context network.json')
        args = parser.parse_args()
        
        print(args)