# -*- coding: utf-8 -*-
"""
Git Core Utilities

Core git operations for CMIP-LD repositories including:
- Repository URL and path operations
- URL format conversions (GitHub repo <-> GitHub Pages <-> Raw)
- Repository information display
"""

import os
import re
import subprocess
from ...__init__ import prefix, mapping

# =============================================================================
# REPOSITORY PATH & URL
# =============================================================================

def toplevel():
    """Get the top-level directory of the git repository."""
    return os.popen('git rev-parse --show-toplevel').read().strip()


def url():
    """Get the repository's remote URL (normalized, without .git)."""
    return subprocess.getoutput('git remote get-url origin').replace('.git', '').strip()


def get_repo_url():
    """
    Get the GitHub repository URL, normalized to HTTPS format.
    
    Returns:
        str: Repository URL ending with '/' and lowercase org name
    """
    repo_url = subprocess.check_output(
        ['git', 'config', '--get', 'remote.origin.url'],
        universal_newlines=True
    ).strip()
    
    # Convert SSH to HTTPS format
    if repo_url.startswith("git@github.com:"):
        repo_url = "https://github.com/" + repo_url.replace("git@github.com:", "").replace(".git", "")
    elif repo_url.endswith(".git"):
        repo_url = repo_url.replace(".git", "")
    
    # Ensure trailing slash
    if not repo_url.endswith('/'):
        repo_url = repo_url + '/'
    
    # Lowercase the org name (index 3 in split URL)
    parts = repo_url.split('/')
    parts[3] = parts[3].lower()
    
    return '/'.join(parts)


def get_relative_path(cwd=None):
    """
    Get relative path from repository root to specified directory.
    
    Args:
        cwd: Directory path (default: current working directory)
    
    Returns:
        str: Relative path from repo root
    """
    if cwd is None:
        cwd = os.getcwd()
    
    repo_root = subprocess.check_output(
        ['git', 'rev-parse', '--show-toplevel'],
        universal_newlines=True
    ).strip()
    
    return os.path.relpath(cwd, repo_root)


def get_path_url(path=None):
    """
    Get GitHub URL for a specific path in the repository.
    
    Args:
        path: Path to get URL for (default: current directory)
    
    Returns:
        str: GitHub URL to the path on main branch
    """
    repo_url = get_repo_url()
    relative_path = get_relative_path(path)
    return f"{repo_url}tree/main/{relative_path}"


# =============================================================================
# URL FORMAT CONVERSIONS
# =============================================================================

def url2io(github_repo_url, branch='main', path_base=''):
    """
    Convert GitHub repository URL to GitHub Pages URL.
    
    Args:
        github_repo_url: GitHub repo URL (https or SSH format)
        branch: Branch name (default: 'main')
        path_base: Base path within repo
    
    Returns:
        str: GitHub Pages URL
    """
    # Convert SSH URL to HTTPS if needed
    if github_repo_url.startswith('git@github.com:'):
        github_repo_url = github_repo_url.replace('git@github.com:', 'https://github.com/')
    
    if '/tree/' in github_repo_url:
        pattern = rf"https://github\.com/(?P<username>[^/]+)/(?P<repo_name>[^/]+)/tree/{branch}/{path_base}(?P<path>.*)"
    else:
        pattern = rf"https://github\.com/(?P<username>[^/]+)/(?P<repo_name>[^/]+)"
    
    match = re.match(pattern, github_repo_url)
    if not match:
        raise ValueError("Invalid GitHub repository URL format.")
    
    username = match.group("username")
    repo_name = match.group("repo_name")
    path = match.groupdict().get("path", "").strip('/')
    
    # github_pages_url = f"https://{username.lower()}.github.io/{repo_name}/{path}/"
    github_url = f"https://{username.lower()}.github.io/{repo_name}/"
    
    github_url = (github_url + '/').replace('//', '/')

    
    return github_url


def io2repo(github_pages_url):
    """
    Convert GitHub Pages URL to GitHub repository URL.
    
    Args:
        github_pages_url: GitHub Pages URL
    
    Returns:
        str: GitHub repository URL
    """
    username, repo_name, path = extract_repo_info(github_pages_url)
    return f'https://github.com/{username}/{repo_name}.git'


def extract_repo_info(github_pages_url):
    """
    Extract username, repository name, and path from GitHub Pages URL.
    
    Args:
        github_pages_url: GitHub Pages URL
    
    Returns:
        tuple: (username, repo_name, path)
    """
    pattern = r'https{0,1}://([a-zA-Z0-9-_]+)\.github\.io/([a-zA-Z0-9-_]+)/(.*)?'
    match = re.match(pattern, github_pages_url)
    
    if match:
        return match.group(1), match.group(2), match.group(3)
    else:
        raise ValueError("Invalid GitHub Pages URL")


# =============================================================================
# REPOSITORY INFO DISPLAY
# =============================================================================

def cmip_info():
    """
    Display and return CMIP-LD repository information.
    
    Shows a formatted panel with repository prefix, location, and pages link.
    
    Returns:
        DotAccessibleDict: Repository info with prefix, path, name, url, io keys
    """
    # Lazy imports to avoid circular dependencies
    from rich.panel import Panel
    from rich.console import Console
    from ...locations import reverse_mapping
    from .git_repo_metadata import getreponame
    
    console = Console()
    
    # Lazy import DotAccessibleDict
    from ..jsontools import DotAccessibleDict
    
    repo_url = get_repo_url()
    # io_url = url2io(repo_url.rstrip('/'))
    repopath = toplevel()
    reponame = getreponame()
    prx = prefix()
    
    
    print(prx,mapping)
    
    data = DotAccessibleDict(
        prefix=prx,
        path=repopath,
        name=reponame,
        url=repo_url,
        link=mapping.get(prx, repo_url)
    )


    console.print(Panel.fit(
        f"[bold cyan]Parsing repo:[/bold cyan] {data['prefix']}\n"
        f"[bold magenta]Location:[/bold magenta] {repo_url}\n"
        f"[bold red]Pages link:[/bold red] {data['link']}",
        title="[bold yellow]Repository Info[/bold yellow]",
        border_style="blue"
    ), justify="center")
    
    return data
