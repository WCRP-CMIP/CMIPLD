
import json
from pyld import jsonld
import jmespath
import re
import os
import pkg_resources


def get_frame(base, file):
    '''Get frame from saved collections'''
    # sanitise path
    path = os.path.normpath(f'{base}/{file}.json')
    # with open(__file__.replace('__init__.py','examples/')+path,'r') as f:
    # print(__name__)
    # this works from the current directory
    with pkg_resources.resource_stream(__name__, f'examples/{path}') as f:
        return json.load(f)


def direct(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AttributeError as e:
            if "object has no attribute 'json_string'" in e.__str__():
                print(
                    '!! Error handling has corrected the error.\n In the future, please ensure that parsing functions are called using "clean(process=[...])" method or between a start and end method.\n For more information consult the documentation.')
                args[0].clean(process=[func.__name__])
                return args[0]

            # print(f"An error occurred in {func.__name__}: {e}")
            # # Handle error, e.g., return a placeholder string
            # return "Error occurred"
    return wrapper


class Frame:
    def __init__(self, source, frame, nograph=True):

        # if isinstance(source, list):
        #     source = {"@context":{},"@graph":source}
        # elif isinstance(source, str):
        #     source = json.loads(source)

        self.source = source
        self.frame = frame

        # "@embed": "@always"

        if "@embed" not in frame:  # make sure each instance is embedded.
            self.frame["@embed"] = "@always"

        if nograph:  # usually used if framing an id directly
            self.data = self.graph_only(jsonld.frame(source, frame))
        else:
            self.data = jsonld.frame(source, frame)

    def __str__(self):
        return json.dumps(self.data, indent=2)

    # we do not need to call this as a function
    @property
    def print(self):
        from pprint import pprint
        pprint(self.data)

    @property
    def json(self):
        return self.data

    # @property

    def clean(self, process=None):

        if not process:
            process = ['rmld', 'rmnull', 'untag', 'flatten']

        self.start

        for function in process:
            self.__getattribute__(function)

        self.end
        return self

    @property
    def filter_empty(self):

        # self.data = {k:v for k,v in self.data.items() if v}
        self.data = [v for v in self.data if v]

        return self

    @property
    def clean_cv(self):
        return self.clean(['rmld', 'missing', 'untag', 'lower', 'flatten'])

    # @staticmethod
    @property
    def start(self):
        self.json_string = json.dumps(self.data, indent=2)
        return self

    # @staticmethod
    @property
    def end(self):
        self.data = json.loads(self.json_string)
        del self.json_string
        return self

    @property
    @direct
    def untag(self):
        self.json_string = re.sub(
            r'"(?!mip:|@)[^@":]*:([^@"]*?)":', r'"\1":', self.json_string)
        return self

    @property
    @direct
    def rmld(self):
        self.json_string = re.sub(
            r'("@[^"]*":\s*".*?"(?:,)?\s*)', '', self.json_string)
        return self

    @property
    @direct
    def rmnull(self):
        self.json_string = re.sub(
            r'[\s]*"(.*?)":\s*null*[,\s]*|[,\s]*"(.*?)":\s*null*[\s]*', '', self.json_string)
        return self

    @property
    @direct
    def rmnoparent(self):
        # Remove key-value pairs where the value is 'no parent'
        self.json_string = re.sub(
            r'[\s]*"(.*?)":\s*"no parent"[,\s]*',  # Pattern to match
            '',  # Replacement (remove the matched part)
            self.json_string
        )
        # Clean up any trailing commas or whitespace
        self.json_string = re.sub(r',\s*(?=[}\]])', '', self.json_string)
        return self

    @property
    @direct
    def flatten(self):
        self.json_string = re.sub(
            r'{\s*"([^"]*?)":\s*"(.+)"\s*}', r'"\2"', self.json_string)
        return self

    @property
    @direct
    def lower(self):
        self.json_string = re.sub(
            r'(?<=")([^"]*?)-(.*?)(?=":)', lambda m: m.group(0).replace('-', '_'), self.json_string)
        return self

    @property
    @direct
    def missing(self):
        self.json_string = re.sub(
            r'\{\s*"@id"\s*:\s*"([^"]+)"\s*\}', r'"Missing Link: \1"', self.json_string)
        return self

    @staticmethod
    def graph_only(json_object):
        return json_object.get('@graph', {})

    # @staticmethod
    # def regex_chain(json_string):
    #     return RegexChain(json_string)

    @staticmethod
    def print_state(json_object):
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

    # @property
    # def rmempty(self):
    #     print(self.data)
    #     self.data = dict([i for i in self.data if i.values()])

    #     return self

    def filterkeys(self, keys, overwrite=False, missing=None):
        # assert not set(keys) - set(self.data)
        output = []
        for d in self.data:
            dummy = {}
            for k in keys:
                dummy[k] = d.get(k, missing)
            output.append(dummy)

        if overwrite:
            self.data = output
            return self
        return output

    def key_value(self, key='name', value=None):
        return key_value(self.data, key, value)

    def key_only(self, key='name', default='missing'):
        return key_only(self.data, key, default)

    def value_only(self, key):
        return value_only(self.data, key)

    # def key_str(self, key,value):
    #     return key_str(self.data,key,value)


####################
# Utility functions
####################

def key_value(data, key='name', value=None):
    return {
        (k := d.pop(key, f'keyNotFound[{key}]')): (d.get(value, f'valueNotFound[{value}]') if value else d)
        for d in data
    }


def value_only(data, key):
    try:
        return sorted(list(set([d.get(key) for d in data if d.get(key)])))
    except TypeError as e:
        return list([d.get(key) for d in data if d.get(key)])


# def key_str(data,key,value):
#     return dict([[d.get(key),d.get(value)] for d in data])

def key_only(data, key='name', default='missing'):
    if isinstance(data[0], str):
        # if single value do not fetch key
        return data
    return sorted(list(set([x.get(key, default) for x in data if x])))
