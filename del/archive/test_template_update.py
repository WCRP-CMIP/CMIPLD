#!/usr/bin/env python3
"""
Test script for the template_update CLI command
"""

import subprocess
import sys
from pathlib import Path

def test_template_update_cli():
    """Test the template_update CLI command."""
    
    print("Testing template_update CLI command...")
    
    # Get the CMIP-LD directory
    cmip_ld_dir = Path(__file__).parent
    
    # Set up paths
    emd_templates = Path("/Users/daniel.ellis/WIPwork/Essential-Model-Documentation/.github/CSV_TEMPLATES/templates")
    output_dir = cmip_ld_dir / "test_output" 
    
    # Create output directory
    output_dir.mkdir(exist_ok=True)
    
    try:
        # Test the CLI command
        cmd = [
            sys.executable, "-m", "cmipld.generate.template_generator",
            "--template-dir", str(emd_templates),
            "--output-dir", str(output_dir)
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            print(f"STDERR:\n{result.stderr}")
        
        # Check if any YAML files were generated
        yaml_files = list(output_dir.glob("*.yml"))
        print(f"Generated {len(yaml_files)} YAML files:")
        for yaml_file in yaml_files:
            print(f"  - {yaml_file.name}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running test: {e}")
        return False

if __name__ == "__main__":
    success = test_template_update_cli()
    if success:
        print("\n✅ Test passed!")
    else:
        print("\n❌ Test failed!")
    sys.exit(0 if success else 1)
