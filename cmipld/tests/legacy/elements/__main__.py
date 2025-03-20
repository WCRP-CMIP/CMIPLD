
# python -m cmipld.tests.elements
import cmipld.tests.elements
from cmipld.utils.git.actions import parse_md, dispatch
import configparser
# from . import activity
import json
import sys
import os
import re


def action():
    issue_body = os.environ.get('ISSUE_BODY')
    print(issue_body)
    conf = parse_md(issue_body)
    print(conf)
    main(conf)


def main(conf):
    issue_number = os.environ.get('ISSUE_NUMBER')
    issue_submitter = os.environ.get(
        'ISSUE_SUBMITTER') or 'automation@wcrp-cmip.org'
    repo = os.environ.get('REPO').replace(
        'https://github.com', 'https://api.github.com/repos')
    token = os.environ.get('GH_TOKEN')
    errors = []

    # process conf
    config = configparser.ConfigParser()
    config.read_string(conf)

    # print(config.sections())

    for section in config.sections():
        try:
            # data
            entry = config[section]
            # library
            section = section.replace('-', "_")
            entrylib = getattr(cmipld.tests.elements, section)
            # class + data
            entryclass = getattr(entrylib, section)()

            # print(entry)

            sucess = entryclass.create_jsonld(entry, write=True)

            # write
            # change branch

            # if sucess:

            #     payload = {
            #         "event_type": 'new_element',
            #         "client_payload": {
            #             "name": entryclass.pullname, # we need this to define the pull request
            #             "issue": issue_number,
            #             "author" : issue_submitter,
            #             "data" : json.dumps(entryclass.json)
            #         }
            #     }

            #     dispatch(token,payload,repo)

        except ModuleNotFoundError as e:
            errors.append(
                f"No such module {section} in cmipld. Please check the congifuration file template.")
            continue

        if errors:
            print(errors)


if __name__ == '__main__':
    print(action())

    # git add one file.
    # git commit with user
    # git push


# conf = '''
# [institution]
#     Acronym = CMIP-IPO
#     Full_Name = CMIP Model Intercomparison Project Office
#     ROR = 000fg4e24

#     # only change the item below to "update" if you are submitting a correction.
#     action = new

# [activity]
#     Name = CMIP
#     Long_Name =  Coupled Model Intercomparison Project
#     URL = https://wcrp-cmip.org

#     # only change the item below to "update" if you are submitting a correction.
#     action = new

# [sub-experiment-id]
#     name =  new-sub-experiment
#     description = A sample sub-experiment id

#     # only change the item below to "update" if you are submitting a correction.
#     action = new
# '''
