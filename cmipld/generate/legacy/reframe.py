#!/usr/bin/env python3

"""
CMIP JSON-LD Graph Processor

This script processes JSON-LD files related to CMIP (Coupled Model Intercomparison Project),
generates a graph, creates frames, links frames, and updates them.

Usage:
    python cmip_graph_processor.py [options] [file_paths...]

Options:
    --graph PATH          Path to write the graph JSON output
    --frame PATH          Path to write the frame JSON output
    --frame-update PATH   Path to write the updated frame JSON output
    --help                Show this help message and exit

Example:
    python cmip_graph_processor.py --graph ./graph.json --frame ./frames.json file1.json file2.json
"""

import cmipld
from cmipld.graph import JSONLDGraphProcessor
import argparse
import asyncio


def parse_args():
    parser = argparse.ArgumentParser(description="Process CMIP JSON-LD files and perform graph operations.")
    parser.add_argument("--graph", help="Path to write the graph JSON output")
    parser.add_argument("--frame", help="Path to write the frame JSON output")
    parser.add_argument("--frame-update", action='store_true', help="Path to write the updated frame JSON output")
    parser.add_argument('files', type=str, nargs='+', help='The file(s) to use to generate the network.json')
    
    args = parser.parse_args()

    if not args.files:
        parser.error("At least one input file is required.")
        
    return args


async def main(args):
    # Initialize the graph processor
    graph = JSONLDGraphProcessor()

    # Process input files
    await graph.make_graph(args.files)
    print("Graph processing completed.")

    # Write graph if specified
    if args.graph:
        graph.write(location=args.graph)
        print(f"Graph written to {args.graph}")

    # Generate frames and write if specified
    if args.frame:
        core_frame = graph.generate_frames
        linked_frame = graph.link_frames
        graph.filter_frames
        graph.write(location=args.frame, item='frames')
        print(f"Frames written to {args.frame}")

    # Update frames and write if specified
    if args.frame and args.frame_update:
        graph.update_frames()

    return print(f"Processing completed for {graph.prefix}")
    

    


def run():
    args = parse_args()
    asyncio.run(main(args))
    

if __name__ == "__main__":
    run()

    
'''

reframe --graph ./compiled/graph.json --frame ./compiled/frames.json --frame-update /Users/daniel.ellis/WIPwork/mip-cmor-tables/compiled/graph_data.json /Users/daniel.ellis/WIPwork/CMIP6Plus_CVs/compiled/graph_data.json


'''