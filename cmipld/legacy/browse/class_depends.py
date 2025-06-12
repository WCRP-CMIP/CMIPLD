from pyld import jsonld
from urllib.parse import urljoin
from .class_processurl import ProcessURL
from typing import Any, Dict, List, Union, Set


class Depends(ProcessURL):

    def extract_dependencies(self, url: str, relative: bool = False, graph=False) -> Set[str]:
        """
        Extract all dependencies (@id references) from a JSON-LD document.

        Args:
            url: URL of the JSON-LD document
            relative: If True, returns relative URLs, if False returns absolute URLs
            graph: Returns the location of the graph object - incompatible with relative

        Returns:
            Set of dependency URLs found in the document
        """
        try:
            # Frame the document to extract all @id references
            # query = self.replace_prefix(url)
            framed = jsonld.frame(
                url, {'@explicit': True}, options={'defaultLoader': self.loader})
            ids = framed.get('@graph', [])

            # Process URLs based on relative flag

            if relative:
                return {item['@id'] for item in ids if '@id' in item}

            elif graph:
                return list(set({urljoin(url, self.graphify(item['@id'])) for item in ids if '@id' in item}))

            else:
                return {urljoin(url, item['@id']) for item in ids if '@id' in item}

        except Exception as e:
            print(f"Error extracting dependencies: {str(e)}")
            return set()

    def depends(self, query, **kwargs):
        '''
        Get all the dependencies of a query.
        relative = True, returns relative URLs, if False returns absolute URLs
        '''
        # if arg in locations, then use that and give that level.
        query = self.resolve_prefix(query)
        return self.extract_dependencies(query, **kwargs)
