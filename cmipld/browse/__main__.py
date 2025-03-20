from .__init__ import * 
from ..utils import sorted_json

def main():
    description = """CLI entry point for the JSON-LD processor.\n\n
    Process JSON-LD documents and extract dependencies
    
    To toggle between data and line mode, press 'm'. 
    To exit the viewer, press 'q'.
    
    
    Maintainer: Dan Ellis (CMIP IPO)
    """
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('url', help='URL of the JSON-LD document to process')
    parser.add_argument('--deps','-d', action='store_true', help='Extract dependencies')
    parser.add_argument('--relative', action='store_true', help='Use relative URLs for dependencies')
    parser.add_argument('--no-compact', '-nc', action='store_true', help='Do not compact the document')
    parser.add_argument('--expand-ctx','-ctx', action='store_false', help='Do not expand context')
    parser.add_argument('--no-expand-links', '-nl', action='store_true', help='Do not expand linked documents')
    parser.add_argument('--output', '-o', help='Output file (default: stdout)')
    parser.add_argument('--no-interactive', '-n',action='store_false',  help='Interactive Playground')
    # parser.add_argument('--no-compact', action='store_true', help='Do not compact the document')
    # data mode for jless 
    
    
    args = parser.parse_args()
    processor = JsonLdProcessor()
    
    
    if 'https://' not in args.url and re.match(matches, args.url):
                for k,v in mapping.items():
                    if k in args.url:
                        args.url = args.url.replace(k+":",v)
                        print(f"Resolving: {k}")
                        break
    print('-'*50)
    print(args.url)
    print('-'*50)
    
    passes=2
    while passes:
        try:
            if args.deps:
                
                # Extract dependencies  
                deps = processor.extract_dependencies(args.url, args.relative)
                result = sorted(list(deps))
            else:
                # Process document
                result = processor.get(
                    args.url,
                    compact=not args.no_compact,
                    expand_ctx=not args.expand_ctx,
                    expand_links=not args.no_expand_links
                )
                
                result = sorted_json(result)
            # Output results
            
            if args.output:
                output = json.dumps(result, indent=2)
                with open(args.output, 'w') as f:
                    f.write(output)
                    
            if args.no_interactive:
                open_jless_with_memory(result)
            else:
                print(output)
                
            passes=0
            sys.exit(0)
                
        except Exception as e:
            if 'Could not retrieve a JSON-LD document from the URL.' in str(e):
                passes-=1
                args.url+= '/graph'
            if not passes:
                print(f"Error processing document: {str(e)}\n\n", file=sys.stderr)
                sys.exit(1)


main()
