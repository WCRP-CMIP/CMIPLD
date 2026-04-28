#!/usr/bin/env python3
"""
Clean up old GitHub Actions workflow runs.

Usage:
    clean_action_logs                          # delete all completed runs in current repo
    clean_action_logs --repo owner/repo        # specific repo
    clean_action_logs --workflow new-issue.yml # specific workflow only
    clean_action_logs --keep 5                 # keep the 5 most recent per workflow
    clean_action_logs --dry-run                # show what would be deleted
"""

import argparse
import json
import subprocess
import sys
from collections import defaultdict


def gh(*args):
    result = subprocess.run(["gh"] + list(args), capture_output=True, text=True)
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except Exception:
        return result.stdout.strip()


def get_repo(repo_arg):
    if repo_arg:
        return repo_arg
    result = subprocess.run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def list_runs(repo, workflow=None):
    args = [
        "run", "list", "--repo", repo,
        "--status", "completed",
        "--limit", "200",
        "--json", "databaseId,conclusion,workflowName,createdAt,displayTitle",
    ]
    if workflow:
        args += ["--workflow", workflow]
    runs = gh(*args)
    return runs if isinstance(runs, list) else []


def delete_run(repo, run_id, dry_run):
    if dry_run:
        return True
    result = subprocess.run(
        ["gh", "run", "delete", str(run_id), "--repo", repo],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Delete completed GitHub Actions workflow runs")
    parser.add_argument("-r", "--repo",     help="owner/repo (default: current repo)")
    parser.add_argument("-w", "--workflow", help="Filter to a specific workflow file or name")
    parser.add_argument("-k", "--keep",     type=int, default=0,
                        help="Keep N most recent runs per workflow (default: 0 = delete all)")
    parser.add_argument("--dry-run",        action="store_true",
                        help="Show what would be deleted without deleting")
    args = parser.parse_args()

    repo = get_repo(args.repo)
    if not repo:
        print("❌ Could not determine repo. Use --repo owner/repo.", file=sys.stderr)
        sys.exit(1)

    print(f"📋 Fetching completed runs for {repo}…")
    runs = list_runs(repo, args.workflow)

    if not runs:
        print("No completed runs found.")
        return

    # Group by workflow, newest first
    by_workflow = defaultdict(list)
    for r in sorted(runs, key=lambda x: x["createdAt"], reverse=True):
        by_workflow[r["workflowName"]].append(r)

    to_delete = []
    for wf_runs in by_workflow.values():
        to_delete.extend(wf_runs[args.keep:])

    if not to_delete:
        print(f"✅ Nothing to delete (keeping {args.keep} per workflow).")
        return

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"\n{prefix}Deleting {len(to_delete)} run(s):\n")

    deleted = failed = 0
    for r in to_delete:
        ok = delete_run(repo, r["databaseId"], args.dry_run)
        mark = "✓" if ok else "✗"
        print(f"  {mark}  {r['workflowName']:<35}  {r.get('conclusion','?'):<12}  {r['createdAt'][:10]}  {r['displayTitle'][:50]}")
        if ok:
            deleted += 1
        else:
            failed += 1

    print(f"\n{'Would delete' if args.dry_run else 'Deleted'} {deleted} run(s).", end="")
    if failed:
        print(f"  {failed} failed.", end="")
    print()


if __name__ == "__main__":
    main()
