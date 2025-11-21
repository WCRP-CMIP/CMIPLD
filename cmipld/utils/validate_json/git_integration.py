#!/usr/bin/env python3
"""
Git Integration for JSON-LD Validation

This module handles git operations including co-author management,
automatic commits, and repository validation checks.
"""

import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

# from ..logging.unique import UniqueLogger, logging

# log = UniqueLogger()
from logging import getLogger
log = getLogger(__name__)

class GitCoauthorManager:
    """
    Manages git operations for the JSON-LD validation process.
    
    Handles co-author attribution, automatic commits, and git repository validation.
    """
    
    def __init__(self, directory: Path, add_coauthors: bool = False,
                 use_last_author: bool = False, auto_commit: bool = False):
        """
        Initialize git co-author manager.
        
        Args:
            directory: Repository directory
            add_coauthors: Include historic authors as co-authors
            use_last_author: Use the author of the last commit
            auto_commit: Automatically create commits after modifications
        """
        self.directory = directory
        self.add_coauthors = add_coauthors
        self.use_last_author = use_last_author
        self.auto_commit = auto_commit
        
        # Lazy load git coauthors utility
        self._git_coauthors = None
        
        # Validate git repository
        if not self.is_git_repo():
            log.warn("Not in a git repository. Git features will be disabled.")
            self.add_coauthors = False
            self.use_last_author = False
            self.auto_commit = False

    def _get_git_coauthors(self):
        """Lazy load git coauthors utility to avoid circular imports."""
        if self._git_coauthors is None:
            try:
                from ..git import coauthors as git_coauthors
                self._git_coauthors = git_coauthors
            except ImportError:
                log.warn("Git coauthors module not available")
                self._git_coauthors = None
        return self._git_coauthors

    def is_git_repo(self) -> bool:
        """Check if the directory is a git repository."""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.directory,
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_file_coauthors(self, file_path: Path) -> List[str]:
        """
        Get co-author lines for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of co-author lines for git commit
        """
        if not self.add_coauthors:
            return []
        
        git_coauthors = self._get_git_coauthors()
        if not git_coauthors:
            return []
        
        try:
            return git_coauthors.get_coauthor_lines(file_path)
        except Exception as e:
            log.warn(f"Failed to get co-authors for {file_path}: {e}")
            return []

    def get_last_commit_author(self, file_path: Optional[Path] = None) -> Optional[Dict[str, str]]:
        """
        Get the author of the last commit (optionally for a specific file).
        
        Args:
            file_path: Optional specific file to check
            
        Returns:
            Dictionary with 'name' and 'email' keys, or None
        """
        if not self.use_last_author:
            return None
        
        try:
            cmd = ['git', 'log', '-1', '--format=%an|%ae']
            if file_path:
                cmd.extend(['--', str(file_path)])
            
            result = subprocess.run(
                cmd,
                cwd=self.directory,
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                name, email = result.stdout.strip().split('|', 1)
                return {'name': name, 'email': email}
        
        except (subprocess.CalledProcessError, ValueError) as e:
            log.warn(f"Failed to get last commit author: {e}")
        
        return None

    def create_commit_message(self, file_path: Path, coauthor_lines: List[str]) -> str:
        """
        Create a commit message for a modified file.
        
        Args:
            file_path: Path to the modified file
            coauthor_lines: Co-author lines to include
            
        Returns:
            Complete commit message
        """
        relative_path = file_path.relative_to(self.directory)
        
        commit_message = f"fix: validate and update {relative_path}\n\n" \
                        f"- Added missing required keys\n" \
                        f"- Fixed ID consistency\n" \
                        f"- Corrected type prefixes\n" \
                        f"- Reordered keys for consistency"
        
        if coauthor_lines:
            commit_message += "\n\n" + "\n".join(coauthor_lines)
        
        return commit_message

    def stage_file(self, file_path: Path) -> bool:
        """
        Stage a file for commit.
        
        Args:
            file_path: Path to the file to stage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            subprocess.run(
                ['git', 'add', str(file_path)],
                # cwd=self.directory,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to stage {file_path}: {e}")
            return False

    def create_commit(self, message: str, author: Optional[Dict[str, str]] = None) -> bool:
        """
        Create a git commit.
        
        Args:
            message: Commit message
            author: Optional author information with 'name' and 'email'
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cmd = ['git', 'commit', '-m', message]
            
            if author:
                author_string = f"{author['name']} <{author['email']}>"
                cmd.extend(['--author', author_string])
            
            result = subprocess.run(
                cmd,
                cwd=self.directory,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                return True
            else:
                log.warn(f"Git commit failed: {result.stderr}")
                return False
        
        except subprocess.CalledProcessError as e:
            log.error(f"Failed to create commit: {e}")
            return False

    def handle_commits(self, modified_files: List[Path]) -> Dict[str, Any]:
        """
        Handle creating commits for all modified files.
        
        Args:
            modified_files: List of modified file paths
            
        Returns:
            Dictionary with commit statistics
        """
        
        
        if not self.auto_commit or not modified_files:
            return {
                'commits_created': 0,
                'commits_failed': 0,
                'total_files': len(modified_files),
                'skipped': True
            }
        
        log.info(f"\n📦 Creating individual commits for {len(modified_files)} modified files...")
        
        successful_commits = 0
        failed_commits = 0
        
        for file_path in modified_files:
            try:
                # Get co-authors for this specific file
                coauthor_lines = self.get_file_coauthors(file_path)
                
                # Get last author if requested
                author = None
                if self.use_last_author:
                    author = self.get_last_commit_author(file_path)
                
                # Create commit message
                commit_message = self.create_commit_message(file_path, coauthor_lines)
                
                # Stage the file
                if not self.stage_file(file_path):
                    failed_commits += 1
                    continue
                
                # Create the commit
                if self.create_commit(commit_message, author):
                    successful_commits += 1
                    
                    relative_path = file_path.relative_to(self.directory)
                    if coauthor_lines:
                        log.info(f"✅ Committed {relative_path} with {len(coauthor_lines)} co-authors")
                    else:
                        log.info(f"✅ Committed {relative_path}")
                else:
                    failed_commits += 1
            
            except Exception as e:
                log.error(f"Error processing commit for {file_path}: {e}")
                failed_commits += 1
        
        # Log summary
        self._log_commit_summary(successful_commits, failed_commits, len(modified_files))
        
        return {
            'commits_created': successful_commits,
            'commits_failed': failed_commits,
            'total_files': len(modified_files),
            'skipped': False
        }

    def _log_commit_summary(self, successful: int, failed: int, total: int) -> None:
        """Log commit operation summary."""
        log.info(f"\n📊 Commit Summary:")
        log.info(f"   ✅ Successful commits: {successful}")
        if failed > 0:
            log.warn(f"   ❌ Failed commits: {failed}")
        log.info(f"   Total files: {total}")

    def get_repository_info(self) -> Dict[str, Any]:
        """
        Get information about the git repository.
        
        Returns:
            Dictionary with repository information including owner, repo, and prefix
        """
        if not self.is_git_repo():
            return {"status": "Not a git repository", "owner": None, "repo": None, "prefix": None}
        
        try:
            # Get current branch
            branch_result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=self.directory,
                capture_output=True,
                text=True,
                check=True
            )
            current_branch = branch_result.stdout.strip()
            
            # Get repository status
            status_result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.directory,
                capture_output=True,
                text=True,
                check=True
            )
            has_changes = bool(status_result.stdout.strip())
            
            # Get remote origin URL to extract owner and repo
            remote_result = subprocess.run(
                ['git', 'config', '--get', 'remote.origin.url'],
                cwd=self.directory,
                capture_output=True,
                text=True,
                check=False
            )
            
            owner = None
            repo = None
            prefix = None
            
            if remote_result.returncode == 0 and remote_result.stdout.strip():
                remote_url = remote_result.stdout.strip()
                # Parse GitHub URL (handles both SSH and HTTPS)
                # Examples:
                #   git@github.com:WCRP-CMIP/CMIP-LD.git
                #   https://github.com/WCRP-CMIP/CMIP-LD.git
                if 'github.com' in remote_url:
                    # Remove .git suffix
                    remote_url = remote_url.rstrip('.git')
                    
                    # Extract owner/repo from different URL formats
                    if remote_url.startswith('git@'):
                        # SSH format: git@github.com:owner/repo
                        parts = remote_url.split(':')[-1].split('/')
                    elif 'github.com/' in remote_url:
                        # HTTPS format: https://github.com/owner/repo
                        parts = remote_url.split('github.com/')[-1].split('/')
                    else:
                        parts = []
                    
                    if len(parts) >= 2:
                        owner = parts[0]
                        repo = parts[1]
                        prefix = f"{owner}/{repo}"
            
            # Get last commit
            commit_result = subprocess.run(
                ['git', 'log', '-1', '--format=%H|%s|%an|%ad'],
                cwd=self.directory,
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
                "last_commit": commit_info,
                "owner": owner,
                "repo": repo,
                "prefix": prefix,
                "coauthors_enabled": self.add_coauthors,
                "auto_commit_enabled": self.auto_commit,
                "use_last_author": self.use_last_author
            }
        
        except subprocess.CalledProcessError as e:
            log.warn(f"Failed to get repository info: {e}")
            return {
                "status": "Git repository (info unavailable)",
                "owner": None,
                "repo": None,
                "prefix": None,
                "error": str(e)
            }
            
            
    def get_last_commit_message(filepath):
        """Get the commit message from the last commit that modified this file."""
        result = subprocess.run(
            ['git', 'log', '-n', '1', '--pretty=format:%B', '--', filepath],
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def check_git_configuration(self) -> Dict[str, Any]:
        """
        Check git configuration for commit requirements.
        
        Returns:
            Dictionary with configuration status
        """
        config_status = {
            "user_name": None,
            "user_email": None,
            "ready_for_commits": False
        }
        
        try:
            # Check user.name
            name_result = subprocess.run(
                ['git', 'config', 'user.name'],
                cwd=self.directory,
                capture_output=True,
                text=True,
                check=False
            )
            if name_result.returncode == 0:
                config_status["user_name"] = name_result.stdout.strip()
            
            # Check user.email
            email_result = subprocess.run(
                ['git', 'config', 'user.email'],
                cwd=self.directory,
                capture_output=True,
                text=True,
                check=False
            )
            if email_result.returncode == 0:
                config_status["user_email"] = email_result.stdout.strip()
            
            config_status["ready_for_commits"] = bool(
                config_status["user_name"] and config_status["user_email"]
            )
        
        except subprocess.CalledProcessError as e:
            log.warn(f"Failed to check git configuration: {e}")
            config_status["error"] = str(e)
        
        return config_status
