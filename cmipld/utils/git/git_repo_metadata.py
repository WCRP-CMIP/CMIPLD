import subprocess, os, re
import requests
from ..io import shell

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
    return shell(f'git ls-tree -r {branch} --name-only ').split()

def get_cmip_repo_info():
    """Retrieve repository information and tags"""
    repo = subprocess.getoutput(
        'git remote get-url origin').replace('.git', '/blob/main/JSONLD').strip()
    cv_tag = subprocess.getoutput(
        "curl -s https://api.github.com/repos/WCRP-CMIP/CMIP6Plus_CVs/tags | jq -r '.[0].name'").strip()
    mip_tag = subprocess.getoutput(
        "curl -s https://api.github.com/repos/PCMDI/mip-cmor-tables/tags | jq -r '.[0].name'").strip()
    return repo, cv_tag, mip_tag


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



import os
import subprocess

def get_repo_url():
    # Get the GitHub repository URL using `git config`
    repo_url = subprocess.check_output(
        ['git', 'config', '--get', 'remote.origin.url'], 
        universal_newlines=True
    ).strip()
    
    # If the URL is in SSH format (git@github.com:...), convert it to HTTPS
    if repo_url.startswith("git@github.com:"):
        repo_url = "https://github.com/" + repo_url.replace("git@github.com:", "").replace(".git", "")
    elif repo_url.endswith(".git"):
        # If it's already HTTPS, just remove the .git
        repo_url = repo_url.replace(".git", "")
    
    return repo_url

def get_relative_path(cwd = None):
    # Get the current working directory
    if cwd == None:
        cwd = os.getcwd()
    
    # Get the root of the git repository using `git rev-parse --show-toplevel`
    repo_root = subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel'], 
        universal_newlines=True
    ).strip()
    
    # Get the relative path from the repo root to the current directory
    relative_path = os.path.relpath(cwd, repo_root)
    
    return relative_path

def get_path_url(path = None):
    # Get the base GitHub URL
    repo_url = get_repo_url()
    
    # Get the relative path from the repo root
    relative_path = get_relative_path(path)
    
    # Construct the URL for the folder
    github_url = f"{repo_url}/tree/main/{relative_path}"
    
    return github_url

