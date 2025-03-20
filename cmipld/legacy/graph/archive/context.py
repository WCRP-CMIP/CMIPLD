import argparse


def get_context():
    parser = argparse.ArgumentParser(
        description='Uses the graph.json to generate a context for a type.')
    parser.add_argument(
        'graph', type=str, help='The file to use to generate the context network.json')
    args = parser.parse_args()
    return args.context


async def main():
    from __init__ import JSONLDProcessor
    g = JSONLDProcessor()
    # g.read_graph
    await g.make_graph(['/Users/daniel.ellis/WIPwork/CMIP6Plus_CVs/compiled/graph_data.json', '/Users/daniel.ellis/WIPwork/mip-cmor-tables/compiled/graph_data.json'])
    print(g.graph.keys())

    g.write()

    print(g.get_context('mip:source-id'))


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
