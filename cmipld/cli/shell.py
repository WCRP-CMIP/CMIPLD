"""
Thin Python entry points that exec the bundled shell scripts in static/bin/.
Each function finds the script relative to this file and runs it via bash,
passing through all CLI arguments and the process return code.
"""

import os
import subprocess
import sys
from pathlib import Path

_BIN = Path(__file__).parent.parent / "bin"


def _run(name: str):
    script = _BIN / name
    result = subprocess.run(["bash", str(script)] + sys.argv[1:])
    sys.exit(result.returncode)


def ld2graph():      _run("ld2graph")
def validjsonld():   _run("validjsonld")
def rmbak():         _run("rmbak")
def rmgraph():       _run("rmgraph")
def coauthor_file(): _run("coauthor_file")
def cmipld_help():   _run("cmipld-help")
