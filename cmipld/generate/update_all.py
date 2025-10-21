#!/bin/python3

import glob
import os
import tqdm


def main():
    """Main function for update_all command"""
    
    
    branch = os.popen('git rev-parse --abbrev-ref HEAD 2>/dev/null').read().strip()
    assert branch in ['src-data','production'], f"Please switch to 'src-data' or 'production' branch from '{branch}' before running update_all."
    
    # Update contexts - this will call the Python function directly
    print("Updating contexts...")
    try:
        from .update_ctx import main as update_ctx_main
        update_ctx_main()
    except ImportError:
        # Fallback to os.system for backward compatibility
        os.system('update_ctx')
    
    
    # Validate JSON-LD files - use shell wrapper
    
    # changed since last commit. 
    # git diff HEAD~1 --name-only | grep -E '\.(json|jsonld)$'
    
    
    print("Validating JSON-LD files...")
    try:
        from ..utils.shell_wrappers import run_shell_script
        run_shell_script('validjsonld', ['.'])
    except ImportError:
        # Fallback to os.system for backward compatibility
        os.system('validjsonld')
    
    # Generate graphs for all src-data directories
    print("Generating graphs...")
    for i in tqdm.tqdm(glob.glob('./*/')):
        try:
            from ..utils.shell_wrappers import run_shell_script
            run_shell_script('ld2graph', [i])
        except ImportError:
            # Fallback to os.system for backward compatibility
            os.system('ld2graph '+i)
    
    print("Update complete!")


if __name__ == '__main__':
    main()
