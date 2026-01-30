#!/usr/bin/env python3
"""
Generate contributors tracking file and HTML page.

Tracks all contributors per file/folder from git history on src-data branch.
Creates .contributors JSON file and contributors.html page.
"""

import json
import subprocess
import os
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import argparse


# Cache for GitHub API calls to avoid hitting rate limits
_github_user_cache = {}


def run_gh_command(cmd: list) -> str:
    """Run a gh CLI command and return output."""
    try:
        result = subprocess.run(
            ['gh'] + cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def get_github_user_from_commit(owner: str, repo: str, commit_hash: str) -> dict:
    """Get the actual GitHub user from a commit via gh CLI."""
    cache_key = f"{owner}/{repo}/{commit_hash}"
    if cache_key in _github_user_cache:
        return _github_user_cache[cache_key]
    
    output = run_gh_command([
        'api', f'/repos/{owner}/{repo}/commits/{commit_hash}',
        '--jq', '.author.login, .committer.login'
    ])
    
    if output:
        lines = output.strip().split('\n')
        result = {
            'author_login': lines[0] if len(lines) > 0 and lines[0] != 'null' else None,
            'committer_login': lines[1] if len(lines) > 1 and lines[1] != 'null' else None,
        }
        _github_user_cache[cache_key] = result
        return result
    
    _github_user_cache[cache_key] = {}
    return {}


def extract_orcid(text: str) -> str:
    """Extract ORCID from text (bio, website URL, HTML, etc.)."""
    if not text:
        return ''
    
    # ORCID format: 0000-0000-0000-000X (where X can be 0-9 or X)
    # Can appear as URL or just the ID
    patterns = [
        r'orcid\.org/(\d{4}-\d{4}-\d{4}-\d{3}[\dX])',  # URL format
        r'\b(\d{4}-\d{4}-\d{4}-\d{3}[\dX])\b',  # Just the ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return ''


def scrape_github_profile_for_orcid(username: str) -> str:
    """Scrape GitHub profile page HTML to find ORCID."""
    if not username:
        return ''
    
    try:
        result = subprocess.run(
            ['curl', '-s', f'https://github.com/{username}'],
            capture_output=True,
            text=True,
            timeout=15
        )
        if result.returncode == 0:
            return extract_orcid(result.stdout)
    except (subprocess.TimeoutExpired, Exception):
        pass
    
    return ''


def get_github_social_accounts(username: str) -> list:
    """Get social accounts linked to a GitHub profile."""
    if not username:
        return []
    
    output = run_gh_command([
        'api', f'/users/{username}/social_accounts',
        '--jq', '.[].url'
    ])
    
    if output:
        return [url.strip() for url in output.split('\n') if url.strip()]
    
    return []


def get_github_user_profile(username: str, try_social_accounts: bool = False) -> dict:
    """Get full GitHub user profile including name, website, bio, social accounts, etc."""
    if not username:
        return {}
    
    # Get basic profile info
    output = run_gh_command([
        'api', f'/users/{username}',
        '--jq', '[.name, .blog, .bio, .company, .location, .twitter_username] | @tsv'
    ])
    
    if not output:
        return {}
    
    parts = output.split('\t')
    name = parts[0] if len(parts) > 0 and parts[0] else None
    website = parts[1] if len(parts) > 1 and parts[1] else None
    bio = parts[2] if len(parts) > 2 and parts[2] else None
    company = parts[3] if len(parts) > 3 and parts[3] else None
    location = parts[4] if len(parts) > 4 and parts[4] else None
    twitter = parts[5] if len(parts) > 5 and parts[5] else None
    
    # Try to find ORCID - scrape profile page first (most reliable)
    orcid = scrape_github_profile_for_orcid(username)
    
    # Fallback to bio/website text
    if not orcid:
        orcid = extract_orcid(bio) or extract_orcid(website)
    
    social_accounts = []
    
    # Only try social accounts API if requested and no ORCID found yet
    if try_social_accounts and not orcid:
        social_accounts = get_github_social_accounts(username)
        for url in social_accounts:
            orcid = extract_orcid(url)
            if orcid:
                break
    
    return {
        'name': name,
        'website': website,
        'bio': bio,
        'company': company,
        'location': location,
        'twitter': twitter,
        'orcid': orcid,
        'social_accounts': social_accounts if social_accounts else None
    }


def get_repo_info_from_remote(cwd: str = None) -> tuple:
    """Extract owner and repo from git remote URL."""
    remote_url = run_git_command(['git', 'remote', 'get-url', 'origin'], cwd)
    if not remote_url:
        return None, None
    
    # Handle SSH format: git@github.com:owner/repo.git
    match = re.match(r'git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$', remote_url)
    if match:
        return match.group(1), match.group(2)
    
    # Handle HTTPS format: https://github.com/owner/repo.git
    match = re.match(r'https://github\.com/([^/]+)/([^/]+?)(?:\.git)?$', remote_url)
    if match:
        return match.group(1), match.group(2)
    
    return None, None


def run_git_command(cmd: list, cwd: str = None) -> str:
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Git command failed: {' '.join(cmd)}")
        print(f"Error: {e.stderr}")
        return ""


def get_repo_root() -> str:
    """Get the repository root directory."""
    return run_git_command(['git', 'rev-parse', '--show-toplevel'])


def get_current_branch() -> str:
    """Get the current branch name."""
    return run_git_command(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])


def branch_exists(branch: str, cwd: str = None) -> bool:
    """Check if a branch exists."""
    result = run_git_command(['git', 'rev-parse', '--verify', branch], cwd)
    return bool(result)


def get_effective_branch(preferred: str, cwd: str = None) -> str:
    """Get the effective branch - preferred if it exists, otherwise current branch."""
    if branch_exists(preferred, cwd):
        return preferred
    current = get_current_branch()
    print(f"Branch '{preferred}' not found, using current branch '{current}'")
    return current


def extract_github_username(email: str, name: str = '') -> str:
    """Extract GitHub username from email or name if possible."""
    if not email and not name:
        return ''
    
    # GitHub noreply format: username@users.noreply.github.com
    # or: 12345+username@users.noreply.github.com
    if email:
        match = re.match(r'^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$', email)
        if match:
            return match.group(1)
    
    # If name looks like a GitHub username (no spaces, lowercase-ish), use it
    if name and ' ' not in name and len(name) <= 39:
        # GitHub usernames: alphanumeric + hyphens, max 39 chars
        if re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', name):
            return name
    
    # Try email prefix as fallback (but not for generic emails)
    if email and '@' in email:
        prefix = email.split('@')[0]
        domain = email.split('@')[1].lower()
        # Skip generic email domains where prefix isn't a username
        if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'icloud.com']:
            return prefix
    
    return ''


def extract_coauthors(message: str) -> list:
    """Extract co-authors from commit message."""
    coauthors = []
    pattern = r'Co-authored-by:\s*([^<]+)\s*<([^>]+)>'
    
    for match in re.finditer(pattern, message, re.IGNORECASE):
        name = match.group(1).strip()
        email = match.group(2).strip()
        username = extract_github_username(email, name)
        coauthors.append({
            'name': name,
            'email': email,
            'username': username
        })
    
    return coauthors


def is_bot(name: str, email: str = '') -> bool:
    """Check if contributor is a bot or automated action."""
    if not name:
        return True
    
    name_lower = name.lower()
    email_lower = email.lower() if email else ''
    
    # Common bot patterns
    bot_patterns = [
        'bot',
        'github-actions',
        'github actions',
        'dependabot',
        'renovate',
        'greenkeeper',
        'semantic-release',
        'auto-commit',
        'automated',
        '[bot]',
        'actions-user',
        'web-flow',  # GitHub web UI commits
    ]
    
    for pattern in bot_patterns:
        if pattern in name_lower or pattern in email_lower:
            return True
    
    # GitHub Actions bot email
    if '41898282+github-actions' in email_lower:
        return True
    
    # noreply@github.com is usually automated
    if email_lower == 'noreply@github.com':
        return True
    
    return False


def get_commits_since(since_date: str = None, branch: str = 'src-data', cwd: str = None) -> list:
    """Get commits with file changes since a date."""
    cmd = [
        'git', 'log', branch,
        '--format=%H|%an|%ae|%aI|%s',
        '--name-status'
    ]
    
    if since_date:
        cmd.append(f'--since={since_date}')
    
    output = run_git_command(cmd, cwd)
    if not output:
        return []
    
    commits = []
    current_commit = None
    
    for line in output.split('\n'):
        if '|' in line and line.count('|') >= 4:
            # New commit line
            if current_commit:
                commits.append(current_commit)
            
            parts = line.split('|', 4)
            current_commit = {
                'hash': parts[0],
                'author_name': parts[1],
                'author_email': parts[2],
                'date': parts[3],
                'subject': parts[4] if len(parts) > 4 else '',
                'files': []
            }
        elif line and current_commit:
            # File status line (A/M/D followed by filename)
            parts = line.split('\t')
            if len(parts) >= 2:
                current_commit['files'].append(parts[1])
    
    if current_commit:
        commits.append(current_commit)
    
    return commits


def get_commit_message(commit_hash: str, cwd: str = None) -> str:
    """Get full commit message for extracting co-authors."""
    return run_git_command(['git', 'log', '-1', '--format=%B', commit_hash], cwd)


def load_contributors_file(filepath: str) -> dict:
    """Load existing .contributors file or return empty structure."""
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                # Ensure fields exist for older files
                if 'username_mappings' not in data:
                    data['username_mappings'] = {}
                if 'user_profiles' not in data:
                    data['user_profiles'] = {}
                return data
        except (json.JSONDecodeError, IOError):
            pass
    
    return {
        'last_updated': None,
        'files': {},
        'folders': {},
        'contributors': {},
        'username_mappings': {},  # email/name -> github username cache
        'user_profiles': {}  # username -> {name, website, orcid, etc.} cache
    }


def save_contributors_file(filepath: str, data: dict):
    """Save .contributors file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def add_contributor(data: dict, username: str, name: str, email: str):
    """Add or update a contributor in the global list. Merges authors and co-authors."""
    if not username or is_bot(name, email):
        return
    
    # Normalize username to lowercase for consistent matching
    username_lower = username.lower()
    
    # Check if we already have this contributor (case-insensitive)
    existing_key = None
    for key in data['contributors']:
        if key.lower() == username_lower:
            existing_key = key
            break
    
    if existing_key:
        contrib = data['contributors'][existing_key]
        contrib['commit_count'] += 1
        contrib['last_seen'] = datetime.now().isoformat()
        
        # Keep the better name (prefer full names with spaces over usernames)
        current_name = contrib.get('name', '')
        if name and ' ' in name and ' ' not in current_name:
            contrib['name'] = name
        elif name and not current_name:
            contrib['name'] = name
        
        # Track all emails seen
        if email and email not in contrib.get('emails', []):
            if 'emails' not in contrib:
                contrib['emails'] = [contrib.get('email', '')] if contrib.get('email') else []
            if email not in contrib['emails']:
                contrib['emails'].append(email)
    else:
        data['contributors'][username] = {
            'name': name if name else username,
            'email': email,
            'emails': [email] if email else [],
            'username': username,
            'first_seen': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat(),
            'commit_count': 1
        }


def add_file_contributor(data: dict, filepath: str, username: str, date: str):
    """Add contributor to a specific file."""
    if not username:
        return
    
    if filepath not in data['files']:
        data['files'][filepath] = {
            'contributors': [],
            'last_updated': date
        }
    
    if username not in data['files'][filepath]['contributors']:
        data['files'][filepath]['contributors'].append(username)
    
    # Update last_updated if this is newer
    if date > data['files'][filepath]['last_updated']:
        data['files'][filepath]['last_updated'] = date


def add_folder_contributor(data: dict, folder: str, username: str, date: str):
    """Add contributor to a folder."""
    if not username or not folder:
        return
    
    if folder not in data['folders']:
        data['folders'][folder] = {
            'contributors': [],
            'last_updated': date
        }
    
    if username not in data['folders'][folder]['contributors']:
        data['folders'][folder]['contributors'].append(username)
    
    if date > data['folders'][folder]['last_updated']:
        data['folders'][folder]['last_updated'] = date


def enrich_contributors_with_profiles(data: dict, recheck_orcid: bool = False, update_members: bool = False):
    """Fetch and cache GitHub profile data for all contributors."""
    profiles = data.get('user_profiles', {})
    contributors = data.get('contributors', {})
    
    # Find contributors without cached profiles
    to_fetch = []
    to_recheck = []
    to_update = []
    
    for username in contributors:
        username_lower = username.lower()
        if username_lower not in profiles:
            to_fetch.append(username)
        elif update_members:
            # Update all existing members
            to_update.append(username)
        elif recheck_orcid:
            # Recheck if no ORCID found previously
            cached = profiles.get(username_lower, {})
            if not cached.get('orcid'):
                to_recheck.append(username)
    
    if not to_fetch and not to_recheck and not to_update:
        return
    
    if to_fetch:
        print(f"  Fetching {len(to_fetch)} GitHub profiles...")
        
        for i, username in enumerate(to_fetch):
            if (i + 1) % 10 == 0:
                print(f"    Fetched {i + 1}/{len(to_fetch)} profiles...")
            
            profile = get_github_user_profile(username, try_social_accounts=False)
            if profile:
                _update_contributor_from_profile(data, username, profile)
    
    if to_update:
        print(f"  Updating {len(to_update)} existing profiles...")
        
        for i, username in enumerate(to_update):
            if (i + 1) % 10 == 0:
                print(f"    Updated {i + 1}/{len(to_update)} profiles...")
            
            profile = get_github_user_profile(username, try_social_accounts=False)
            if profile:
                _update_contributor_from_profile(data, username, profile)
    
    if to_recheck:
        print(f"  Rechecking {len(to_recheck)} profiles for ORCID (trying social accounts)...")
        
        for i, username in enumerate(to_recheck):
            if (i + 1) % 10 == 0:
                print(f"    Rechecked {i + 1}/{len(to_recheck)} profiles...")
            
            profile = get_github_user_profile(username, try_social_accounts=True)
            if profile and profile.get('orcid'):
                _update_contributor_from_profile(data, username, profile)
                print(f"    Found ORCID for {username}: {profile['orcid']}")


def _update_contributor_from_profile(data: dict, username: str, profile: dict):
    """Update contributor data from profile."""
    profiles = data.get('user_profiles', {})
    contributors = data.get('contributors', {})
    
    # Store with lowercase key for consistent lookup
    data['user_profiles'][username.lower()] = profile
    
    # Update contributor with profile data
    if username in contributors:
        contrib = contributors[username]
        
        # Use profile name if better (has spaces, indicating full name)
        profile_name = profile.get('name')
        current_name = contrib.get('name', '')
        if profile_name and ' ' in profile_name:
            contrib['name'] = profile_name
        
        # Add profile fields
        if profile.get('website'):
            contrib['website'] = profile['website']
        if profile.get('orcid'):
            contrib['orcid'] = profile['orcid']
        if profile.get('company'):
            contrib['company'] = profile['company']
        if profile.get('location'):
            contrib['location'] = profile['location']
        if profile.get('twitter'):
            contrib['twitter'] = profile['twitter']


def process_commits(commits: list, data: dict, owner: str = None, repo: str = None, cwd: str = None):
    """Process commits and update contributor data."""
    use_gh_api = owner and repo
    total = len(commits)
    
    for i, commit in enumerate(commits):
        # Progress indicator
        if total > 10 and (i + 1) % 10 == 0:
            print(f"  Processing commit {i + 1}/{total}...")
        
        author_name = commit['author_name']
        author_email = commit['author_email']
        commit_hash = commit['hash']
        commit_date = commit['date']
        
        # Skip bot/action commits entirely
        if is_bot(author_name, author_email):
            continue
        
        # Check if we already have a cached mapping for this email or name
        mappings = data.get('username_mappings', {})
        author_username = mappings.get(author_email) or mappings.get(author_name)
        
        # Try to get actual GitHub username from API if not cached
        if not author_username and use_gh_api:
            gh_data = get_github_user_from_commit(owner, repo, commit_hash)
            author_username = gh_data.get('author_login') or gh_data.get('committer_login')
            
            # Save mappings for future use (both email and name)
            if author_username:
                if author_email:
                    data['username_mappings'][author_email] = author_username
                if author_name:
                    data['username_mappings'][author_name] = author_username
        
        # Fallback to extracting from email/name
        if not author_username:
            author_username = extract_github_username(author_email, author_name)
        
        # Get full message for co-authors
        full_message = get_commit_message(commit_hash, cwd)
        coauthors = extract_coauthors(full_message)
        
        # Collect all contributors for this commit (authors + co-authors combined)
        all_contributors = []
        seen_usernames = set()
        
        # Add primary author
        if author_username:
            all_contributors.append({
                'name': author_name,
                'email': author_email,
                'username': author_username
            })
            seen_usernames.add(author_username.lower())
        
        # Add co-authors (skip if same as author)
        for ca in coauthors:
            if not is_bot(ca['name'], ca['email']) and ca['username']:
                if ca['username'].lower() not in seen_usernames:
                    all_contributors.append(ca)
                    seen_usernames.add(ca['username'].lower())
        
        # Add to global contributors
        for contrib in all_contributors:
            add_contributor(data, contrib['username'], contrib['name'], contrib['email'])
        
        # Process files
        for filepath in commit['files']:
            for contrib in all_contributors:
                add_file_contributor(data, filepath, contrib['username'], commit_date)
            
            # Add to folder hierarchy
            path = Path(filepath)
            for i in range(len(path.parts) - 1):
                folder = '/'.join(path.parts[:i+1])
                for contrib in all_contributors:
                    add_folder_contributor(data, folder, contrib['username'], commit_date)


def generate_html(data: dict, output_path: str, project_name: str = 'this project'):
    """Generate contributors.html page."""
    # Sort contributors by commit count
    sorted_contributors = sorted(
        data['contributors'].values(),
        key=lambda x: x.get('commit_count', 0),
        reverse=True
    )
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Contributors - {project_name}</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    margin: 0;
    padding: 40px 20px;
  }}
  .container {{
    max-width: 900px;
    margin: 0 auto;
  }}
  h1 {{
    text-align: center;
    color: #fff;
    font-size: 2.2em;
    margin-bottom: 10px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
  }}
  .subtitle {{
    text-align: center;
    color: rgba(255,255,255,0.9);
    font-size: 1.1em;
    margin-bottom: 40px;
  }}
  .contributors-grid {{
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 20px;
  }}
  .contributor {{
    background: #fff;
    border-radius: 12px;
    padding: 16px;
    width: 140px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    transition: transform 0.2s, box-shadow 0.2s;
  }}
  .contributor:hover {{
    transform: translateY(-5px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
  }}
  .contributor > a {{
    text-decoration: none;
    color: inherit;
  }}
  .contributor img {{
    width: 80px;
    height: 80px;
    border-radius: 50%;
    margin-bottom: 12px;
    border: 3px solid #eee;
  }}
  .contributor-name {{
    font-weight: 600;
    font-size: 0.95em;
    color: #333;
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .contributor-username {{
    font-size: 0.8em;
    color: #666;
  }}
  .contributor-commits {{
    font-size: 0.75em;
    color: #999;
    margin-top: 6px;
  }}
  .contributor-links {{
    margin-top: 8px;
    display: flex;
    justify-content: center;
    gap: 8px;
    align-items: center;
  }}
  .contributor-links a {{
    color: #666;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
  }}
  .contributor-links a:hover {{
    opacity: 0.7;
  }}
  .contributor-links a svg,
  .contributor-links a img {{
    width: 16px;
    height: 16px;
  }}
  .stats {{
    text-align: center;
    color: rgba(255,255,255,0.8);
    margin-bottom: 30px;
    font-size: 0.95em;
  }}
  .footer {{
    text-align: center;
    color: rgba(255,255,255,0.7);
    margin-top: 40px;
    font-size: 0.85em;
  }}
</style>
</head>
<body>
<div class="container">
  <h1>With Thanks to All Our Contributors</h1>
  <p class="subtitle">The people who make {project_name} possible</p>
  <p class="stats">{len(sorted_contributors)} contributors</p>
  <div class="contributors-grid">
'''
    
    for contrib in sorted_contributors:
        username = contrib.get('username', '')
        name = contrib.get('name', username)
        commits = contrib.get('commit_count', 0)
        website = contrib.get('website', '')
        orcid = contrib.get('orcid', '')
        avatar_url = f'https://github.com/{username}.png?size=160'
        profile_url = f'https://github.com/{username}'
        
        # Ensure website has protocol
        if website and not website.startswith('http'):
            website = f'https://{website}'
        
        # Build links section (outside the main link to avoid nested anchors)
        links_html = ''
        if website or orcid:
            links_html = '<div class="contributor-links">'
            if website:
                # SVG globe icon
                links_html += f'<a href="{website}" target="_blank" title="Website"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg></a>'
            if orcid:
                links_html += f'<a href="https://orcid.org/{orcid}" target="_blank" title="ORCID: {orcid}"><img src="https://orcid.org/assets/icons/favicon.ico" alt="ORCID" style="width:22px;height:22px;position:relative;top:5px;"></a>'
            links_html += '</div>'
        
        html += f'''    <div class="contributor">
      <a href="{profile_url}" target="_blank">
        <img src="{avatar_url}" alt="{name}" onerror="this.src='https://github.githubassets.com/images/gravatars/gravatar-user-420.png'">
        <div class="contributor-name" title="{name}">{name}</div>
        <div class="contributor-username">@{username}</div>
      </a>
      <div class="contributor-commits">{commits} commit{'s' if commits != 1 else ''}</div>
      {links_html}
    </div>
'''
    
    html += f'''  </div>
  <p class="footer">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</p>
</div>
</body>
</html>
'''
    
    with open(output_path, 'w') as f:
        f.write(html)


def generate_markdown(data: dict, output_path: str, project_name: str = 'this project'):
    """Generate contributors.md page with styled HTML boxes."""
    # Sort contributors by commit count
    sorted_contributors = sorted(
        data['contributors'].values(),
        key=lambda x: x.get('commit_count', 0),
        reverse=True
    )
    
    md = f'''# With Thanks to All Our Contributors

The people who make {project_name} possible — {len(sorted_contributors)} contributors

<div style="display: flex; flex-wrap: wrap; gap: 16px; justify-content: center; margin-bottom: 24px;">
'''
    
    for contrib in sorted_contributors:
        username = contrib.get('username', '')
        name = contrib.get('name', username)
        commits = contrib.get('commit_count', 0)
        website = contrib.get('website', '')
        orcid = contrib.get('orcid', '')
        avatar_url = f'https://github.com/{username}.png?size=100'
        profile_url = f'https://github.com/{username}'
        
        # Ensure website has protocol
        if website and not website.startswith('http'):
            website = f'https://{website}'
        
        # Build extra links
        links_html = ''
        if website or orcid:
            links_html = '<div style="margin-top: 8px; display: flex; justify-content: center; gap: 8px; align-items: center;">'
            if website:
                links_html += f'<a href="{website}" title="Website" style="color: #666; text-decoration: none; display: inline-flex; align-items: center;"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg></a>'
            if orcid:
                links_html += f'<a href="https://orcid.org/{orcid}" title="ORCID: {orcid}" style="display: inline-flex; align-items: center;"><img src="https://orcid.org/assets/icons/favicon.ico" alt="ORCID" width="16" height="16"></a>'
            links_html += '</div>'
        
        md += f'''<div style="background: #fff; border-radius: 12px; padding: 16px; width: 140px; text-align: center; box-shadow: 0 4px 15px rgba(0,0,0,0.1);">
  <a href="{profile_url}" style="text-decoration: none; color: inherit;">
    <img src="{avatar_url}" width="80" height="80" style="border-radius: 50%; border: 3px solid #eee;" alt="{name}">
    <div style="font-weight: 600; font-size: 0.95em; color: #333; margin: 8px 0 4px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{name}">{name}</div>
    <div style="font-size: 0.8em; color: #666;">@{username}</div>
  </a>
  <div style="font-size: 0.75em; color: #999; margin-top: 6px;">{commits} commit{'s' if commits != 1 else ''}</div>
  {links_html}
</div>
'''
    
    md += f'''</div>

---
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*
'''
    
    with open(output_path, 'w') as f:
        f.write(md)


def main():
    parser = argparse.ArgumentParser(description='Generate contributors tracking and HTML/Markdown page')
    parser.add_argument('--branch', default=None, help='Single branch to analyze (overrides default)')
    parser.add_argument('--branches', nargs='+', default=['src-data', 'docs'], help='Multiple branches to analyze (default: src-data docs)')
    parser.add_argument('--output', default='.contributors', help='Output JSON file (default: .contributors)')
    parser.add_argument('--html', default='contributors.html', help='Output HTML file (default: contributors.html)')
    parser.add_argument('--md', default=None, help='Output Markdown file (e.g., CONTRIBUTORS.md)')
    parser.add_argument('--full', action='store_true', help='Full scan (ignore existing .contributors)')
    parser.add_argument('--recheck-orcid', action='store_true', help='Re-fetch profiles for contributors without ORCID (tries social accounts API)')
    parser.add_argument('--update-members', action='store_true', help='Re-fetch profile data (name, website, ORCID) for all existing contributors')
    args = parser.parse_args()
    
    repo_root = get_repo_root()
    if not repo_root:
        print("Error: Not in a git repository")
        return 1
    
    # Determine which branches to analyze
    if args.branch:
        branches_to_check = [args.branch]
    else:
        branches_to_check = args.branches
    
    contributors_path = os.path.join(repo_root, args.output)
    html_path = os.path.join(repo_root, args.html)
    
    # Get repo info for GitHub API lookups and project name
    owner, repo = get_repo_info_from_remote(repo_root)
    project_name = repo or os.path.basename(repo_root)
    
    # Load existing data or start fresh
    if args.full:
        data = {
            'last_updated': None,
            'files': {},
            'folders': {},
            'contributors': {},
            'username_mappings': {},
            'user_profiles': {}
        }
        print("Starting full scan...")
    else:
        data = load_contributors_file(contributors_path)
        if data['last_updated']:
            print(f"Updating from {data['last_updated']}...")
            print(f"  (using {len(data.get('username_mappings', {}))} cached username mappings)")
        else:
            print("No existing data, starting full scan...")
    
    if owner and repo:
        print(f"Using GitHub API for {owner}/{repo}")
    else:
        print("Could not detect GitHub repo, falling back to git log only")
    
    # Get commits since last update from all branches
    since_date = data['last_updated'] if not args.full else None
    total_commits = 0
    
    for branch_name in branches_to_check:
        branch = get_effective_branch(branch_name, repo_root)
        if branch != branch_name:
            print(f"Branch '{branch_name}' not found, using '{branch}' instead")
        
        commits = get_commits_since(since_date, branch, repo_root)
        if commits:
            print(f"Processing {len(commits)} commits on branch '{branch}'...")
            process_commits(commits, data, owner, repo, repo_root)
            total_commits += len(commits)
        else:
            print(f"No new commits on branch '{branch}'")
    
    print(f"Processed {total_commits} total commits across {len(branches_to_check)} branch(es)")
    
    # Enrich contributors with GitHub profile data
    enrich_contributors_with_profiles(data, recheck_orcid=args.recheck_orcid, update_members=args.update_members)
    
    # Update timestamp
    data['last_updated'] = datetime.now().isoformat()
    
    # Save JSON
    save_contributors_file(contributors_path, data)
    print(f"Saved {contributors_path}")
    print(f"  ({len(data.get('username_mappings', {}))} username mappings cached)")
    print(f"  ({len(data.get('user_profiles', {}))} user profiles cached)")
    
    # Generate HTML
    generate_html(data, html_path, project_name)
    print(f"Generated {html_path}")
    
    # Generate Markdown if requested
    if args.md:
        md_path = os.path.join(repo_root, args.md)
        generate_markdown(data, md_path, project_name)
        print(f"Generated {md_path}")
    
    print(f"\nTotal contributors: {len(data['contributors'])}")
    print(f"Total files tracked: {len(data['files'])}")
    print(f"Total folders tracked: {len(data['folders'])}")
    
    return 0


if __name__ == '__main__':
    exit(main())
