"""
Tools for adding and validating checksums
"""
from copy import copy, deepcopy
import hashlib
import json
import datetime
from collections import OrderedDict
from .git import getbranch, getreponame, getrepoowner, getlastcommit, getlasttag, url
from ..locations import reverse_mapping
from ..__init__ import prefix



def validate_checksum(dictionary, checksum_location='version_metadata'):
    """
    Validate the checksum in the ``dictionary``.

    Parameters
    ----------
    dictionary: dict
        The dictionary containing the ``checksum`` to validate.
    checksum_location: str
        sub-dictionary to look for in /add the checksum to.

    Raises
    ------
    KeyError
        If the ``checksum`` key does not exist.
    RuntimeError
        If the ``checksum`` value is invalid.
    """
    if 'checksum' not in dictionary[checksum_location]:
        raise KeyError('No checksum to validate')
    dictionary_copy = deepcopy(dictionary)
    del dictionary_copy[checksum_location]['checksum']
    checksum = _checksum(dictionary_copy)
    if dictionary[checksum_location]['checksum'] != checksum:
        msg = ('Expected checksum   "{}"\n'
               'Calculated checksum "{}"').format(dictionary[checksum_location]['checksum'],
                                                  checksum)
        raise RuntimeError(msg)


def _checksum(obj):
    obj_str = json.dumps(obj, sort_keys=True)
    checksum_hex = hashlib.md5(obj_str.encode(
        'utf8')).hexdigest().split('.')[0]
    return 'md5: {}'.format(checksum_hex)


def version(data, name, location='./', repo=None):
    rmap = reverse_mapping

    writefile = f'{location}'
    output = OrderedDict()

    header = OrderedDict()
    header['file'] = writefile
    header['file_creation_date'] = datetime.datetime.now().isoformat()
    # header['branch'] = getbranch()
    header['version'] = getlasttag()
    header['checksum'] = _checksum(data)

    if repo:
        header['repo_url'] = repo[0]
        header['repo_prefix'] = repo[1]
    else:
        header['repo_url'] = url()
        header['repo_prefix'] = prefix()

    header['last_commit'] = getlastcommit()
    header['comment'] = 'This is an automatically generated file. Do not edit.'

    output['Header'] = header
    if isinstance(data, dict):
        output[name] = OrderedDict(sorted(data.items(), key=lambda item: item[0]))
    elif isinstance(data, list):
        if isinstance(data[0], dict):
            output[name] = [OrderedDict(sorted(d.items(), key=lambda item: item[0])) for d in data]
        else:
            output[name] = sorted(data)
    else:
        output[name] = data

    return output
