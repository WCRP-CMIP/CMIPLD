# cmip_utils.py

import requests
import json
from pyld import jsonld
import jmespath
import base64
import asyncio
import re

class RegexChain:
    def __init__(self, json_string):
        self.json_string = json_string

    def untag(self):
        self.json_string = re.sub(r'"(?!mip:|@)[^@":]*:([^@"]*?)":', r'"\1":', self.json_string)
        return self

    def rmld(self):
        self.json_string = re.sub(r'("@[^"]*":\s*".*?"(?:,)?\s*)', '', self.json_string)
        return self

    def rmnull(self):
        self.json_string = re.sub(r'[\s]*"(.*?)":\s*null*[,\s]*|[,\s]*"(.*?)":\s*null*[\s]*', '', self.json_string)
        return self

    def flatten(self):
        self.json_string = re.sub(r'{\s*"([^"]*?)":\s*"(.+)"\s*}', r'"\2"', self.json_string)
        return self

    def execute(self):
        return self.json_string


    @staticmethod
    async def stringify(json_object):
        if isinstance(json_object, str):
            return json_object
        return json.dumps(json_object, indent=2)

    @staticmethod
    async def str2json(json_string):
        if isinstance(json_string, dict):
            return json_string
        return json.loads(json_string)

    @staticmethod
    async def graph_only(json_object):
        return json_object.get('@graph', {})

    @staticmethod
    def regex_chain(json_string):
        return RegexChain(json_string)

    @staticmethod
    async def print_state(json_object):
        print(json_object)
        return json_object

    @staticmethod
    def search(json_object, jmespath_query):
        return jmespath.search(jmespath_query, json_object)

    @staticmethod
    async def validate_jsonld(json_object):
        try:
            expanded = jsonld.expand(json_object)
            return True
        except jsonld.JsonLdError as e:
            print(f"JSON-LD validation error: {e}")
            return False

    @staticmethod
    async def compact_jsonld(json_object, context):
        try:
            compacted = jsonld.compact(json_object, context)
            return compacted
        except jsonld.JsonLdError as e:
            print(f"JSON-LD compaction error: {e}")
            return None

    @staticmethod
    def test():
        return 42
    
    '''
    # usage_example.py

import asyncio
from cmip_utils import CMIPUtils

async def main():
    # List files in a GitHub repository
    files = await CMIPUtils.list_files('owner', 'repo', 'path', 'branch')
    
    # Read a file from GitHub
    content = await CMIPUtils.read_file_gh('owner', 'repo', 'file_path', 'branch')
    
    # Read a local JSON file
    local_json = await CMIPUtils.read_file_fs('local_file.json')
    
    # Write JSON to a file
    CMIPUtils.write_file(local_json, 'output.json')
    
    # Manipulate JSON
    json_str = await CMIPUtils.stringify(local_json)
    
    # Demonstrate regex chaining
    processed_json = CMIPUtils.regex_chain(json_str) \
        .untag() \
        .rmld() \
        .rmnull() \
        .flatten() \
        .execute()
    
    # Convert back to JSON
    final_json = await CMIPUtils.str2json(processed_json)
    
    print("Processed JSON:", final_json)
    
    # Search JSON using JMESPath
    result = CMIPUtils.search(final_json, 'jmespath_query')
    
    # Validate JSON-LD
    is_valid = await CMIPUtils.validate_jsonld(final_json)
    
    # Compact JSON-LD
    context = {"@vocab": "http://schema.org/"}
    compacted = await CMIPUtils.compact_jsonld(final_json, context)
    
    print("Test function result:", CMIPUtils.test())

if __name__ == "__main__":
    asyncio.run(main())
    
    '''