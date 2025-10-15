#!/usr/bin/env python3
"""
Git utilities for JSON validation workflow.

Provides functions specific to the validation process including
commit message retrieval, author management, and validation commits.
"""

import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Union


def get_last_commit_message(filepath: Union[str, Path]) -> str:
    """
    Get the commit message from the last commit that modified a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        Commit message string (empty string if error)
    """
    try:
        result = subprocess.run(
            ['git', 'log', '-n', '1', '--pretty=format:%B', '--', str(filepath)],
            capture_output=True,
            text=True,
            check=False
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def get_last_commit_author(filepath: Optional[Union[str, Path]] = None, 
                           directory: Optional[Path] = None) -> Optional[Dict[str, str]]:
    """
    Get the author of the last commit (optionally for a specific file).
    
    Args:
        filepath: Optional specific file to check
        directory: Optional directory to run command in
        
    Returns:
        Dictionary with 'name' and 'email' keys, or None if error
    """
    try:
        cmd = ['git', 'log', '-1', '--format=%an|%ae']
        if filepath:
            cmd.extend(['--', str(filepath)])
        
        kwargs = {'capture_output': True, 'text': True, 'check': True}
        if directory:
            kwargs['cwd'] = directory
        
        result = subprocess.run(cmd, **kwargs)
        
        if result.stdout.strip():
            name, email = result.stdout.strip().split('|', 1)
            return {'name': name, 'email': email}
    
    except (subprocess.CalledProcessError, ValueError):
        pass
    
    return None


def create_validation_commit(filepath: Union[str, Path], 
                            coauthor_lines: List[str],
                            author: Optional[Dict[str, str]] = None,
                            directory: Optional[Path] = None) -> bool:
    """
    Create a commit for a validated file with co-authors.
    
    Args:
        filepath: Path to the file to commit
        coauthor_lines: List of co-author lines
        author: Optional author dict with 'name' and 'email'
        directory: Optional directory to run commands in
        
    Returns:
        True if successful, False otherwise
    """
    filepath = Path(filepath)
    relative_path = filepath.name if not directory else filepath
    
    # Create commit message
    commit_message = (
        f"fix: validate and update {relative_path}\n\n"
        f"- Added missing required keys\n"
        f"- Fixed ID consistency\n"
        f"- Corrected type prefixes\n"
        f"- Reordered keys for consistency"
    )
    
    if coauthor_lines:
        commit_message += "\n\n" + "\n".join(coauthor_lines)
    
    try:
        kwargs = {}
        if directory:
            kwargs['cwd'] = directory
        
        # Stage the file
        subprocess.run(['git', 'add', str(filepath)], check=True, **kwargs)
        
        # Build commit command
        cmd = ['git', 'commit', '-m', commit_message]
        
        if author:
            author_string = f"{author['name']} <{author['email']}>"
            cmd.extend(['--author', author_string])
        
        # Create commit
        result = subprocess.run(cmd, capture_output=True, text=True, 
                              check=False, **kwargs)
        
        return result.returncode == 0
    
    except subprocess.CalledProcessError:
        return False


def stage_file(filepath: Union[str, Path], directory: Optional[Path] = None) -> bool:
    """
    Stage a file for commit.
    
    Args:
        filepath: Path to the file
        directory: Optional directory to run command in
        
    Returns:
        True if successful, False otherwise
    """
    try:
        kwargs = {'check': True}
        if directory:
            kwargs['cwd'] = directory
        
        subprocess.run(['git', 'add', str(filepath)], **kwargs)
        return True
    except subprocess.CalledProcessError:
        return False


def create_commit(message: str, 
                 author: Optional[Dict[str, str]] = None,
                 directory: Optional[Path] = None) -> bool:
    """
    Create a git commit.
    
    Args:
        message: Commit message
        author: Optional author dict with 'name' and 'email'
        directory: Optional directory to run command in
        
    Returns:
        True if successful, False otherwise
    """
    try:
        cmd = ['git', 'commit', '-m', message]
        
        if author:
            author_string = f"{author['name']} <{author['email']}>"
            cmd.extend(['--author', author_string])
        
        kwargs = {'capture_output': True, 'text': True, 'check': False}
        if directory:
            kwargs['cwd'] = directory
        
        result = subprocess.run(cmd, **kwargs)
        return result.returncode == 0
    
    except subprocess.CalledProcessError:
        return False


def get_repository_info(directory: Path) -> Dict[str, Any]:
    """
    Get information about the git repository.
    
    Args:
        directory: Repository directory
        
    Returns:
        Dictionary with repository information
    """
    try:
        # Get current branch
        branch_result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True
        )
        current_branch = branch_result.stdout.strip()
        
        # Get repository status
        status_result = subprocess.run(
            ['git', 'status', '--porcelain'],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True
        )
        has_changes = bool(status_result.stdout.strip())
        
        # Get last commit
        commit_result = subprocess.run(
            ['git', 'log', '-1', '--format=%H|%s|%an|%ad'],
            cwd=directory,
            capture_output=True,
            text=True,
            check=True
        )
        
        commit_info = {}
        if commit_result.stdout.strip():
            parts = commit_result.stdout.strip().split('|', 3)
            if len(parts) == 4:
                commit_info = {
                    'hash': parts[0][:8],
                    'message': parts[1],
                    'author': parts[2],
                    'date': parts[3]
                }
        
        return {
            "status": "Git repository",
            "current_branch": current_branch,
            "has_uncommitted_changes": has_changes,
            "last_commit": commit_info
        }
    
    except subprocess.CalledProcessError as e:
        return {
            "status": "Git repository (info unavailable)",
            "error": str(e)
        }


def check_git_configuration(directory: Optional[Path] = None) -> Dict[str, Any]:
    """
    Check git configuration for commit requirements.
    
    Args:
        directory: Optional directory to check
        
    Returns:
        Dictionary with configuration status
    """
    config_status = {
        "user_name": None,
        "user_email": None,
        "ready_for_commits": False
    }
    
    try:
        kwargs = {'capture_output': True, 'text': True, 'check': False}
        if directory:
            kwargs['cwd'] = directory
        
        # Check user.name
        name_result = subprocess.run(['git', 'config', 'user.name'], **kwargs)
        if name_result.returncode == 0:
            config_status["user_name"] = name_result.stdout.strip()
        
        # Check user.email
        email_result = subprocess.run(['git', 'config', 'user.email'], **kwargs)
        if email_result.returncode == 0:
            config_status["user_email"] = email_result.stdout.strip()
        
        config_status["ready_for_commits"] = bool(
            config_status["user_name"] and config_status["user_email"]
        )
    
    except subprocess.CalledProcessError as e:
        config_status["error"] = str(e)
    
    return config_status
