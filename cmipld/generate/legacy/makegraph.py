import cmipld
from cmipld.graph import JSONLDGraphProcessor
import argparse
import asyncio

def parse_args():
    parser = argparse.ArgumentParser(description='Generates a network.json file from a list of files.')
    parser.add_argument('--output', type=str, default='./network.json', help='The file to write the network.json to.')
    parser.add_argument('--frame', default=False, help='The file to write the network.json to.')
    parser.add_argument('--updateframes', action='store_true', help='Update the frame.jsonls files in each repository.')
    
    parser.add_argument('files', type=str, nargs='+', help='The file(s) to use to generate the network.json')
    return parser.parse_args()

async def main(args):
    print(args)
    graph = JSONLDGraphProcessor()
    await graph.make_graph(args.files)
    graph.write(location = args.output)
    
    if args.frame:
        from cmipld.reframe import EnhancedJSONLDGraphProcessor
        
        frames = graph.generate_frames()
        graph.write(location = args)
    
    
    
    
    return True

def run():
    args = parse_args()
    asyncio.run(main(args))

if __name__ == "__main__":
    run()

    
'''

makegraph --output network.json /Users/daniel.ellis/WIPwork/mip-cmor-tables/compiled/graph_data.json /Users/daniel.ellis/WIPwork/CMIP6Plus_CVs/compiled/graph_data.json


'''