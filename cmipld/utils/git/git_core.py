import os
import subprocess
import sys

def toplevel():
    """Get the top-level directory of the git repository"""
    return os.popen('git rev-parse --show-toplevel').read().strip()

def url():
    """Get the repository's remote URL"""
    return subprocess.getoutput('git remote get-url origin').replace('.git', '').strip()
