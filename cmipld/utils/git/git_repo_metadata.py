import subprocess
import requests

def getreponame():
    """Get the repository name"""
    return subprocess.getoutput('git remote get-url origin').split('/')[-1].replace('.git', '').strip()

def getrepoowner():
    """Get the repository owner"""
    return subprocess.getoutput('git remote get-url origin').split('/')[-2].strip()

def getlastcommit():
    """Get the last commit hash"""
    return subprocess.getoutput('git rev-parse HEAD').strip()

def getlasttag():
    """Get the most recent tag"""
    return subprocess.getoutput('git describe --tags --abbrev=0').strip()

def getfilenames(branch='main'):
    """Get file names in the repository"""
    return os.popen(f'git ls-tree -r {branch} --name-only ').read().split()

def get_cmip_repo_info():
    """Retrieve repository information and tags"""
    repo = subprocess.getoutput(
        'git remote get-url origin').replace('.git', '/blob/main/JSONLD').strip()
    cv_tag = subprocess.getoutput(
        "curl -s https://api.github.com/repos/WCRP-CMIP/CMIP6Plus_CVs/tags | jq -r '.[0].name'").strip()
    mip_tag = subprocess.getoutput(
        "curl -s https://api.github.com/repos/PCMDI/mip-cmor-tables/tags | jq -r '.[0].name'").strip()
    return repo, cv_tag, mip_tag

import re

def extract_repo_info(github_pages_url):
    """Extract username and repository name from GitHub Pages URL."""
    pattern = r'https{0,1}://([a-zA-Z0-9-_]+)\.github\.io/([a-zA-Z0-9-_]+)/(.*)?'
    match = re.match(pattern, github_pages_url)

    if match:
        username = match.group(1)
        repo_name = match.group(2)
        path = match.group(3)
        return username, repo_name, path
    else:
        raise ValueError("Invalid GitHub Pages URL")

# ... (rest of the URL conversion functions remain the same)
