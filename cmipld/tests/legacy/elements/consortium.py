import os
import cmipld
from cmipld.tests.elements.global_import import *
from typing import List, Optional
import asyncio

elementpath = 'organisations/consortia'
elementtype = "consortium"
owners = ['mip-cmor-tables:']

repo_path = cmipld.utils.git.ldpath('')
repourl = cmipld.utils.git.url()
reposhort = urlmap[repourl]

####################################################
# Issue Templates
####################################################
conf = f'''
[{elementtype}]
    Acronym = "CMIP"
    Name = "Coupled Model Intercomparison Project"
    
    [institutions]
        cmip6_acronyms = [
                "CMIP-IPO",
                "WCRP"
            ]
    # nest institutions here, use the cmip acnronyms which they have been registered with.
'''

description = '''
'''

more_info = ''


####################################################
# Validation Functions
####################################################

class DateRange(BaseModel):
    from_: int = Field(..., alias="from")
    phase: str
    to: int


class Institution(BaseModel):
    id: str = Field(..., alias="@id")


class Member(BaseModel):
    type: str = Field(..., alias="@type")
    dates: List[DateRange]
    institution: Institution
    membership_type: str = Field(..., alias="membership-type")


class Validate(BaseModel):
    id: str = Field(..., alias="@id")
    type: str = Field(..., alias="@type")
    changes: Optional[str] = ""
    cmip_acronym: str = Field(..., alias="cmip-acronym")
    members: List[Member]
    name: str
    status: str
    url: Optional[HttpUrl] = None

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


    # # after alias resolved
    # @model_validator(mode='before')#before
    # def check_keys(cls, values):
    #     return check_all_keys_present(cls, values)
print(os.popen('pwd').read())


async def get_existing():
    inst = await cmipld.quicklook([os.path.abspath('./JSONLD/organisations/institutions/')])
    cons = await cmipld.quicklook([os.path.abspath('./JSONLD/organisations/consortia/')])
    return dict(institutions=inst, consortia=cons)


####################################################
# Element Class
####################################################
class consortium(MIPConfig):
    def __init__(self) -> None:
        self.checks = Validate

    ##### Config to JSONLD #####
    def create_jsonld(self, conf, write=True):

        self.conf = conf
        self.action = conf.get('action', 'new')
        if 'action' in conf:
            del conf['action']

        exist = asyncio.run(get_existing())

        print(exist)

        institutions = dict([[i['cmip_acronym'], i]
                            for i in exist['institutions']])

        error = ''
        inst = {}
        for i in conf['institutions']:
            if i not in institutions:
                error += f'    - Institution [{i}] does not exists in the institutions file. Please add this to proceed.\n'
            else:
                inst[i] = f"{i} [{institutions[i]['identifiers']['ror']} - {institutions[i]['identifiers']['institution_name']}]"
        if error:
            error = '#Error: \n Pausing submission. Please edit the initial config (above) addressing the issues below to try again. \n\n ' + error
            update_issue(issue_number, error)

        print('aaa')

        self.path = ldname(
            f"{repo_path}/{elementpath}/{self.conf['name'].lower()}.json")

        print(self.path)
        self.new_old_action_checks(elementtype)
        print(self.pullname)

        self.json = cmipld.utils.sorted_dict(self.json)

        if self.validate(self.json):
            return self.json
        else:
            return False


def get_template():
    if reposhort not in owners:
        return None
    print('test disabled - to correct. ')
    # test_config(__file__,conf)
    location = repo_path.replace(
        'JSONLD', f".github/ISSUE_TEMPLATE/{elementtype}.md")
    print(f"Saving {elementtype} to {location}")
    return create_template(elementtype, more_info, conf, location)
