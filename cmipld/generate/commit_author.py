k#!/usr/bin/env python3
"""
Simple script to commit files as different authors.

Usage:
    python commit_as_author.py <file_path> <author_name> <author_email> [repo_dir]
    
Example:
    python commit_as_author.py data/experiment/historical.json "John Doe" "john@example.com"
    python commit_as_author.py data/experiment/historical.json "John Doe" "johndoe" /path/to/repo
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, '/Users/daniel.ellis/WIPwork/CMIP-LD')
from cmipld.utils.validate_json.git_integration import GitCoauthorManager


def commit_file_as_author(file_path, author_name, author_email, repo_dir='.'):
    """
    Commit a file as a specific author.
    
    Args:
        file_path: Path to file (relative to repo_dir)
        author_name: Author name
        author_email: Author email or GitHub username (if no @, converts to noreply format)
        repo_dir: Repository directory (default: current directory)
    
    Returns:
        bool: True if successful
    """
    # Convert GitHub username to noreply email if no @ present
    if '@' not in author_email:
        username = author_email.replace(' ','_')
        author_email = f"{username}@users.noreply.github.com"
        print(f"ℹ️  Using GitHub noreply email: {author_email}")
    
    file_path = Path(repo_dir) / file_path
    repo_dir = Path(repo_dir)
    
    # Initialize git manager
    git_manager = GitCoauthorManager(
        directory=repo_dir,
        add_coauthors=False,
        use_last_author=False,
        auto_commit=False
    )
    
    # Create author and message
    author = {'name': author_name, 'email': author_email}
    relative_path = file_path.relative_to(repo_dir)
    message = f"fix: validate and update {relative_path}"
    
    # Stage and commit
    if git_manager.stage_file(file_path):
        if git_manager.create_commit(message, author=author):
            print(f"✅ Committed {file_path.name} as {author_name} <{author_email}>")
            return True
    
    print(f"❌ Failed to commit {file_path.name}")
    return False


def main():
    parser = argparse.ArgumentParser(
        description='Commit a file as a different author',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Commit with email address
  python commit_as_author.py data/experiment/historical.json "John Doe" "john@example.com"
  
  # Commit with GitHub username (converts to noreply email)
  python commit_as_author.py data/experiment/historical.json "John Doe" "johndoe"
  # Creates: johndoe@users.noreply.github.com
  
  # Commit with specific repo directory
  python commit_as_author.py data/test.json "Jane Smith" "janesmith" /path/to/repo
        """
    )
    
    parser.add_argument('file_path', help='Path to file (relative to repo)')
    parser.add_argument('author_name', help='Author name')
    parser.add_argument('author_email', help='Author email or GitHub username')
    parser.add_argument('repo_dir', nargs='?', default='.', 
                        help='Repository directory (default: current directory)')
    
    args = parser.parse_args()
    
    # Call the function with parsed arguments
    success = commit_file_as_author(
        args.file_path,
        args.author_name,
        args.author_email,
        args.repo_dir
    )
    
    sys.exit(0 if success else 1)


