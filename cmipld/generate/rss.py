#!/usr/bin/env python3
"""
RSS Feed Generator for CMIP-LD Repositories

Generates an RSS feed from git commits and releases for a CMIP-LD repository.
Includes author avatars, co-author support, and release tracking.

Usage:
    rss                           # Generate RSS (since last release or 30 days)
    rss --since 2024-01-01        # Generate RSS since specific date
    rss --output feed.xml         # Output to specific file
    rss --branch src-data         # Specify branch (default: src-data)
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

import requests

from cmipld.locations import reverse_direct, direct


# =============================================================================
# Repository Information
# =============================================================================

def get_repo_info() -> dict:
    """Get repository information using gh CLI."""
    try:
        output = os.popen("gh repo view --json name,url,owner").read()
        return json.loads(output)
    except (json.JSONDecodeError, Exception) as e:
        print(f"Warning: Could not get repo info via gh: {e}", file=sys.stderr)
        return {}


def get_repo_url_from_git() -> str:
    """Get repository URL from git remote."""
    url = os.popen('git remote get-url origin').read().strip()
    # Convert SSH to HTTPS format
    if url.startswith('git@github.com:'):
        url = url.replace('git@github.com:', 'https://github.com/')
    return url.replace('.git', '').rstrip('/')


def get_repository_prefix(repo_url: str) -> str:
    """Get the CMIP-LD prefix for the repository."""
    # Normalize URL for lookup
    normalized = repo_url.rstrip('/') + '/'
    
    # Try direct lookup
    for prefix, url in direct.items():
        if normalized == url or repo_url == url.rstrip('/'):
            return prefix
    
    # Fallback to repo name
    return repo_url.split('/')[-1]


def get_owner_repo(repo_url: str) -> tuple:
    """Extract owner and repo name from URL."""
    parts = repo_url.rstrip('/').split('/')
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return None, None


# =============================================================================
# GitHub API Functions
# =============================================================================

def get_last_release_date(owner: str, repo: str) -> datetime | None:
    """Get the date of the last release from GitHub API."""
    try:
        url = f'https://api.github.com/repos/{owner}/{repo}/releases/latest'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            published_at = data.get('published_at')
            if published_at:
                return datetime.fromisoformat(published_at.replace('Z', '+00:00'))
    except Exception as e:
        print(f"Warning: Could not fetch last release date: {e}", file=sys.stderr)
    return None


def get_releases(owner: str, repo: str, since: datetime | None = None) -> list:
    """Get releases from GitHub API."""
    releases = []
    try:
        url = f'https://api.github.com/repos/{owner}/{repo}/releases'
        response = requests.get(url, params={'per_page': 100}, timeout=10)
        if response.status_code == 200:
            for release in response.json():
                published_at = release.get('published_at')
                if not published_at:
                    continue
                    
                release_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                if since and release_date.replace(tzinfo=None) < since:
                    continue
                    
                releases.append({
                    'type': 'release',
                    'tag': release.get('tag_name', ''),
                    'name': release.get('name') or release.get('tag_name', ''),
                    'body': release.get('body', ''),
                    'date': release_date.replace(tzinfo=None),
                    'url': release.get('html_url', ''),
                    'author': release.get('author', {}),
                    'prerelease': release.get('prerelease', False),
                    'draft': release.get('draft', False),
                })
    except Exception as e:
        print(f"Warning: Could not fetch releases: {e}", file=sys.stderr)
    return releases


def get_commit_details(owner: str, repo: str, commit_sha: str) -> dict | None:
    """Get detailed commit info including author avatar from GitHub API."""
    try:
        url = f'https://api.github.com/repos/{owner}/{repo}/commits/{commit_sha}'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


def get_github_avatar_url(username: str, size: int = 32) -> str:
    """Get GitHub avatar URL for a username."""
    if username:
        return f'https://github.com/{username}.png?size={size}'
    return ''


# =============================================================================
# Git Log Parsing
# =============================================================================

def get_context_directories() -> set:
    """Find directories containing _context files."""
    context_dirs = set()
    for root, dirs, files in os.walk("."):
        if "_context" in files:
            context_dirs.add(Path(root).resolve())
    return context_dirs


def parse_git_log(branch: str, since_date: str) -> list:
    """Parse git log for commits with file changes."""
    cmd = f"git log {branch} --name-status --pretty=format:'%H|%an|%ae|%ad|%s' --date=iso --since='{since_date}' -- '*.json'"
    output = os.popen(cmd).read()
    
    context_dirs = get_context_directories()
    commits = []
    current = None
    
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        
        # Check for commit header (40-char hash with pipe)
        if '|' in line:
            parts = line.split('|', 4)
            if len(parts[0]) == 40:
                # Save previous commit
                if current and current['files']:
                    commits.append(current)
                
                current = {
                    'type': 'commit',
                    'hash': parts[0],
                    'author_name': parts[1] if len(parts) > 1 else 'Unknown',
                    'author_email': parts[2] if len(parts) > 2 else '',
                    'date_str': parts[3] if len(parts) > 3 else '',
                    'subject': parts[4] if len(parts) > 4 else '',
                    'files': [],
                    'branch': branch,
                }
                continue
        
        # Parse file status line
        if current:
            file_info = parse_file_line(line, context_dirs)
            if file_info:
                current['files'].append(file_info)
    
    # Don't forget the last commit
    if current and current['files']:
        commits.append(current)
    
    return commits


def parse_file_line(line: str, context_dirs: set) -> dict | None:
    """Parse a file status line from git log."""
    parts = line.split()
    if not parts:
        return None
    
    status = parts[0]
    
    # Handle renames (R100, R090, etc.)
    if status.startswith('R') and len(parts) >= 3:
        old_path, new_path = parts[1], parts[2]
        file_path = Path(new_path).resolve()
    elif len(parts) >= 2:
        old_path = parts[1]
        new_path = None
        file_path = Path(old_path).resolve()
    else:
        return None
    
    # Filter by context directories
    if not any(
        file_path.is_relative_to(d) or file_path.parent.resolve() == d
        for d in context_dirs
    ):
        return None
    
    return {
        'status': status[0],  # Normalize to single char (A, M, D, R)
        'file': old_path,
        'new_file': new_path,
    }


def extract_coauthors(commit_body: str) -> list:
    """Extract co-authors from commit message body."""
    if not commit_body:
        return []
    
    coauthors = []
    pattern = r'Co-authored-by:\s*([^<]+)\s*<([^>]+)>'
    
    for match in re.finditer(pattern, commit_body, re.IGNORECASE):
        name, email = match.groups()
        username = extract_github_username(email)
        coauthors.append({
            'name': name.strip(),
            'email': email.strip(),
            'username': username,
        })
    
    return coauthors


def extract_github_username(email: str) -> str | None:
    """Extract GitHub username from noreply email."""
    if '@users.noreply.github.com' in email:
        username = email.split('@')[0]
        if '+' in username:
            username = username.split('+')[1]
        return username
    return None


# =============================================================================
# RSS Generation
# =============================================================================

# Color mapping for each prefix
PREFIX_COLORS = {
    'universal': '#e74c3c',
    'cmip7': '#3498db',
    'cf': '#2ecc71',
    'vr': '#9b59b6',
    'cmip6plus': '#f39c12',
    'emd': '#1abc9c',
}

def generate_rss(
    items: list,
    repo_name: str,
    repo_url: str,
    prefix: str,
    branch: str,
    owner: str,
    repo: str,
) -> str:
    """Generate RSS 2.0 feed XML."""
    
    rss = Element('rss', version='2.0')
    rss.set('xmlns:atom', 'http://www.w3.org/2005/Atom')
    rss.set('xmlns:dc', 'http://purl.org/dc/elements/1.1/')
    rss.set('xmlns:cmip', 'https://wcrp-cmip.github.io/CMIP-LD/rss/')
    
    channel = SubElement(rss, 'channel')
    
    # Channel metadata with prefix
    SubElement(channel, 'title').text = f'[{prefix}] {repo_name} Updates'
    SubElement(channel, 'link').text = repo_url
    SubElement(channel, 'description').text = f'Commits and releases for {prefix} ({repo_name})'
    SubElement(channel, 'language').text = 'en-us'
    SubElement(channel, 'lastBuildDate').text = format_rss_date(datetime.utcnow())
    
    # Custom channel properties
    SubElement(channel, 'cmip:prefix').text = prefix
    SubElement(channel, 'cmip:color').text = PREFIX_COLORS.get(prefix, '#666666')
    
    # Atom self-link
    atom_link = SubElement(channel, 'atom:link')
    atom_link.set('href', f'{repo_url}/rss.xml')
    atom_link.set('rel', 'self')
    atom_link.set('type', 'application/rss+xml')
    
    # Sort items by date (newest first)
    sorted_items = sorted(items, key=lambda x: x.get('date', datetime.min), reverse=True)
    
    # Add items
    for item_data in sorted_items:
        # Skip commits with 'no-rss' in subject or body
        if item_data.get('type') != 'release':
            subject = item_data.get('subject', '')
            body = item_data.get('body', '')
            if should_skip_commit(subject, body):
                continue
        
        item = SubElement(channel, 'item')
        
        if item_data.get('type') == 'release':
            build_release_item(item, item_data, repo_url, prefix)
        else:
            build_commit_item(item, item_data, repo_url, owner, repo, prefix)
    
    # Pretty print XML
    xml_str = tostring(rss, encoding='unicode')
    dom = minidom.parseString(xml_str)
    return dom.toprettyxml(indent='  ')


def is_bot(name: str) -> bool:
    """Check if a name belongs to a bot."""
    return 'bot' in name.lower()


def should_skip_commit(subject: str, body: str = '') -> bool:
    """Check if commit should be excluded from RSS feed."""
    text = f'{subject} {body}'.lower()
    return 'no-rss' in text


def build_release_item(item: Element, data: dict, repo_url: str, prefix: str):
    """Build RSS item for a release."""
    tag = data.get('tag', '')
    name = data.get('name', tag)
    is_prerelease = data.get('prerelease', False)
    
    # Title with emoji indicator (no prefix)
    emoji = '🧪' if is_prerelease else '🚀'
    release_type = 'Pre-release' if is_prerelease else 'Release'
    SubElement(item, 'title').text = f'{emoji} {release_type} {name}'
    
    # Links
    release_url = data.get('url') or f'{repo_url}/releases/tag/{tag}'
    SubElement(item, 'link').text = release_url
    SubElement(item, 'guid').text = release_url
    
    # Date
    SubElement(item, 'pubDate').text = format_rss_date(data['date'])
    
    # Author (skip bots)
    author = data.get('author', {})
    author_login = author.get('login', '') if author else ''
    
    # Check if author is a bot or missing
    if author and author_login and not is_bot(author_login):
        profile_url = f'https://github.com/{author_login}'
        SubElement(item, 'dc:creator').text = author_login
        
        # Build description (no images to avoid RSS reader preview issues)
        desc_lines = [
            f'<p><strong>Release {escape_html(tag)}</strong></p>',
            f'<p>👤 <a href="{profile_url}" target="_blank">{escape_html(author_login)}</a></p>',
        ]
    else:
        # No author or bot author
        desc_lines = [
            f'<p><strong>Release {escape_html(tag)}</strong></p>',
        ]
        
    if data.get('body'):
        # Truncate and escape body
        body = data['body'][:1000]
        if len(data['body']) > 1000:
            body += '...'
        desc_lines.append(f'<pre style="white-space:pre-wrap;">{escape_html(body)}</pre>')
    
    desc_lines.append(f'<p><a href="{release_url}">View release on GitHub →</a></p>')
    SubElement(item, 'description').text = '\n'.join(desc_lines)


def build_commit_item(item: Element, data: dict, repo_url: str, owner: str, repo: str, prefix: str):
    """Build RSS item for a commit."""
    commit_hash = data['hash']
    short_hash = commit_hash[:7]
    subject = data.get('subject', 'No message')
    branch = data.get('branch', 'main')
    
    # Calculate folder changes first (needed for title)
    files = data.get('files', [])
    folder_counts = defaultdict(lambda: {'A': 0, 'M': 0, 'D': 0, 'R': 0})
    
    for f in files:
        folder = Path(f['file']).parent.name or 'root'
        status = f['status']
        if status in folder_counts[folder]:
            folder_counts[folder][status] += 1
    
    # Build title with folder changes (no prefix)
    if folder_counts:
        folder_parts = []
        for folder in sorted(folder_counts.keys()):
            counts = folder_counts[folder]
            # Format folder name: replace _ with space, title case
            display_name = folder.replace('_', ' ').title()
            
            # Build change indicators (same symbols as description: + ~ - ↻)
            changes = []
            if counts['A'] > 0:
                changes.append(f"+{counts['A']}")
            if counts['M'] > 0:
                changes.append(f"~{counts['M']}")
            if counts['D'] > 0:
                changes.append(f"-{counts['D']}")
            if counts['R'] > 0:
                changes.append(f"↻{counts['R']}")
            
            if changes:
                folder_parts.append(f"{' '.join(changes)} {display_name}")
            else:
                folder_parts.append(display_name)
        
        # If more than 2 folders, simplify
        if len(folder_parts) > 2:
            SubElement(item, 'title').text = f"{len(folder_parts)} categories updated"
        else:
            SubElement(item, 'title').text = ', '.join(folder_parts)
    else:
        SubElement(item, 'title').text = subject
    
    # Correct commit URL
    commit_url = f'{repo_url}/commit/{commit_hash}'
    SubElement(item, 'link').text = commit_url
    SubElement(item, 'guid').text = commit_url
    
    # Parse date
    date_str = data.get('date_str', '')
    try:
        commit_date = datetime.strptime(date_str[:19], '%Y-%m-%d %H:%M:%S')
    except (ValueError, IndexError):
        commit_date = datetime.utcnow()
    data['date'] = commit_date  # Store for sorting
    
    SubElement(item, 'pubDate').text = format_rss_date(commit_date)
    
    # Collect all contributors (author + co-authors)
    contributors = []
    
    # Primary author
    author_name = data.get('author_name', 'Unknown')
    author_email = data.get('author_email', '')
    author_username = extract_github_username(author_email)
    
    if not is_bot(author_name):
        contributors.append({
            'name': author_name,
            'email': author_email,
            'username': author_username,
        })
    
    # Get co-authors and full commit message from API
    commit_body = ''
    commit_details = get_commit_details(owner, repo, commit_hash)
    if commit_details:
        commit_message = commit_details.get('commit', {}).get('message', '')
        coauthors = extract_coauthors(commit_message)
        
        # Extract body (everything after first line)
        message_lines = commit_message.split('\n', 1)
        if len(message_lines) > 1:
            commit_body = message_lines[1].strip()
            # Remove co-author lines from body
            commit_body = '\n'.join(
                line for line in commit_body.split('\n')
                if not line.strip().lower().startswith('co-authored-by:')
            ).strip()
        
        for ca in coauthors:
            if not is_bot(ca['name']):
                contributors.append(ca)
    
    # Set dc:creator for primary author
    if contributors:
        SubElement(item, 'dc:creator').text = contributors[0]['name']
        
        # Add all contributor avatars as cmip:avatar elements
        for contributor in contributors:
            username = contributor.get('username')
            if username:
                avatar_el = SubElement(item, 'cmip:avatar')
                avatar_el.text = get_github_avatar_url(username)
                avatar_el.set('username', username)
                avatar_el.set('name', contributor['name'])
    
    # Build description
    desc_lines = ['<div style="font-family:system-ui,sans-serif;">']
    
    # Commit title first
    desc_lines.append(f'<p style="margin:0 0 12px 0;"><strong>{escape_html(subject)}</strong></p>')
    
    # Commit body if present
    if commit_body:
        desc_lines.append(f'<p style="margin:0 0 12px 0;color:#555;">{escape_html(commit_body)}</p>')
    
    # Contributors section with avatar icons and hyperlinks
    if contributors:
        desc_lines.append('<p style="margin:0 0 12px 0;">')
        
        for i, c in enumerate(contributors):
            username = c.get('username')
            name = c['name']
            avatar_url = get_github_avatar_url(username) if username else ''
            profile_url = f'https://github.com/{username}' if username else ''
            
            if i > 0:
                desc_lines.append(' ')
            
            # Avatar with link
            if avatar_url and profile_url:
                desc_lines.append(
                    f'<a href="{profile_url}" target="_blank" style="text-decoration:none;">'
                    f'<img src="{avatar_url}" width="20" height="20" '
                    f'title="{escape_html(name)}" '
                    f'style="border-radius:50%;vertical-align:middle;" />'
                    f'</a>'
                )
        
        # Names with links
        desc_lines.append(' ')
        name_parts = []
        for c in contributors:
            username = c.get('username')
            name = c['name']
            if username:
                name_parts.append(f'<a href="https://github.com/{username}" target="_blank">{escape_html(name)}</a>')
            else:
                name_parts.append(escape_html(name))
        
        if len(name_parts) == 1:
            desc_lines.append(name_parts[0])
        elif len(name_parts) == 2:
            desc_lines.append(f'{name_parts[0]} &amp; {name_parts[1]}')
        else:
            desc_lines.append(f'{", ".join(name_parts[:-1])} &amp; {name_parts[-1]}')
        
        desc_lines.append('</p>')
    
    # File changes summary
    if folder_counts:
        
        desc_lines.append('<div style="margin-top:12px;">')
        desc_lines.append(f'<strong>Changes on {branch}:</strong>')
        desc_lines.append('<ul style="margin:8px 0;padding-left:20px;">')
        
        for folder, counts in sorted(folder_counts.items()):
            # Format folder name: replace _ with space, title case
            display_name = folder.replace('_', ' ').title()
            
            parts = []
            if counts['A'] > 0:
                parts.append(f'<span style="color:#22863a;">+{counts["A"]}</span>')
            if counts['M'] > 0:
                parts.append(f'<span style="color:#b08800;">~{counts["M"]}</span>')
            if counts['D'] > 0:
                parts.append(f'<span style="color:#cb2431;">-{counts["D"]}</span>')
            if counts['R'] > 0:
                parts.append(f'<span style="color:#6f42c1;">↻{counts["R"]}</span>')
            
            if parts:
                desc_lines.append(f'<li><code>{escape_html(display_name)}</code> ({" ".join(parts)})</li>')
        
        desc_lines.append('</ul>')
        desc_lines.append('</div>')
    
    # Link to commit
    desc_lines.append(
        f'<p style="margin-top:12px;">'
        f'<a href="{commit_url}">View commit {short_hash} on GitHub →</a>'
        f'</p>'
    )
    desc_lines.append('</div>')
    
    SubElement(item, 'description').text = '\n'.join(desc_lines)


def format_rss_date(dt: datetime) -> str:
    """Format datetime for RSS pubDate."""
    return dt.strftime('%a, %d %b %Y %H:%M:%S +0000')


def escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate RSS feed for CMIP-LD repository commits and releases',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rss                             # Since last release or 30 days
  rss --since 2024-01-01          # Since specific date  
  rss --branch main               # Different branch
  rss --output docs/feed.xml      # Custom output path
        """
    )
    
    parser.add_argument(
        '--since', '-s',
        help='Start date (YYYY-MM-DD). Default: last release date or 30 days ago'
    )
    parser.add_argument(
        '--branch', '-b',
        default='src-data',
        help='Git branch to track (default: src-data)'
    )
    parser.add_argument(
        '--output', '-o',
        default='rss.xml',
        help='Output file path (default: rss.xml)'
    )
    parser.add_argument(
        '--no-releases',
        action='store_true',
        help='Exclude releases from feed'
    )
    
    args = parser.parse_args()
    
    # Get repository information
    print('🔍 Getting repository information...')
    repo_info = get_repo_info()
    repo_url = repo_info.get('url') or get_repo_url_from_git()
    repo_name = repo_info.get('name') or repo_url.split('/')[-1]
    owner, repo = get_owner_repo(repo_url)
    
    # Get CMIP-LD prefix
    prefix = get_repository_prefix(repo_url)
    print(f'📦 Repository: [{prefix}] {repo_name}')
    print(f'🔗 URL: {repo_url}')
    
    # Determine since date
    if args.since:
        since_date = args.since
        print(f'📅 Using provided date: {since_date}')
    else:
        # Try to get last release date
        last_release = get_last_release_date(owner, repo) if owner and repo else None
        if last_release:
            since_date = last_release.strftime('%Y-%m-%d')
            print(f'📅 Using last release date: {since_date}')
        else:
            # Fallback to 30 days ago
            fallback = datetime.utcnow() - timedelta(days=30)
            since_date = fallback.strftime('%Y-%m-%d')
            print(f'📅 No releases found, using 30 days ago: {since_date}')
    
    # Collect items
    items = []
    
    # Get commits
    print(f'📝 Fetching commits from {args.branch} since {since_date}...')
    commits = parse_git_log(args.branch, since_date)
    print(f'   Found {len(commits)} commits with relevant changes')
    items.extend(commits)
    
    # Get releases
    if not args.no_releases and owner and repo:
        print('🚀 Fetching releases...')
        since_dt = datetime.strptime(since_date, '%Y-%m-%d')
        releases = get_releases(owner, repo, since_dt)
        print(f'   Found {len(releases)} releases')
        items.extend(releases)
    
    if not items:
        print('⚠️  No items found for the specified period')
        # Still generate empty feed
    
    # Generate RSS
    print(f'📄 Generating RSS feed...')
    rss_content = generate_rss(
        items=items,
        repo_name=repo_name,
        repo_url=repo_url,
        prefix=prefix,
        branch=args.branch,
        owner=owner,
        repo=repo,
    )
    
    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rss_content, encoding='utf-8')
    
    print(f'✅ RSS feed written to: {output_path}')
    print(f'   Total items: {len(items)} ({len(commits)} commits, {len(items) - len(commits)} releases)')


if __name__ == '__main__':
    main()
