#!/usr/bin/env python3
import sys
import json
import os
from pyld import jsonld

try:
    from pygments import highlight
    from pygments.lexers import JsonLexer
    from pygments.formatters import TerminalFormatter
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False

def pretty_print_json(data):
    """Pretty print JSON with colors if pygments is available"""
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    
    if HAS_PYGMENTS:
        formatted = highlight(json_str, JsonLexer(), TerminalFormatter())
        print(formatted)
    else:
        print(json_str)

def load_input(input_path):
    """Load input - if file exists, load as JSON and inline relative contexts, otherwise treat as URL"""
    if os.path.isfile(input_path):
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        # Inline relative context references
        if '@context' in data and isinstance(data['@context'], str):
            if not data['@context'].startswith(('http://', 'https://')):
                # Load the context file and substitute it in place
                base_dir = os.path.dirname(os.path.abspath(input_path))
                context_path = os.path.join(base_dir, data['@context'])
                if os.path.isfile(context_path):
                    try:
                        with open(context_path, 'r') as ctx_f:
                            context_data = json.load(ctx_f)
                            data['@context'] = context_data.get('@context', context_data)
                    except:
                        pass 
        
        return data
    else:
        return input_path  # Return URL string for pyld to fetch

def expand(input_file):
    """Expand JSON-LD document"""
    try:
        input_data = load_input(input_file)
        result = jsonld.expand(input_data)
        pretty_print_json(result)
    except Exception as e:
        print(f"Error expanding: {e}", file=sys.stderr)
        sys.exit(1)

def compact(input_file, context_file):
    """Compact JSON-LD document with context"""
    try:
        input_data = load_input(input_file)
        context_data = load_input(context_file)
        result = jsonld.compact(input_data, context_data)
        pretty_print_json(result)
    except Exception as e:
        print(f"Error compacting: {e}", file=sys.stderr)
        sys.exit(1)

def test(input_file):
    """Test if JSON-LD document is valid by compacting with itself - returns True/False"""
    try:
        input_data = load_input(input_file)
        jsonld.compact(input_data, input_data)  # Try to compact with itself
        print("true")
        return True
    except Exception:
        print("false")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: script {expand|compact|test} <input> [context]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "expand":
        if len(sys.argv) != 3:
            print("Usage: script expand <input>")
            sys.exit(1)
        expand(sys.argv[2])
    
    elif command == "compact":
        if len(sys.argv) == 3:
            compact(sys.argv[2], sys.argv[2])
        elif len(sys.argv) == 4:
            compact(sys.argv[2], sys.argv[3])
        else:
            print("Usage: script compact <input> [context]")
            sys.exit(1)
    
    elif command == "test":
        if len(sys.argv) != 3:
            print("Usage: script test <input>")
            sys.exit(1)
        test(sys.argv[2])
    
    else:
        print("Unknown command. Use: expand, compact, or test")
        sys.exit(1)

if __name__ == "__main__":
    main()