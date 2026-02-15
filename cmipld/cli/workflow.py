#!/usr/bin/env python3
"""
CLI tool to run GitHub Actions workflows.

Usage:
    cmipworkflow --branch src-data                    # List available workflows
    cmipworkflow --branch src-data src-data-change    # Run specific workflow
    cmipworkflow --branch src-data --repo WCRP-CMIP/Other-Repo src-data-change
"""

import argparse
import subprocess
import sys
import json


def get_current_repo():
    """Get the current repository from git remote."""
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def list_workflows(repo):
    """List available workflows for a repository."""
    try:
        result = subprocess.run(
            ["gh", "workflow", "list", "--repo", repo, "--json", "name,state"],
            capture_output=True, text=True, check=True
        )
        workflows = json.loads(result.stdout)
        return workflows
    except subprocess.CalledProcessError as e:
        print(f"Error listing workflows: {e.stderr}", file=sys.stderr)
        return []


def run_workflow(repo, workflow, branch):
    """Run a workflow on a specific branch."""
    cmd = ["gh", "workflow", "run", workflow, "--repo", repo, "--ref", branch]
    try:
        subprocess.run(cmd, check=True)
        print(f"Workflow '{workflow}' started on branch '{branch}'")
        print(f"\nView at: https://github.com/{repo}/actions")
        
        # Offer to watch
        print("\nTo watch the run:")
        print(f"  gh run watch --repo {repo}")
    except subprocess.CalledProcessError as e:
        print(f"Error running workflow: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Run GitHub Actions workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cmipworkflow --branch src-data                     # List workflows
  cmipworkflow --branch src-data src-data-change     # Run workflow
  cmipworkflow -b main ci                            # Run CI on main
        """
    )
    parser.add_argument(
        "workflow",
        nargs="?",
        help="Workflow name to run (omit to list available)"
    )
    parser.add_argument(
        "-b", "--branch",
        required=True,
        help="Branch to run the workflow on"
    )
    parser.add_argument(
        "-r", "--repo",
        help="Repository (default: current repo)"
    )
    parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Watch the workflow run after starting"
    )
    
    args = parser.parse_args()
    
    # Get repo
    repo = args.repo or get_current_repo()
    if not repo:
        print("Error: Could not determine repository. Use --repo to specify.", file=sys.stderr)
        sys.exit(1)
    
    # List or run
    if not args.workflow:
        workflows = list_workflows(repo)
        if not workflows:
            print("No workflows found.")
            sys.exit(0)
        
        print(f"Available workflows for {repo}:\n")
        print(f"  {'Workflow':<30} {'State':<10}")
        print(f"  {'-'*30} {'-'*10}")
        for wf in workflows:
            print(f"  {wf['name']:<30} {wf['state']:<10}")
        
        print(f"\nRun with: cmipworkflow --branch {args.branch} <workflow-name>")
    else:
        run_workflow(repo, args.workflow, args.branch)
        
        if args.watch:
            subprocess.run(["gh", "run", "watch", "--repo", repo])


if __name__ == "__main__":
    main()
