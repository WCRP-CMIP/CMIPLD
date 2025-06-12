import json
import sys
import re
import os
import argparse
from typing import Any, Dict, List, Union, Set
from functools import lru_cache
from urllib.parse import urljoin
# from ..utils.urltools import valid_url
from pyld import jsonld
from .interactive import open_jless_with_memory
from ..locations import mapping, matches
from .contexts import get_context, generate_context
from p_tqdm import p_map


# from ..utils

# import Loader
from ..utils.server_tools.loader import Loader
from .class_linknav import LinkNav
# linknav import depends.
# Depends import processurl.

# Loader

class JsonLdProcessor(Loader,LinkNav):
    """
    A class for processing JSON-LD documents with recursive expansion and ID resolution.

    Features:
    - Recursively expands and resolves @id fields containing URLs
    - Handles document caching
    - Supports compact and expanded document formats
    - Maintains context handling
    - Extracts document dependencies
    """






    def _resolve_ids(self,
                     data: Union[Dict, List],
                     compact: bool = True,
                     depth: int = 60
                     ) -> Union[Dict, List]:

        if not depth:
            return data

        if isinstance(data, dict):
            if '@id' in data and not '@type' in data and data['@id'].startswith('http'):

                try:

                    expanded = self.expand_document(
                        data['@id'],
                        compact=compact,
                        is_nested=True,
                        depth=depth
                    )

                except jsonld.JsonLdError:
                    print('\n WARNING missing id: ', data['@id'])
                    expanded = None
                    
                if expanded:

                    if len(data.keys()) - 1:
                        # we have additional keys
                        id = data['@id']
                        del data['@id']
                        data = jsonld.compact(
                            {**expanded[0], **data}, expanded[0])
                        # print(data.keys())
                        # print(data)

                    else:
                        data = expanded[0]

            return {
                key: self._resolve_ids(value, compact, depth)
                for key, value in data.items()
            }

        elif isinstance(data, list):

            if len(data) > 3 and depth < 2:
                # lets try parallel
                def resolve_id(it):
                    return self._resolve_ids(it, compact, depth)

                # return p_map(resolve_id, data)
                return list(map(resolve_id, data))
            else:
                return [self._resolve_ids(item, compact, depth) for item in data]

        return data

    def get(self, query, **kwargs):
        # query = self.resolve_prefix(query)
        return self.expand_document(query,**kwargs)

    def frame(self, query, frame=None, embed='@always'):
        query = self.resolve_prefix(query)
        if frame is None:
            # use context of the file as a frame
            frame = query
        if '@embed' not in frame:
            frame['@embed'] = embed
        if '@context' not in frame:
            frame['@context'] = mapping
        else:
            frame['@context'] = {**mapping, **frame['@context']}

        return jsonld.frame(query, frame)

    def compact(self, query, ctx=None):

        if isinstance(query, str):
            query = self.resolve_prefix(query)
            if ctx is None:
                print('No context provided, using the context of the file')
                ctx = query

        elif '@context' in query and ctx == None:
            ctx = query['@context']
        elif ctx is None:
            ctx = {}
        return jsonld.compact(query, ctx)

    @lru_cache(maxsize=None)
    def expand_document(self,
                        jsonld_doc: Union[str, Dict],
                        compact: bool = True,
                        # expand_ctx: bool = True,
                        expand_links: bool = True,
                        no_ctx: bool = True,
                        as_json: bool = False,
                        pprint: bool = False,
                        depth: int = 2,
                        is_nested: bool = False) -> List[Dict]:


        expanded = jsonld.expand(jsonld_doc,options={'extractAllScripts': True})
                                #  options={ 'defaultLoader': self.loader}
                                # )
        depth -= 1

        # mainfile context
        processed = []
        for item in expanded:
            print(item.get('@id',item))
            if expand_links:
                processed_item = self._resolve_ids(item, compact, depth).copy()
            else:
                processed_item = item.copy()


            

            if compact:
                # and not is_nested:
                
                # print('\n\n ++++++++++',self.id2ctx(item['@id']),'+++')
                
                processed_item = jsonld.compact(
                    processed_item, self.id2ctx(item['@id']))

            if no_ctx and '@context' in processed_item:
                del processed_item['@context']

            processed.append(processed_item)



        if not no_ctx:
            if isinstance(jsonld_doc, str):
                ctx = get_context(jsonld_doc)
            else:
                ctx = jsonld_doc.get('@context', {})

            for item in expanded:
                if '@context' not in item:
                    item['@context'] = ctx


            # sys.exit('processed_item'+str(processed))
        
        if pprint:
            from pprint import pprint
            pprint(processed)
            
            
        if as_json:
            return json.dumps(processed, indent=4)
        
        return processed

    @staticmethod
    def EmbeddedFrame(url, timeout=5):
        from .class_embedded import EmbeddedFrame as ef
        return ef(url)
