import json
import os
import sys
from collections import OrderedDict
import cmipld

# from schema import Schema, And, Use, Optional, SchemaError

from cmipld.locations import urlmap
from cmipld.utils import errprint
import cmipld.utils.git as gitutils

from cmipld.file_io import CMIPFileUtils, ldname
from cmipld.frame_ld import Frame

from pydantic import BaseModel, ValidationError, field_validator, Field, HttpUrl, model_validator


def getid(self):
    return self.json['@id'].split('/')[-1]


def pydantic_eprint(e):
    error_details = e.errors()

    gh = '''# Errors <br>'''

    print("\nParsed error details:")
    for error in error_details:
        # print(f"Error in field '{error}")

        gh += f"-  {error['msg']} \n Input:{error['input']} \n\n"

    gitutils.update_issue(f'#Sanity Check \n {comment}')


class MIPConfig():
    '''Superclass for all MIP elements'''
    # def __init__(self) -> None:
    #     self.checks = lambda x: print('checks not set up')

    def validate_one(self, data):
        try:
            data['skip'] = 'all'
            self.checks(**data)
            return True
        except ValidationError as e:
            pydantic_eprint(e)
            return False

    def validate(self, data):
        try:
            self.checks(**data)
            return True
        except ValidationError as e:
            pydantic_eprint(e)
            return False

    @property
    def getid(self):
        return self.json['@id'].split('/')[-1]

    @property
    def jsonstr(self):
        return json.dumps(self.json, indent=4)

    def new_old_action_checks(self, elementtype):
        if self.action == 'new':
            if os.path.exists(self.path):
                gitutils.close_issue(
                    '### File Already Exists \n Closing Issue. \n If you meant to update the file, please change the action to "update"')
                raise FileExistsError(f'File Already Exists {self.path}')

            self.pullname = f"Add {elementtype}: {self.json['cmip_acronym']}"
        else:
            if not os.path.exists(self.path):
                gitutils.close_issue(
                    '### File Does Not Exist \n Closing Issue. \n To add a new file, please change the action to "new"')
                raise FileNotFoundError(
                    f'Missing File - cannot update: {self.path}')

            self.pullname = f"Update {elementtype}:{self.getid}"


def check_all_keys_present(cls, values):
    """
    Ensure that all required fields are present in the input data.
    """
    # required_fields = cls.__annotations__.keys()
    required_fields = {field.alias or name: name for name,
                       field in cls.__fields__.items()}

    # print('-----')
    # for i in cls.__fields__.items():
    #     print(i)
    #     print(i[1].alias)
    #     print(values)
    # print('-----')

    if 'skip' in values:
        if values['skip'] == 'all':
            return values
        else:
            for i in values['skip']:
                required_fields.remove(i)

    # Check for missing fields
    missing_fields = [
        field for field in required_fields if field not in values and f"@{field}" not in values]

    if missing_fields:
        raise ValueError(
            f"Missing required fields: {', '.join(missing_fields)}\n\n")

    return values


def create_template(element_type, moreinfo, config, location):

    element_type_c = element_type.capitalize()
    split = ' '.join([i.capitalize() for i in element_type.split('-')])

    template = f"""---
name: {element_type_c}
about: Adding a new, or updating an existing, {split.lower()}
title: 'Review request for change in {element_type}'
labels: '{element_type}'
assignees: ''

---

# Add Consortium Template

To request a new item, please amend the template below to reflect the items you are interested in.

Relevant conditions and naming conventions for this item can be found using the wiki pages [here]({moreinfo}).

## Amending Information on an Existing Item

If you wish to amend an item, please supply only the fields you are interested in and ensure that you change the *action* field to *update*.

``` action = update ```

<!---  info 

We are trialing the addition of new components using the configuration file format. 
To use this, please fill out the template below, keeping the spacing and indentation of the file.

--->

## Contents (What We Wish to Add)



``` configfile

{config}

```

"""

    with open(location, 'w') as f:
        f.write(template)
        print(f"Template written to {location}")
    return template


def test_config(file, conf):
    # test_config()
    import configparser
    cfg = configparser.ConfigParser()
    cfg.read_string(conf)

    element = __file__.split('/')[-1].split('.')[0]
    templateconf = dict(cfg[element])

    test = globals()[element]()
    test.create_jsonld(templateconf, write=False)
