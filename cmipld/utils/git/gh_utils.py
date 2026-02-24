"""
Utility functions for GitHub CLI operations
"""

import subprocess
import json
import re

class GitHubUtils:
    """Utility class for GitHub CLI operations"""
    
    # ANSI escape sequence regex for cleaning output
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    
    @classmethod
    def run_gh_cmd(cls, args, input_data=None):
        """Run GitHub CLI command with detailed logging"""
        cmd = ["gh"] + args
        print(f"🔄 Running: {' '.join(cmd)}")
        
        if input_data:
            result = subprocess.run(cmd, input=input_data, capture_output=True, text=True, check=False)
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        print(f"Return code: {result.returncode}")
        if result.stdout:
            clean_stdout = cls.ansi_escape.sub('', result.stdout.strip())
            print(f"Stdout: {clean_stdout[:200]}..." if len(clean_stdout) > 200 else f"Stdout: {clean_stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        
        if result.returncode != 0:
            raise RuntimeError(f"Command failed: {' '.join(args)}\nError: {result.stderr}")
        
        return cls.ansi_escape.sub('', result.stdout.strip())

    @classmethod
    def run_gh_cmd_safe(cls, args):
        """Run GitHub CLI command that might fail without throwing exception"""
        cmd = ["gh"] + args
        print(f"🔄 Running (safe): {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        
        print(f"Return code: {result.returncode}")
        if result.stdout:
            clean_stdout = cls.ansi_escape.sub('', result.stdout.strip())
            print(f"Stdout: {clean_stdout[:200]}..." if len(clean_stdout) > 200 else f"Stdout: {clean_stdout}")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        
        return result.returncode, cls.ansi_escape.sub('', result.stdout.strip()), result.stderr

    @classmethod
    def clear_workflow_runs(cls, limit=5000):
        """Delete all workflow runs from the current repository.
        
        Uses `gh run list` and `gh run delete` to clear workflow history.
        Requires the GitHub CLI to be authenticated and in a git repository.
        
        Args:
            limit: Maximum number of runs to fetch and delete (default: 5000)
        """
        print(f"🗑️  Fetching up to {limit} workflow runs...")
        try:
            output = cls.run_gh_cmd(
                ["run", "list", "--limit", str(limit), "--json", "databaseId", "-q", ".[].databaseId"]
            )
        except RuntimeError:
            print("No workflow runs found or gh CLI error.")
            return

        if not output.strip():
            print("No workflow runs to delete.")
            return

        run_ids = [rid.strip() for rid in output.strip().splitlines() if rid.strip()]
        print(f"Found {len(run_ids)} workflow runs. Deleting...")

        deleted = 0
        failed = 0
        for rid in run_ids:
            code, _, stderr = cls.run_gh_cmd_safe(["run", "delete", rid])
            if code == 0:
                deleted += 1
            else:
                failed += 1

        print(f"✅ Deleted {deleted} workflow runs.")
        if failed:
            print(f"⚠️  Failed to delete {failed} runs.")

    @classmethod
    def extract_repo_info(cls, issue_url):
        """Extract repository owner and name from issue URL"""
        parts = issue_url.split('/')
        if len(parts) >= 5:
            return parts[3], parts[4]  # owner, repo
        raise ValueError(f"Invalid issue URL format: {issue_url}")


def clear_runs_cli():
    """CLI entry point for clearing all workflow runs."""
    import argparse
    parser = argparse.ArgumentParser(description="Delete all GitHub Actions workflow runs from the current repository.")
    parser.add_argument("--limit", type=int, default=5000, help="Max runs to fetch (default: 5000)")
    args = parser.parse_args()
    GitHubUtils.clear_workflow_runs(limit=args.limit)
