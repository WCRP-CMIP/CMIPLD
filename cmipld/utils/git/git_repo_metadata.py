# -*- coding: utf-8 -*-
"""
Git Repository Metadata

Functions for retrieving repository metadata and tracking file changes:
- Basic metadata (repo name, owner, commits, tags)
- File listing and file change tracking (local and remote)
"""

import json
import os
import re
import subprocess

import requests

from ..io import shell
from .gh_utils import GitHubUtils

# =============================================================================
# BASIC REPOSITORY METADATA
# =============================================================================

def getreponame():
    """Get the repository name."""
    return subprocess.getoutput('git remote get-url origin').split('/')[-1].replace('.git', '').strip()


def getrepoowner():
    """Get the repository owner."""
    return subprocess.getoutput('git remote get-url origin').split('/')[-2].strip()


def getlastcommit():
    """Get the last commit hash."""
    return subprocess.getoutput('git rev-parse HEAD').strip()


def getlasttag():
    """Get the most recent tag."""
    return subprocess.getoutput('git describe --tags --abbrev=0').strip()


def getfilenames(branch='main'):
    """Get file names in the repository."""
    return shell(f'git ls-tree -r {branch} --name-only ').split()


def get_cmip_repo_info():
    """Retrieve CMIP-specific repository information and tags."""
    repo = subprocess.getoutput(
        'git remote get-url origin').replace('.git', '/blob/main/JSONLD').strip()
    cv_tag = subprocess.getoutput(
        "curl -s https://api.github.com/repos/WCRP-CMIP/CMIP6Plus_CVs/tags | jq -r '.[0].name'").strip()
    mip_tag = subprocess.getoutput(
        "curl -s https://api.github.com/repos/PCMDI/mip-cmor-tables/tags | jq -r '.[0].name'").strip()
    return repo, cv_tag, mip_tag


# =============================================================================
# REMOTE FILE LISTING
# =============================================================================

def list_repo_files(owner, repo, branch='main', path=''):
    """
    List files in a remote repository via GitHub API.
    
    Args:
        owner: Repository owner
        repo: Repository name
        branch: Branch name (default: 'main')
        path: Path within repository
    
    Returns:
        list: List of dicts with 'name', 'type', 'path' keys
    """
    utils = GitHubUtils()
    returncode, result, stderr = utils.run_gh_cmd_safe(
        ['api', f'/repos/{owner}/{repo}/contents/{path}?ref={branch}']
    )
    
    if returncode != 0:
        raise Exception(f"Failed to list files in repository {owner}/{repo} on branch {branch}: {stderr}")
    
    items = json.loads(result)
    return [{'name': i['name'], 'type': i['type'], 'path': i['path']} 
            for i in (items if isinstance(items, list) else [items])]


# =============================================================================
# FILE CHANGE TRACKING - LOCAL
# =============================================================================

def get_files_changed_since_date(since_date, branch='main', base_path_filter=None, 
                                  exclude_paths=None, repo_url=None, owner=None, repo=None):
    """
    Get all files changed since a specific date from all commits.
    
    Args:
        since_date: Date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
        branch: Branch to check (default: 'main')
        base_path_filter: Optional base path to filter files
        exclude_paths: Optional list of paths to exclude
        repo_url: Optional remote repository URL
        owner: Optional repository owner (alternative to repo_url)
        repo: Optional repository name (alternative to repo_url)
    
    Returns:
        list: List of unique file paths changed since the date
    """
    try:
        # If remote repository is specified, use GitHub API
        if repo_url or (owner and repo):
            return _get_remote_files_changed_since_date(
                since_date, branch, base_path_filter, exclude_paths, repo_url, owner, repo
            )
        
        # Local repository operation
        cmd = f'git log --since="{since_date}" --name-only --pretty=format: {branch}'
        result = subprocess.getoutput(cmd)
        
        files = [f.strip() for f in result.split('\n') if f.strip()]
        unique_files = list(set(files))
        
        # Apply filters
        unique_files = _apply_path_filters(unique_files, base_path_filter, exclude_paths)
        return sorted(unique_files)
        
    except Exception as e:
        print(f"Error getting files changed since {since_date}: {e}")
        return []


def get_files_changed_between_dates(start_date, end_date, branch='main', base_path_filter=None,
                                     exclude_paths=None, repo_url=None, owner=None, repo=None):
    """
    Get all files changed between two specific dates.
    
    Args:
        start_date: Start date in format 'YYYY-MM-DD'
        end_date: End date in format 'YYYY-MM-DD'
        branch: Branch to check (default: 'main')
        base_path_filter: Optional base path to filter files
        exclude_paths: Optional list of paths to exclude
        repo_url: Optional remote repository URL
        owner: Optional repository owner
        repo: Optional repository name
    
    Returns:
        list: List of unique file paths changed between the dates
    """
    try:
        if repo_url or (owner and repo):
            return _get_remote_files_changed_between_dates(
                start_date, end_date, branch, base_path_filter, exclude_paths, repo_url, owner, repo
            )
        
        cmd = f'git log --since="{start_date}" --until="{end_date}" --name-only --pretty=format: {branch}'
        result = subprocess.getoutput(cmd)
        
        files = [f.strip() for f in result.split('\n') if f.strip()]
        unique_files = list(set(files))
        
        unique_files = _apply_path_filters(unique_files, base_path_filter, exclude_paths)
        return sorted(unique_files)
        
    except Exception as e:
        print(f"Error getting files changed between {start_date} and {end_date}: {e}")
        return []


def get_files_changed_with_details(since_date, branch='main', base_path_filter=None,
                                    exclude_paths=None, repo_url=None, owner=None, repo=None):
    """
    Get detailed information about files changed since a specific date.
    
    Args:
        since_date: Date in format 'YYYY-MM-DD'
        branch: Branch to check (default: 'main')
        base_path_filter: Optional base path to filter files
        exclude_paths: Optional list of paths to exclude
        repo_url: Optional remote repository URL
        owner: Optional repository owner
        repo: Optional repository name
    
    Returns:
        list: List of dicts with path, commit_hash, author, date, message
    """
    try:
        if repo_url or (owner and repo):
            return _get_remote_files_changed_with_details(
                since_date, branch, base_path_filter, exclude_paths, repo_url, owner, repo
            )
        
        cmd = f'git log --since="{since_date}" --name-only --pretty=format:"%H|%an|%ae|%ad|%s" --date=iso {branch}'
        result = subprocess.getoutput(cmd)
        
        files_with_details = []
        current_commit = None
        
        for line in result.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if '|' in line:
                parts = line.split('|')
                if len(parts) >= 5:
                    current_commit = {
                        'hash': parts[0],
                        'author': parts[1],
                        'email': parts[2],
                        'date': parts[3],
                        'message': '|'.join(parts[4:])
                    }
            else:
                if current_commit and _passes_filters(line, base_path_filter, exclude_paths):
                    files_with_details.append({
                        'path': line,
                        'commit_hash': current_commit['hash'],
                        'author': current_commit['author'],
                        'email': current_commit['email'],
                        'date': current_commit['date'],
                        'message': current_commit['message']
                    })
        
        return files_with_details
        
    except Exception as e:
        print(f"Error getting detailed file changes since {since_date}: {e}")
        return []


# =============================================================================
# FILE CHANGE TRACKING - CONVENIENCE FUNCTIONS
# =============================================================================

def get_files_changed_from_github_url(github_url, since_date, branch='main',
                                       base_path_filter=None, exclude_paths=None):
    """
    Get files changed from a GitHub URL.
    
    Args:
        github_url: GitHub repository URL
        since_date: Date in format 'YYYY-MM-DD'
        branch: Branch to check (default: 'main')
        base_path_filter: Optional base path to filter files
        exclude_paths: Optional list of paths to exclude
    
    Returns:
        list: List of file paths changed since the date
    """
    return get_files_changed_since_date(
        since_date=since_date,
        branch=branch,
        base_path_filter=base_path_filter,
        exclude_paths=exclude_paths,
        repo_url=github_url
    )


def get_files_changed_from_repo_shorthand(repo_shorthand, since_date, branch='main',
                                           base_path_filter=None, exclude_paths=None):
    """
    Get files changed using 'owner/repo' shorthand notation.
    
    Args:
        repo_shorthand: Repository in 'owner/repo' format
        since_date: Date in format 'YYYY-MM-DD'
        branch: Branch to check (default: 'main')
        base_path_filter: Optional base path to filter files
        exclude_paths: Optional list of paths to exclude
    
    Returns:
        list: List of file paths changed since the date
    """
    if '/' not in repo_shorthand:
        raise ValueError("repo_shorthand must be in 'owner/repo' format")
    
    owner, repo = repo_shorthand.split('/', 1)
    return get_files_changed_since_date(
        since_date=since_date,
        branch=branch,
        base_path_filter=base_path_filter,
        exclude_paths=exclude_paths,
        owner=owner,
        repo=repo
    )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _apply_path_filters(files, base_path_filter=None, exclude_paths=None):
    """Apply base path and exclusion filters to file list."""
    result = files
    
    if base_path_filter:
        if not base_path_filter.endswith('/'):
            base_path_filter += '/'
        result = [f for f in result if f.startswith(base_path_filter)]
    
    if exclude_paths:
        for exclude_path in exclude_paths:
            result = [f for f in result if not f.startswith(exclude_path)]
    
    return result


def _passes_filters(filepath, base_path_filter=None, exclude_paths=None):
    """Check if a filepath passes the filters."""
    if base_path_filter:
        if not base_path_filter.endswith('/'):
            base_path_filter += '/'
        if not filepath.startswith(base_path_filter):
            return False
    
    if exclude_paths:
        for exclude_path in exclude_paths:
            if filepath.startswith(exclude_path):
                return False
    
    return True


def _parse_repo_url(repo_url):
    """Parse GitHub repository URL to extract owner and repo name."""
    if not repo_url:
        return None, None
    
    patterns = [
        r'https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$',
        r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$',
        r'github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$'
    ]
    
    for pattern in patterns:
        match = re.match(pattern, repo_url)
        if match:
            return match.group(1), match.group(2)
    
    return None, None


# =============================================================================
# FILE CHANGE TRACKING - REMOTE (GitHub API)
# =============================================================================

def _get_remote_commits(owner, repo, branch='main', since_date=None, until_date=None):
    """Get commits from a remote repository using GitHub API."""
    try:
        params = {'sha': branch, 'per_page': 100}
        
        if since_date:
            if len(since_date) == 10:
                since_date += 'T00:00:00Z'
            elif 'T' not in since_date and 'Z' not in since_date:
                since_date += 'T00:00:00Z'
            params['since'] = since_date
        
        if until_date:
            if len(until_date) == 10:
                until_date += 'T23:59:59Z'
            elif 'T' not in until_date and 'Z' not in until_date:
                until_date += 'T23:59:59Z'
            params['until'] = until_date
        
        url = f'https://api.github.com/repos/{owner}/{repo}/commits'
        all_commits = []
        page = 1
        
        while True:
            params['page'] = page
            response = requests.get(url, params=params)
            
            if response.status_code != 200:
                print(f"Error fetching commits: {response.status_code} - {response.text}")
                break
            
            commits = response.json()
            if not commits:
                break
            
            all_commits.extend(commits)
            
            if len(commits) < 100:
                break
            
            page += 1
            if page > 10:  # Max 1000 commits
                break
        
        return all_commits
        
    except Exception as e:
        print(f"Error fetching remote commits: {e}")
        return []


def _get_commit_files(owner, repo, commit_sha):
    """Get files changed in a specific commit."""
    try:
        url = f'https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}'
        response = requests.get(url)
        
        if response.status_code != 200:
            return []
        
        commit_data = response.json()
        files = commit_data.get('files', [])
        return [f['filename'] for f in files]
        
    except Exception as e:
        print(f"Error fetching commit files for {commit_sha}: {e}")
        return []


def _get_remote_files_changed_since_date(since_date, branch='main', base_path_filter=None,
                                          exclude_paths=None, repo_url=None, owner=None, repo=None):
    """Get files changed since a date from a remote repository."""
    if repo_url:
        owner, repo = _parse_repo_url(repo_url)
    
    if not owner or not repo:
        print("Error: Could not parse repository information")
        return []
    
    commits = _get_remote_commits(owner, repo, branch, since_date)
    
    all_files = set()
    for commit in commits:
        files = _get_commit_files(owner, repo, commit['sha'])
        all_files.update(files)
    
    return sorted(_apply_path_filters(list(all_files), base_path_filter, exclude_paths))


def _get_remote_files_changed_between_dates(start_date, end_date, branch='main', base_path_filter=None,
                                             exclude_paths=None, repo_url=None, owner=None, repo=None):
    """Get files changed between two dates from a remote repository."""
    if repo_url:
        owner, repo = _parse_repo_url(repo_url)
    
    if not owner or not repo:
        print("Error: Could not parse repository information")
        return []
    
    commits = _get_remote_commits(owner, repo, branch, start_date, end_date)
    
    all_files = set()
    for commit in commits:
        files = _get_commit_files(owner, repo, commit['sha'])
        all_files.update(files)
    
    return sorted(_apply_path_filters(list(all_files), base_path_filter, exclude_paths))


def _get_remote_files_changed_with_details(since_date, branch='main', base_path_filter=None,
                                            exclude_paths=None, repo_url=None, owner=None, repo=None):
    """Get detailed file change information from a remote repository."""
    if repo_url:
        owner, repo = _parse_repo_url(repo_url)
    
    if not owner or not repo:
        print("Error: Could not parse repository information")
        return []
    
    commits = _get_remote_commits(owner, repo, branch, since_date)
    files_with_details = []
    
    for commit in commits:
        files = _get_commit_files(owner, repo, commit['sha'])
        
        for file_path in files:
            if _passes_filters(file_path, base_path_filter, exclude_paths):
                files_with_details.append({
                    'path': file_path,
                    'commit_hash': commit['sha'],
                    'author': commit['commit']['author']['name'],
                    'email': commit['commit']['author']['email'],
                    'date': commit['commit']['author']['date'],
                    'message': commit['commit']['message']
                })
    
    return files_with_details
