
from typing import Any, Dict, List, Union, Set
from ..utils.urltools import https
from pyld import jsonld

custom_cache = {}


class Loader:

    def __init__(self, tries=3):
        """Initialize the processor with a cached document loader."""
        self.loader = None
        self.set_cache_loader(tries)
        assert self.loader == jsonld.get_document_loader()

    # @lru_cache(maxsize=100)

    def _load_document(self, url: str) -> Dict:
        """
        Load and cache a JSON-LD document from a URL.

        Args:
            url: The URL to fetch the document from

        Returns:
            The loaded document
        """
        return self.loader(url)['document']

    @staticmethod
    def clear_cache():
        global custom_cache
        custom_cache = {}

    def set_cache_loader(self, tries=3):

        default_loader = jsonld.requests_document_loader()

        def cached_loader(url, kwargs={}):
            global custom_cache
            url = https(url)
            # cache hit
            if url in custom_cache:
                return custom_cache[url]

            # cache miss
            for _ in range(tries):
                try:
                    custom_cache[url] = default_loader(url)
                    return custom_cache[url]
                except:
                    pass

            # last time to throw the error

            custom_cache[url] = default_loader(url)
            return custom_cache[url]

        # update jsonld loader
        jsonld.set_document_loader(cached_loader)

        self.loader = jsonld.get_document_loader()

    def replace_loader(self, server_url, replaced=[], tries=3):
        '''
        replaced = [('https://wcrp-cmip.github.io/CF/', 'cf'),]

        '''
        # input('replacing loader, press enter to continue')
        import warnings
        from requests.packages.urllib3.exceptions import InsecureRequestWarning
        warnings.simplefilter('ignore', InsecureRequestWarning)

        assert type(replaced) == list
        self.clear_cache()

        default_loader = jsonld.requests_document_loader(verify=False)

        print('Setting up location forwarding for:')
        for j, i in replaced:
            print(f" -  {j} >>> {server_url}/{i}/ \n")

        def localhost_loader(url, kwargs):
            global custom_cache

            url = https(url)
            if url in custom_cache:
                # input(f'cache hit: {url}')
                return custom_cache[url]

            for j, i in replaced:
                if j in url:
                    url = url.replace(j, f'{server_url}/{i}/')
                    break

            for _ in range(tries):
                try:
                    custom_cache[url] = default_loader(url)
                    return custom_cache[url]
                except:
                    pass
            # last time to throw the error
            custom_cache[url] = default_loader(url)
            return custom_cache[url]

        # update jsonld loader
        jsonld.set_document_loader(localhost_loader)

        # update default cmipld loader
        self.loader = jsonld.get_document_loader()
