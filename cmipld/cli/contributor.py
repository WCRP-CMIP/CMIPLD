#!/usr/bin/env python3
"""
CLI tool to get or assign the last contributor for a file.

Usage:
    cmip-contributor <file>                    # Show last contributor
    cmip-contributor <file> --assign <handle>  # Assign (recommit) as contributor
    cmip-contributor <file> --json             # Output as JSON
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def get_last_contributor(filepath, repo_dir=None):
    """
    Get the GitHub handle of the last contributor to a file.
    
    Args:
        filepath: Path to the file
        repo_dir: Repository directory (default: current directory)
        
    Returns:
        dict: Contributor info with 'login', 'name', 'email' keys
    """
    if repo_dir:
        filepath = Path(repo_dir) / filepath
    else:
        filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Change to repo directory if specified
    cwd = repo_dir if repo_dir else None
    
    try:
        # Get last commit info: hash, author name, author email, date, subject
        result = subprocess.run(
            ['git', 'log', '-1', '--pretty=format:%H|%an|%ae|%ai|%s', str(filepath)],
            capture_output=True,
            text=True,
            check=True,
            cwd=cwd
        )
        
        output = result.stdout.strip()
        if not output:
            return None
            
        parts = output.split('|', 4)
        if len(parts) < 5:
            return None
            
        commit_hash, author_name, author_email, date, subject = parts
        
        # Extract GitHub username from email
        github_handle = None
        if '@users.noreply.github.com' in author_email:
            github_handle = author_email.split('@')[0]
            # Remove numeric prefix (like 12345+username)
            if '+' in github_handle:
                github_handle = github_handle.split('+')[1]
        else:
            # Try to get username from git config or use email prefix
            github_handle = author_email.split('@')[0]
        
        return {
            'login': github_handle,
            'name': author_name,
            'email': author_email,
            'commit': commit_hash[:8],
            'date': date,
            'message': subject,
            'file': str(filepath)
        }
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Git error: {e.stderr}")


def assign_contributor(filepath, github_handle, repo_dir=None, message=None):
    """
    Assign a contributor to a file by recommitting it with their authorship.
    
    Args:
        filepath: Path to the file
        github_handle: GitHub username
        repo_dir: Repository directory
        message: Commit message (optional)
        
    Returns:
        bool: True if successful
    """
    if repo_dir:
        filepath = Path(repo_dir) / filepath
    else:
        filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    # Generate author info
    author_email = f"{github_handle}@users.noreply.github.com"
    author_name = github_handle.replace('-', ' ').replace('_', ' ').title()
    author_str = f"{author_name} <{author_email}>"
    
    # Default message
    if not message:
        message = f"Assign {github_handle} as contributor for {filepath.name}"
    
    cwd = repo_dir if repo_dir else None
    
    try:
        # Stage the file
        subprocess.run(
            ['git', 'add', str(filepath)],
            check=True,
            cwd=cwd
        )
        
        # Check if there are changes to commit
        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet', str(filepath)],
            cwd=cwd
        )
        
        if result.returncode == 0:
            # No changes, need to do empty commit or touch file
            print(f"ℹ️  No changes to {filepath.name}, creating attribution commit...")
            
            # Create an empty commit with the attribution
            subprocess.run(
                ['git', 'commit', '--allow-empty', f'--author={author_str}', '-m', message],
                check=True,
                cwd=cwd
            )
        else:
            # Commit with author
            subprocess.run(
                ['git', 'commit', f'--author={author_str}', '-m', message],
                check=True,
                cwd=cwd
            )
        
        print(f"✅ Assigned {github_handle} as contributor for {filepath.name}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to assign contributor: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Get or assign the last contributor for a file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show the last contributor to a file
  cmip-contributor src/data/experiment.json
  
  # Output as JSON
  cmip-contributor src/data/experiment.json --json
  
  # Assign a contributor (creates attribution commit)
  cmip-contributor src/data/experiment.json --assign johndoe
  
  # Assign with custom message
  cmip-contributor src/data/experiment.json --assign johndoe -m "Attribution for data contribution"
        """
    )
    
    parser.add_argument('file', help='Path to the file')
    parser.add_argument('--assign', '-a', metavar='HANDLE',
                        help='GitHub handle to assign as contributor')
    parser.add_argument('--message', '-m', 
                        help='Custom commit message (with --assign)')
    parser.add_argument('--json', '-j', action='store_true',
                        help='Output as JSON')
    parser.add_argument('--repo', '-r', default=None,
                        help='Repository directory (default: current directory)')
    
    args = parser.parse_args()
    
    try:
        if args.assign:
            # Assign mode
            success = assign_contributor(
                args.file, 
                args.assign, 
                repo_dir=args.repo,
                message=args.message
            )
            sys.exit(0 if success else 1)
        else:
            # Get mode
            contributor = get_last_contributor(args.file, repo_dir=args.repo)
            
            if not contributor:
                print(f"No commits found for: {args.file}", file=sys.stderr)
                sys.exit(1)
            
            if args.json:
                print(json.dumps(contributor, indent=2))
            else:
                print(f"📄 File: {contributor['file']}")
                print(f"👤 Contributor: @{contributor['login']}")
                print(f"   Name: {contributor['name']}")
                print(f"   Email: {contributor['email']}")
                print(f"📝 Last commit: {contributor['commit']}")
                print(f"   Date: {contributor['date']}")
                print(f"   Message: {contributor['message']}")
            
            sys.exit(0)
            
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
