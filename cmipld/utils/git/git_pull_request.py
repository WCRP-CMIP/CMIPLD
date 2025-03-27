import os
import subprocess
import sys

def prepare_pull(feature_branch):
    """Prepare a pull request branch"""
    issue_number = os.environ['ISSUE_NUMBER']
    if issue_number:
        feature_branch = f'{feature_branch}-{issue_number}'
        reset_branch(feature_branch)
        return feature_branch
    return False

def newpull(feature_branch, author, content, title, issue, base_branch='main', update=None):
    """Create or update a pull request"""
    feature_branch = subprocess.getoutput("git rev-parse --abbrev-ref HEAD")

    os.popen(f"git branch --set-upstream-to=origin/{base_branch} {feature_branch}")

    commits = subprocess.getoutput(f"git log origin/{base_branch}..HEAD --oneline")
    if not commits:
        raise ValueError(f"No commits between {base_branch} and {feature_branch}. Cannot create pull request.")

    if update is not None:
        where = f"gh pr comment {update}"
    else:
        where = f"gh pr create --base '{base_branch}' --head '{feature_branch}' --title '{title}'"

    content = content.replace('`', r'\`')
    cmds = f"""
    nohup git pull -v > /dev/null 2>&1 ;
    {where} --body \"$(cat <<EOF
This pull request was automatically created by a GitHub Actions workflow.

Adding the following new data.

\`\`\`js
{content}
\`\`\`

Resolves #{issue}
EOF
)\"
"""
    print('++', cmds)

    output = subprocess.getoutput(cmds).strip()

    update_issue(f'New Pull Request: {output}', False)
    print(os.popen(f'gh issue edit "{issue}" --add-label "pull_req"').read())

def pull_req(feature_branch, author, content, title):
    """Handle pull request creation"""
    feature_branch = f'{feature_branch}'

    if not branchinfo(feature_branch):
        print(f'Pull_req: Branch {feature_branch} not found')
        sys.exit(f'Pull_req: Branch {feature_branch} not found')

    cmds = [
        f'git config --global user.email "{author}@users.noreply.github.com" ',
        f'git config --global user.name "{author}" '
    ]

    for cmd in cmds:
        print(cmd, ':', subprocess.getoutput(cmd).strip())

    curl_command = f"gh pr list --head {feature_branch} --state all --json url --jq '.[].url'"

    pullrqsts = subprocess.getoutput(curl_command).strip().split('/')[-1]

    try:
        update = int(pullrqsts)
    except:
        update = None

    newpull('main', feature_branch, author, content, title, os.environ["ISSUE_NUMBER"], update)

