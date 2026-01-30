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


def extract_github_username(email: str) -> str:
    """Extract GitHub username from email if possible."""
    if not email:
        return ''
    
    # GitHub noreply format: username@users.noreply.github.com
    # or: 12345+username@users.noreply.github.com
    match = re.match(r'^(?:\d+\+)?([^@]+)@users\.noreply\.github\.com$', email)
    if match:
        return match.group(1)
    
    # Try email prefix as fallback
    return email.split('@')[0] if '@' in email else ''


def extract_coauthors(message: str) -> list:
    """Extract co-authors from commit message."""
    coauthors = []
    pattern = r'Co-authored-by:\s*([^<]+)\s*<([^>]+)>'
    
    for match in re.finditer(pattern, message, re.IGNORECASE):
        name = match.group(1).strip()
        email = match.group(2).strip()
        username = extract_github_username(email)
        coauthors.append({
            'name': name,
            'email': email,
            'username': username
        })
    
    return coauthors


def is_bot(name: str) -> bool:
    """Check if contributor is a bot."""
    if not name:
        return True
    return 'bot' in name.lower()


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
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    
    return {
        'last_updated': None,
        'files': {},
        'folders': {},
        'contributors': {}
    }


def save_contributors_file(filepath: str, data: dict):
    """Save .contributors file."""
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)


def add_contributor(data: dict, username: str, name: str, email: str):
    """Add or update a contributor in the global list."""
    if not username or is_bot(name):
        return
    
    if username not in data['contributors']:
        data['contributors'][username] = {
            'name': name,
            'email': email,
            'username': username,
            'first_seen': datetime.now().isoformat(),
            'commit_count': 0
        }
    
    data['contributors'][username]['commit_count'] += 1
    data['contributors'][username]['last_seen'] = datetime.now().isoformat()
    
    # Update name if we have a better one
    if name and not data['contributors'][username].get('name'):
        data['contributors'][username]['name'] = name


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


def process_commits(commits: list, data: dict, cwd: str = None):
    """Process commits and update contributor data."""
    for commit in commits:
        author_name = commit['author_name']
        author_email = commit['author_email']
        author_username = extract_github_username(author_email)
        commit_date = commit['date']
        
        # Get full message for co-authors
        full_message = get_commit_message(commit['hash'], cwd)
        coauthors = extract_coauthors(full_message)
        
        # Collect all contributors for this commit
        all_contributors = []
        
        if not is_bot(author_name) and author_username:
            all_contributors.append({
                'name': author_name,
                'email': author_email,
                'username': author_username
            })
        
        for ca in coauthors:
            if not is_bot(ca['name']) and ca['username']:
                all_contributors.append(ca)
        
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


def generate_html(data: dict, output_path: str):
    """Generate contributors.html page."""
    # Sort contributors by commit count
    sorted_contributors = sorted(
        data['contributors'].values(),
        key=lambda x: x.get('commit_count', 0),
        reverse=True
    )
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Contributors - CMIP-LD</title>
<style>
  * { box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    margin: 0;
    padding: 40px 20px;
  }
  .container {
    max-width: 900px;
    margin: 0 auto;
  }
  h1 {
    text-align: center;
    color: #fff;
    font-size: 2.2em;
    margin-bottom: 10px;
    text-shadow: 0 2px 4px rgba(0,0,0,0.2);
  }
  .subtitle {
    text-align: center;
    color: rgba(255,255,255,0.9);
    font-size: 1.1em;
    margin-bottom: 40px;
  }
  .contributors-grid {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 20px;
  }
  .contributor {
    background: #fff;
    border-radius: 12px;
    padding: 16px;
    width: 140px;
    text-align: center;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    transition: transform 0.2s, box-shadow 0.2s;
    text-decoration: none;
    color: inherit;
  }
  .contributor:hover {
    transform: translateY(-5px);
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
  }
  .contributor img {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    margin-bottom: 12px;
    border: 3px solid #eee;
  }
  .contributor-name {
    font-weight: 600;
    font-size: 0.95em;
    color: #333;
    margin-bottom: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .contributor-username {
    font-size: 0.8em;
    color: #666;
  }
  .contributor-commits {
    font-size: 0.75em;
    color: #999;
    margin-top: 6px;
  }
  .stats {
    text-align: center;
    color: rgba(255,255,255,0.8);
    margin-bottom: 30px;
    font-size: 0.95em;
  }
  .footer {
    text-align: center;
    color: rgba(255,255,255,0.7);
    margin-top: 40px;
    font-size: 0.85em;
  }
</style>
</head>
<body>
<div class="container">
  <h1>🙏 With Thanks to All Our Contributors</h1>
  <p class="subtitle">The people who make CMIP-LD possible</p>
  <p class="stats">''' + f'{len(sorted_contributors)} contributors' + '''</p>
  <div class="contributors-grid">
'''
    
    for contrib in sorted_contributors:
        username = contrib.get('username', '')
        name = contrib.get('name', username)
        commits = contrib.get('commit_count', 0)
        avatar_url = f'https://github.com/{username}.png?size=160'
        profile_url = f'https://github.com/{username}'
        
        html += f'''    <a href="{profile_url}" target="_blank" class="contributor">
      <img src="{avatar_url}" alt="{name}" onerror="this.src='https://github.githubassets.com/images/gravatars/gravatar-user-420.png'">
      <div class="contributor-name" title="{name}">{name}</div>
      <div class="contributor-username">@{username}</div>
      <div class="contributor-commits">{commits} commit{'s' if commits != 1 else ''}</div>
    </a>
'''
    
    html += '''  </div>
  <p class="footer">Last updated: ''' + datetime.now().strftime('%Y-%m-%d %H:%M UTC') + '''</p>
</div>
</body>
</html>
'''
    
    with open(output_path, 'w') as f:
        f.write(html)


def main():
    parser = argparse.ArgumentParser(description='Generate contributors tracking and HTML page')
    parser.add_argument('--branch', default='src-data', help='Branch to analyze (default: src-data)')
    parser.add_argument('--output', default='.contributors', help='Output JSON file (default: .contributors)')
    parser.add_argument('--html', default='contributors.html', help='Output HTML file (default: contributors.html)')
    parser.add_argument('--full', action='store_true', help='Full scan (ignore existing .contributors)')
    args = parser.parse_args()
    
    repo_root = get_repo_root()
    if not repo_root:
        print("Error: Not in a git repository")
        return 1
    
    contributors_path = os.path.join(repo_root, args.output)
    html_path = os.path.join(repo_root, args.html)
    
    # Load existing data or start fresh
    if args.full:
        data = {
            'last_updated': None,
            'files': {},
            'folders': {},
            'contributors': {}
        }
        print("Starting full scan...")
    else:
        data = load_contributors_file(contributors_path)
        if data['last_updated']:
            print(f"Updating from {data['last_updated']}...")
        else:
            print("No existing data, starting full scan...")
    
    # Get commits since last update
    since_date = data['last_updated'] if not args.full else None
    commits = get_commits_since(since_date, args.branch, repo_root)
    
    print(f"Processing {len(commits)} commits...")
    
    # Process commits
    process_commits(commits, data, repo_root)
    
    # Update timestamp
    data['last_updated'] = datetime.now().isoformat()
    
    # Save JSON
    save_contributors_file(contributors_path, data)
    print(f"Saved {contributors_path}")
    
    # Generate HTML
    generate_html(data, html_path)
    print(f"Generated {html_path}")
    
    print(f"\nTotal contributors: {len(data['contributors'])}")
    print(f"Total files tracked: {len(data['files'])}")
    print(f"Total folders tracked: {len(data['folders'])}")
    
    return 0


if __name__ == '__main__':
    exit(main())
