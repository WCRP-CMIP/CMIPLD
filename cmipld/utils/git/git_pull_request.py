import os
import subprocess
import sys
import json
from . import reset_branch, branchinfo, update_summary, update_issue, branch_pull_requests
from ..io import shell


def _find_pr_by_title(title: str) -> dict | None:
    """Return the first open PR whose title exactly matches *title*, or None."""
    try:
        raw = shell("gh pr list --state open --json number,title,headRefName --limit 100").strip()
        prs = json.loads(raw or "[]")
        for pr in prs:
            if pr.get("title") == title:
                return pr
    except Exception:
        pass
    return None

def prepare_pull(feature_branch):
    """Prepare a pull request branch"""
    issue_number = os.environ.get('ISSUE_NUMBER')
    if issue_number:
        feature_branch = f"{feature_branch}-{issue_number}"
        reset_branch(feature_branch)
        return feature_branch
    return False

def newpull(feature_branch, author, content, title, issue, base_branch='main', update=None):
    """Create or update a pull request"""

    # 1. Check by branch name
    prs = branch_pull_requests(head=feature_branch)
    if prs:
        update = prs[0]['number']
        update_summary(f"++ Found existing PR #{update} by branch. Will update.")

    # 2. Fallback: check by title to avoid duplicates if branch lookup missed it
    if not update:
        existing = _find_pr_by_title(title)
        if existing:
            update = existing['number']
            update_summary(f"++ Found existing PR #{update} by title. Will update.")

    # Get current branch name
    current_branch = shell("git rev-parse --abbrev-ref HEAD").strip()

    # Set upstream branch for feature branch
    shell(f"git branch --set-upstream-to=origin/{base_branch} {current_branch}")

    # Check for commits between the base branch and the current branch
    commits = shell(f"git log origin/{base_branch}..HEAD --oneline").strip()
    if not commits:
        raise ValueError(f"No commits between {base_branch} and {current_branch}. Cannot create pull request.")

    if update:
        # PR already exists — new_issue.py handles body + comment upserts separately
        print(f"++ PR #{update} already exists — skipping body write (handled by caller)", flush=True)
        output = str(update)
    else:
        # Create a minimal PR body; new_issue.py will overwrite it via update_pr_body()
        pr_body = (
            f"Resolves #{issue}\n\n"
            f"_This pull request was automatically created by a GitHub Actions workflow._"
        )
        print(f"++ Creating a new PR", flush=True)
        cmds = (
            f"nohup git pull -v > /dev/null 2>&1 ; "
            f"gh pr create --base '{base_branch}' --head '{current_branch}' "
            f"--title '{title}' --body '{pr_body}'"
        )
        output = shell(cmds).strip()

    # Update issue with PR info
    update_issue(f"Updating Pull Request: {output}", False)

    # Assign issue author to the PR and request their review
    if author:
        pr_num = update or output.strip('/').split('/')[-1]
        try:
            shell(f"gh pr edit '{pr_num}' --add-assignee '{author}'")
            print(f"  ✓ Assigned @{author} to PR #{pr_num}", flush=True)
        except Exception:
            pass
        try:
            shell(f"gh pr edit '{pr_num}' --add-reviewer '{author}'")
            print(f"  ✓ Requested review from @{author} on PR #{pr_num}", flush=True)
        except Exception:
            pass  # reviewer request can fail if author doesn't have repo access

    # Add "pull_req" label to the issue (only when creating a new PR)
    if update is None:
        shell(f'gh issue edit "{issue}" --add-label "pull_req"')



def pull_req(feature_branch, author, content, title):
    """Handle pull request creation"""

    # Check if the branch exists
    if not branchinfo(feature_branch):
        sys.exit(f"❌ Branch {feature_branch} not found")

    # Configure Git user details
    print(f"🔸 Setting git author to: {author}")
    shell(f'git config --global user.email "{author}@users.noreply.github.com";')
    shell(f'git config --global user.name "{author}";')

    # Check if the pull request already exists for the feature branch
    curl_command = f"gh pr list --head {feature_branch} --state all --json url --jq '.[].url';"
    pr_url = shell(curl_command).strip()
    update = None

    # If the PR exists, extract the PR number
    if pr_url:
        try:
            update = int(pr_url.strip('/').split('/')[-1])
        except ValueError:
            pass

    issue_number = os.environ.get("ISSUE_NUMBER")
    if not issue_number:
        sys.exit("❌ ISSUE_NUMBER environment variable not set")

    # Proceed to create or update the pull request
    newpull(feature_branch, author, content, title, issue_number, update=update)
