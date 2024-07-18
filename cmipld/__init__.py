from .file_io import CMIPFileUtils,LatestFiles
from .frame_ld import Frame



# for CLI purposes. To develop further

import argparse,os
import subprocess


def run_bash_script(script_name):
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', script_name)
    try:
        result = subprocess.run(['bash', script_path], check=True, capture_output=True, text=True)
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error running script: {e}")
        print(e.stderr)

def main():
    parser = argparse.ArgumentParser(description="CMIP Utilities")
    parser.add_argument('--run-script', help="Run a bash script from the scripts directory")
    args = parser.parse_args()

    if args.run_script:
        run_bash_script(args.run_script)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()