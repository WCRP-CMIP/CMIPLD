# import the library

async def quicklook(graphpath, clean=True):
    ''' Quickly load the files from a CMIPLD repo using the frame inside. '''

    import cmipld
    import json

    latest = await cmipld.CMIPFileUtils.load(graphpath)

    print(latest)

    frame = json.load(open(graphpath[0].replace(
        'graph.jsonld', 'frame.jsonld'), 'r'))
    # del frame['@context']
    print(frame)

    return cmipld.Frame([latest], frame).clean().json if clean else cmipld.Frame(latest, frame).json


await quicklook(['JSONLD/organisations/institutions/graph.jsonld'])
