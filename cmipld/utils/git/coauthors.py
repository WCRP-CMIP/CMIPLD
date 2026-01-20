"""
Git co-author utilities for CMIP-LD

Simple functions for retrieving and managing co-authors from git history.
"""

import subprocess
from pathlib import Path
from typing import List, Set, Union


def get_file_authors(file_path: Union[str, Path]) -> List[str]:
    """
    Get all unique authors of a file from git history.
    
    Args:
        file_path: Path to the file
        
    Returns:
        List of unique author strings in "Name <email>" format
    """
    file_path = Path(file_path)
    
    try:
        # Get all unique authors for this file
        cmd = ['git', 'log', '--format=%an <%ae>', '--', str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return []
        
        # Split by newlines and remove empty strings
        authors = [a.strip() for a in result.stdout.strip().split('\n') if a.strip()]
        
        # Remove duplicates by email while preserving order
        # Also filter out None authors
        seen_emails = set()
        unique_authors = []
        
        for author in authors:
            # Skip if author contains 'None'
            if 'None' in author or '<>' in author:
                continue
                
            # Extract email from "Name <email>" format
            if '<' in author and '>' in author:
                email_start = author.find('<')
                email_end = author.find('>')
                email = author[email_start+1:email_end].strip()
                
                # Skip if email is empty, already seen, or invalid (no @ symbol)
                if not email or email in seen_emails or '@' not in email:
                    continue
                    
                seen_emails.add(email)
                unique_authors.append(author)
            else:
                # Skip malformed entries
                continue
        
        return unique_authors
        
    except Exception:
        return []


def get_coauthor_lines(file_paths: Union[Union[str, Path], List[Union[str, Path]]]) -> List[str]:
    """
    Get formatted co-author lines for one or more files.
    
    Args:
        file_paths: Single file path or list of file paths
        
    Returns:
        List of unique formatted co-author lines ready for commit messages
    """
    if isinstance(file_paths, (str, Path)):
        file_paths = [file_paths]
    
    # Use email as key to prevent duplicates with different names
    authors_by_email = {}
    
    for file_path in file_paths:
        authors = get_file_authors(file_path)
        for author in authors:
            # Extract email
            if '<' in author and '>' in author:
                email_start = author.find('<')
                email_end = author.find('>')
                email = author[email_start+1:email_end].strip()
                
                # Store author, keeping the first occurrence of each email
                # Only if email is valid (contains @)
                if email and '@' in email and email not in authors_by_email:
                    authors_by_email[email] = author
    
    # Format as co-author lines and sort by name
    coauthor_lines = [f"Co-authored-by: {author}" for author in sorted(authors_by_email.values())]
    return coauthor_lines


def commit_with_coauthors(file_paths: List[Union[str, Path]], message: str) -> bool:
    """
    Create a commit with co-authors from the given files.
    
    Args:
        file_paths: List of file paths that were modified
        message: Commit message
        
    Returns:
        True if commit was created successfully
    """
    if not file_paths:
        return False
    
    # Get co-author lines
    coauthor_lines = get_coauthor_lines(file_paths)
    
    # Build full message
    if coauthor_lines:
        full_message = message + "\n\n" + "\n".join(coauthor_lines)
    else:
        full_message = message
    
    try:
        # Stage files
        for file_path in file_paths:
            subprocess.run(['git', 'add', str(file_path)], check=True)
        
        # Create commit
        result = subprocess.run(['git', 'commit', '-m', full_message], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\n✅ Commit created with {len(coauthor_lines)} co-authors")
            return True
        else:
            print(f"\n❌ Failed to create commit: {result.stderr}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error creating commit: {e}")
        return False


def is_git_repo(path: Union[str, Path] = '.') -> bool:
    """Check if the path is inside a git repository."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            cwd=str(path)
        )
        return result.returncode == 0
    except:
        return False


def parse_issue_authors(author: str, coauthors_string: str = '') -> dict:
    """
    Parse issue author and coauthors into commit-ready format.
    
    Args:
        author: Primary author (GitHub username or login)
        coauthors_string: Raw string from issue form containing GitHub usernames
                         (comma/semicolon/space separated, may include @ prefix)
    
    Returns:
        dict with:
            - 'primary': {'login': str, 'email': str} - primary author
            - 'coauthors': list of {'login': str, 'email': str} - additional authors
            - 'coauthor_lines': list of formatted "Co-authored-by: ..." strings
            - 'all_logins': list of all GitHub usernames involved
    """
    def github_email(username: str) -> str:
        """Generate GitHub noreply email for username"""
        return f"{username}@users.noreply.github.com"
    
    def clean_username(name: str) -> str:
        """Clean a username string"""
        return name.strip().lstrip('@').strip()
    
    def parse_coauthors_string(collab_string: str) -> List[str]:
        """Parse coauthors string into list of GitHub usernames"""
        if not collab_string or collab_string.strip() in ('', '_No response_', 'None', 'none'):
            return []
        
        # Normalize separators
        normalized = collab_string.replace(';', ',').replace('\n', ',')
        
        # Split and clean
        collaborators = []
        for part in normalized.split(','):
            # Handle space-separated within comma-separated
            for name in part.split():
                cleaned = clean_username(name)
                if cleaned and cleaned.lower() not in {'e.g.', 'e.g', 'eg', 'example', '_no', 'response_', 'none'}:
                    collaborators.append(cleaned)
        
        return collaborators
    
    # Process primary author
    primary_login = clean_username(author) if author else 'unknown'
    primary = {
        'login': primary_login,
        'email': github_email(primary_login)
    }
    
    # Process coauthors
    coauthor_logins = parse_coauthors_string(coauthors_string)
    
    # Remove primary author from coauthors if present
    coauthor_logins = [c for c in coauthor_logins if c.lower() != primary_login.lower()]
    
    # Remove duplicates while preserving order
    seen = set()
    unique_coauthors = []
    for login in coauthor_logins:
        if login.lower() not in seen:
            seen.add(login.lower())
            unique_coauthors.append(login)
    
    # Build coauthors list
    coauthors = [{'login': login, 'email': github_email(login)} for login in unique_coauthors]
    
    # Build formatted co-author lines for commit message
    coauthor_lines = [f"Co-authored-by: {c['login']} <{c['email']}>" for c in coauthors]
    
    # All logins involved
    all_logins = [primary_login] + unique_coauthors
    
    return {
        'primary': primary,
        'coauthors': coauthors,
        'coauthor_lines': coauthor_lines,
        'all_logins': all_logins
    }


def build_commit_message(message: str, coauthor_lines: List[str] = None) -> str:
    """
    Build a commit message with optional co-author lines.
    
    Args:
        message: Main commit message
        coauthor_lines: List of "Co-authored-by: ..." strings
    
    Returns:
        Formatted commit message with co-authors appended
    """
    if not coauthor_lines:
        return message
    
    return message + "\n\n" + "\n".join(coauthor_lines)
