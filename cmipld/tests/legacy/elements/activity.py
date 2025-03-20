from cmipld.tests.elements.global_import import *


elementpath = 'activity/'
elementtype = "activity-id"
owners = ['cmip6plus:']

repo_path = cmipld.utils.git.ldpath('')
repourl = cmipld.utils.git.url()
reposhort = urlmap[repourl]

####################################################
# Issue Templates
####################################################
conf = '''
[activity]
    Name = "CMIP"
    Long_Name =  "Coupled Model Intercomparison Project"
    URL = "https://wcrp-cmip.org"
    
    # only change the item below to "update" if you are submitting a correction. 
    action = "new"
'''

description = '''
'''

more_info = ''


# ldcontent = CMIPFileUtils().load(f"{repo_path}/{elementpath}graph.jsonld")


####################################################
# Validation Functions
####################################################

class Validate(BaseModel):
    '''
    Pydantic model for validating element files
    '''

    id: str = Field(alias='@id')
    type: str = Field(alias='@type')
    name: str
    description: str
    url: HttpUrl
    # optional: int = Field(..., description="The age of the user")

    # class Config:
    #     loc_by_alias = False

    @field_validator('id')
    def id(cls, v):
        if not v.startswith(f"{reposhort}:{elementpath}"):
            raise ValueError('must start with the correct path')
        return v

    @field_validator('type')
    def type(cls, v):
        if v != elementtype:
            raise ValueError(f'{v} must be {elementtype} ')
        return v

    @field_validator('name')
    def name(cls, v):
        if len(v) < 3 or len(v) > 25:
            raise ValueError('must be at between 3 and 25 characters')
        return v

    @field_validator('description')
    def description(cls, v):
        return True

    @field_validator('url')
    def url(cls, v):
        return True

    # after alias resolved
    @model_validator(mode='before')  # before
    def check_keys(cls, values):
        return check_all_keys_present(cls, values)


####################################################
# Element Class
####################################################
class activity(MIPConfig):

    def __init__(self) -> None:
        # super().__init__()

        self.checks = Validate

    ##### Config to JSONLD #####
    def create_jsonld(self, conf, write=True):

        self.conf = conf
        self.aciton = conf['action']

        self.json = {
            "@id": f"{urlmap[repourl]}:{elementpath}{self.conf['name']}",
            "@type": elementtype,
            "description": self.conf['long_name'],
            "name": self.conf['name'],
            "url": self.conf['url']
        }

        if self.validate(self.json):
            print(json.dumps(self.json, indent=4))

            if write:
                path = ldname(
                    f"{repo_path}/{elementpath}/{self.conf['name']}.json")
                print(path)

            return True
        else:
            return False


def test_config():
    # test_config()
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read_string(conf)

    element = __file__.split('/')[-1].split('.')[0]
    templateconf = dict(cfg[element])

    test = globals()[element]()
    test.create_jsonld(templateconf, write=False)


def get_template():

    if reposhort not in owners:
        return None

    test_config()

    location = repo_path.replace(
        'JSONLD', f".github/ISSUE_TEMPLATE/{elementtype}.md")

    print(f"Saving {elementtype} to {location}")

    return create_template(elementtype, more_info, conf, location)
