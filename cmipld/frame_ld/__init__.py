
import json
from pyld import jsonld
import jmespath
import re


def direct(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except AttributeError as e:
            if "object has no attribute 'json_string'" in e.__str__():
                print('!! Error handling has corrected the error.\n In the future, please ensure that parsing functions are called using "clean(process=[...])" method or between a start and end method.\n For more information consult the documentation.')
                args[0].clean(process=[func.__name__])
                return args[0]
                
            # print(f"An error occurred in {func.__name__}: {e}")
            # # Handle error, e.g., return a placeholder string
            # return "Error occurred"
    return wrapper



class Frame:
    def __init__(self,source,frame):
        
        # if isinstance(source, list):
        #     source = {"@context":{},"@graph":source}
        # elif isinstance(source, str):
        #     source = json.loads(source)
        
        self.source = source
        self.frame = frame
        
        self.data = self.graph_only(jsonld.frame(source, frame))
        
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
    def clean(self, process = None):
        
        if not process:
            process = ['rmld','rmnull','untag','flatten']
            
        self.start
        
        for function in process:    
            self.__getattribute__(function)
        
        self.end
        
    # @staticmethod
    @property
    def start(self):
        self.json_string = json.dumps(self.data , indent=2)
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
        self.json_string = re.sub(r'"(?!mip:|@)[^@":]*:([^@"]*?)":', r'"\1":', self.json_string)
        return self
    @property 
    @direct
    def rmld(self):
        self.json_string = re.sub(r'("@[^"]*":\s*".*?"(?:,)?\s*)', '', self.json_string)
        return self
    @property 
    @direct
    def rmnull(self):
        self.json_string = re.sub(r'[\s]*"(.*?)":\s*null*[,\s]*|[,\s]*"(.*?)":\s*null*[\s]*', '', self.json_string)
        return self
    @property 
    @direct
    def flatten(self):
        self.json_string = re.sub(r'{\s*"([^"]*?)":\s*"(.+)"\s*}', r'"\2"', self.json_string)
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