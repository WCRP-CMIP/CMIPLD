from cmipld import Frame
from cmipld.graph import JSONLDGraphProcessor
from typing import Dict, Any, List, Optional


import argparse
import asyncio
import json
from pprint import pprint
from typing import Dict, Any, List, Optional

class EnhancedJSONLDGraphProcessor(JSONLDGraphProcessor):
    """
    An enhanced version of JSONLDGraphProcessor with additional functionality for getting frames.
    """
    def __init__(self,original_instance):
        # super().__init__(existingself)
        self.__dict__.update(original_instance.__dict__)
        self.extended = True
   
    @staticmethod
    def clean_entry(entry: Dict[str, Any], ignore: bool = False) -> Dict[str, Any]:
        """
        Clean an entry by removing certain keys and simplifying the structure.

        Args:
            entry (Dict[str, Any]): The entry to clean.
            ignore (bool): Whether to ignore certain conditions.

        Returns:
            Dict[str, Any]: The cleaned entry.
        """
        nentry = {}
        if '@id' in entry and not ignore:
            return {}
        
        if isinstance(entry, dict):
            for key, value in entry.items():
                if key[0] == '@':
                    continue
           
                if isinstance(value, (str, int, float, bool)) or value is None:
                    nentry[key] = ""  
                elif isinstance(value, dict):
                    if '@id' in value:
                        nentry[key] = {}
                    else:                        
                        cleaned_value = EnhancedJSONLDGraphProcessor.clean_entry(value, False)
                        if cleaned_value:  # Only add non-empty dictionaries
                            nentry[key] = cleaned_value
                            
                elif isinstance(value, list):
                    nentry[key] = []
                       
                else:
                    print('-else', key, value)
        return nentry

    def get_frames(self) -> Dict[str, Dict[str, Any]]:
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
            if not len(data.data):
                continue
            
            print(k, v)
            single = data.data[-1]
            cleaned = self.clean_entry(single, ignore=True)
            cleaned['@type'] = f'mip:{v}'
            cleaned['@context'] = {"@vocab": v, '@base': k}
            cleaned['@embed'] = '@always'
            cleaned['@explicit'] = True 
            frames[k] = cleaned 
        
        self.frames = frames
        return frames

    def link_frames(self, frames: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Link frames based on their relationships.

        Args:
            frames (Dict[str, Dict[str, Any]]): The frames to link.

        Returns:
            List[Dict[str, Any]]: List of failed links.
        """
        fail = []
        for select in self.frames:
            links = self.linked(select, 'source')
            if not links:
                continue
            print(links)
            for link in links:
                try:
                    frames[select][link['predicate']] = self.frames[link['target']]
                except Exception as e:
                    link['error'] = str(e)
                    fail.append(link)
                    continue
        
        print("Failed links:", fail)
        
        
        
    
    def write_frame(self, location: str) -> None:
        """
        Write frames to a file.

        Args:
            location (str): The location to write the frames to.
        """
        with open(location, 'w') as f:
            json.dump(self.frames, f, indent=4)

# async def main():
#     parser = argparse.ArgumentParser(description="Process JSON-LD files and create a graph.")
#     parser.add_argument("--files", nargs="*")
#     parser.add_argument("--output", help="Output file path")
#     args = parser.parse_args()

#     graph = EnhancedJSONLDGraphProcessor()
#     await graph.process_files(args.files)

#     print("Graph keys:", graph.get_graph_keys())
    
#     frames = graph.generate_frames()
#     fail = graph.link_frames(frames)

#     print("Failed links:", fail)
#     print("Missing:", graph.graph['missing'])
#     pprint(frames['cmip6plus:source/id'])
#     graph.walk_graph('cmip6plus:source/id')

#     if args.output:
#         graph.write(location=args.output)

# if __name__ == "__main__":
#     asyncio.run(main())