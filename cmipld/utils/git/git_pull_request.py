import os
import subprocess
import sys
from . import reset_branch, branchinfo, update_summary, update_issue,branch_pull_requests
from ..io import shell 

def prepare_pull(feature_branch):
    """Prepare a pull request branch"""
    issue_number = os.environ.get('ISSUE_NUMBER')
    if issue_number:
        feature_branch = f"{feature_branch}-{issue_number}"
        reset_branch(feature_branch)
        return feature_branch
    return False

def newpull(feature_branch, author, content, title, issue, base_branch='main', update=None, labels = []):
    """Create or update a pull request"""

    prs = branch_pull_requests(head=feature_branch,)

    if prs:
        update = prs[0]['number']
        update_summary(f"++ Found existing PR: {update}. Will be updating this. ")

    # Get current branch name
    current_branch = shell("git rev-parse --abbrev-ref HEAD").strip()

    # Set upstream branch for feature branch
    shell(f"git branch --set-upstream-to=origin/{base_branch} {current_branch}")

    # Check for commits between the base branch and the current branch
    commits = shell(f"git log origin/{base_branch}..HEAD --oneline").strip()
    if not commits:
        raise ValueError(f"No commits between {base_branch} and {current_branch}. Cannot create pull request.")

    if update is not None:
        # PR already exists — nothing to do here, caller handles body via update_pr_body
        print(f"++ PR #{update} already exists, skipping re-create")
        output = str(update)
    else:
        # Create new PR with a minimal placeholder body (caller will update it)
        print(f"++ Creating a new PR")
        placeholder = f"Resolves #{issue}"
        placeholder = placeholder.replace("'", r"'\''")
        cmds = f"""
        nohup git pull -v > /dev/null 2>&1 ;
        gh pr create --base '{base_branch}' --head '{current_branch}' --title '{title}' --body '{placeholder}' {' '.join(f'--label "{label}"' for label in labels)} 2>&1;
        """
        output = shell(cmds).strip()

    update_issue(f"Updating Pull Request: {output}", False)

    # Ensure pull_req label exists then add it to the issue (if new PR)
    if update is None:
        shell('gh label create "pull_req" --color "0075ca" --description "Has an open pull request" 2>/dev/null || true')
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
