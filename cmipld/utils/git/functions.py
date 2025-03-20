from . import functions
from . import add
import os
import subprocess
import sys
import json
import re
from typing import List, Dict, Any, Tuple
import requests
import shlex


def update_env(key, value):
    import os
    github_env_file = os.environ.get("GITHUB_ENV")

    with open(github_env_file, "a") as env_file:
        env_file.write(f"{key}={value}\n")


def update_summary(md):
    import os
    if "GITHUB_STEP_SUMMARY" in os.environ:
        github_env_file = os.environ.get("GITHUB_STEP_SUMMARY")

        with open(github_env_file, "a") as summary:
            summary.write(f"{md}\n")
    else:
        print(md)


def update_issue_title(what):
    # change issue name to reflect contents.
    if 'ISSUE_NUMBER' in os.environ:
        assert isinstance(int(os.environ['ISSUE_NUMBER']), int)
        issue_number = os.environ['ISSUE_NUMBER']

        print(
            os.popen(f'gh issue edit {issue_number} --title "{what}"').read())
        # : {payload["client_payload"]["name"]}"
    update_summary(f"#### Title Updated:\n `{what}`")


def update_issue(comment, err=True, summarize=True):
    if 'ISSUE_NUMBER' in os.environ:
        assert isinstance(int(os.environ['ISSUE_NUMBER']), int)
        issue_number = os.environ['ISSUE_NUMBER']

        cmd = f'gh issue comment {issue_number} --body \'{comment}\' '
        # .replace('"', '\\"').replace('\n', '\\n')
        print(cmd)
        out = os.popen(cmd).read()

        if summarize:
            update_summary(comment)
        if err:
            print(out)
            raise ValueError(comment)

    print(comment)


def close_issue(comment, err=True):
    if 'ISSUE_NUMBER' in os.environ:
        issue_number = os.environ['ISSUE_NUMBER']
        print(os.popen(f'gh issue close {issue_number} -c "{comment}"'))
        if err:
            raise ValueError(comment)
            # sys.exit(comment)

    print(comment)


def jr(file):
    return json.load(open(file, 'r'))


def jw(data, file):
    return json.dump(data, open(file, 'w'), indent=4)


def getfile(fileend):
    import glob
    return glob.glob(f'*{fileend}.json')


def pp(js):
    import pprint
    pprint.pprint(js)


def extract_repo_info(github_pages_url):
    """Extract username and repository name from GitHub Pages URL."""
    pattern = r'https{0,1}://([a-zA-Z0-9-_]+)\.github\.io/([a-zA-Z0-9-_]+)/(.*)?'
    match = re.match(pattern, github_pages_url)

    if match:
        username = match.group(1)
        repo_name = match.group(2)
        path = match.group(3)
        return username, repo_name, path
    else:
        raise ValueError("Invalid GitHub Pages URL")


def io2url(github_pages_url, branch='main', path_base=''):

    username, repo_name, path = extract_repo_info(github_pages_url)
    base_url = f'https://github.com/{username}/{repo_name}/tree/{branch}/{path_base}{path}'

    return base_url


def io2repo(github_pages_url):

    username, repo_name, path = extract_repo_info(github_pages_url)
    base_url = f'https://github.com/{username}/{repo_name}.git'

    return base_url


def url2io(github_repo_url, branch='main', path_base=''):
    print('make test for url2io')

    if '/tree/' in github_repo_url:
        # Regex to extract username, repo name, and path from GitHub repo URL
        pattern = rf"https://github\.com/(?P<username>[^/]+)/(?P<repo_name>[^/]+)/tree/{branch}/{path_base}(?P<path>.*)"

    else:
        pattern = rf"https://github\.com/(?P<username>[^/]+)/(?P<repo_name>[^/]+)"

    match = re.match(pattern, github_repo_url)

    if not match:
        raise ValueError("Invalid GitHub repository URL format.")

    username = match.group("username")
    repo_name = match.group("repo_name")
    path = match.groupdict().get("path", "").strip('/')

    github_pages_url = f"https://{username.lower()}.github.io/{repo_name}/{path}/"
    if github_pages_url[-2:] == '//':
        github_pages_url = github_pages_url[:-1]
    elif github_pages_url[-1] != '/':
        github_pages_url += '/'

    return github_pages_url


def toplevel():
    return os.popen('git rev-parse --show-toplevel').read().strip()


def ldpath(path=''):
    # path = f'organisations/institutions'
    loc = os.path.abspath(f"{toplevel()}/src-data/{path}/")
    if loc[-1] != '/':
        loc += '/'
    return loc


def url():
    return subprocess.getoutput('git remote get-url origin').replace('.git', '').strip()


def commit_override_author(entry, where):
    if os.environ.get('OVERRIDE_AUTHOR'):
        cmd = f'git commit -a --author="{os.environ["OVERRIDE_AUTHOR"].strip()} <{os.environ["OVERRIDE_AUTHOR"].strip()}@users.noreply.github.com>" -m "New entry {entry} to the {where} LD file"'
        print(os.popen(cmd).read())
        return True
    print('No author found')
    os.popen(f'git commit -m "A commit to {entry} at {where}"').read()
    return False


def commit_one(location, author, comment, branch=None):
    cmds = [
        f'git config --global user.email "{author}@users.noreply.github.com"',
        f'git config --global user.name "{author}"',
        f'git add {location} ',
        f'git commit -a --author="{author} <{author}@users.noreply.github.com>" -m "{comment}"'
    ]
    print('>> pushing commit to branch')

    if branch:
        cmds.append(f'git push origin {branch} --force')
    # else:

    cmds.append(f'git push -f ')

    for cmd in cmds:
        print(cmd, ':', subprocess.getoutput(cmd).strip())


def commit(message):
    print(os.popen(f'git commit -a -m "{message}"').read())


def addfile(file):
    print(os.popen(f'git add {file}').read())


def getbranch():
    return subprocess.getoutput('git rev-parse --abbrev-ref HEAD').strip()


def getreponame():
    return subprocess.getoutput('git remote get-url origin').split('/')[-1].replace('.git', '').strip()


def getrepoowner():
    return subprocess.getoutput('git remote get-url origin').split('/')[-2].strip()


def getlastcommit():
    return subprocess.getoutput('git rev-parse HEAD').strip()


def getlasttag():
    return subprocess.getoutput('git describe --tags --abbrev=0').strip()


def getfilenames(branch='main'):
    return os.popen(f'git ls-tree -r {branch} --name-only ').read().split()


def addall():
    print(os.popen('git add -A').read())


def newbranch(branch):
    branch = branch.replace(' ', '-')
    # pull the main
    print(os.popen(f"git pull").read())
    # create the new branch
    print(
        os.popen(f"git checkout -b {branch} || git checkout {branch}").read())
    # pull the branch if it exists
    print(os.popen(f"git pull").read())
    # set upstream
    print(os.popen(f'git branch --set-upstream-to=origin/{branch}').read())


def get_cmip_repo_info() -> Tuple[str, str, str]:
    """Retrieve repository information and tags."""
    repo = subprocess.getoutput(
        'git remote get-url origin').replace('.git', '/blob/main/JSONLD').strip()
    cv_tag = subprocess.getoutput(
        "curl -s https://api.github.com/repos/WCRP-CMIP/CMIP6Plus_CVs/tags | jq -r '.[0].name'").strip()
    mip_tag = subprocess.getoutput(
        "curl -s https://api.github.com/repos/PCMDI/mip-cmor-tables/tags | jq -r '.[0].name'").strip()
    return repo, cv_tag, mip_tag


def branchinfo(feature_branch):
    binfo = subprocess.getoutput(
        f"git rev-parse --verify {feature_branch}").strip()
    if 'fatal' in binfo:
        return False
    return binfo


def reset_branch(feature_branch):
    # if a branch exists, reset it to main, then progress.

    binfo = branchinfo(feature_branch)
    print('BINFO:', binfo)

    cmds = [
        'git remote -v',
        'git fetch --all',
        f"git pull",
        f"git checkout {feature_branch}",
        f"git reset --hard origin/main",
        f"git push origin {feature_branch} -f",


    ]
    if not binfo:
        cmds[3] = f"git checkout -b {feature_branch}"
        cmds[5] = f"git push --set-upstream origin {feature_branch} --force"

    for cmd in cmds:
        print(os.popen(cmd).read())


def prepare_pull(feature_branch):
    issue_number = os.environ['ISSUE_NUMBER']
    if issue_number:
        feature_branch = f'{feature_branch}-{issue_number}'
        reset_branch(feature_branch)
        return feature_branch
    return False


def newpull(feature_branch, author, content, title, issue, base_branch='main', update=None):
    # Ensure we're using the current branch
    feature_branch = subprocess.getoutput("git rev-parse --abbrev-ref HEAD")

    # Set upstream for the current branch if not already set
    os.popen(
        f"git branch --set-upstream-to=origin/{base_branch} {feature_branch}")

    # Ensure there are commits between the branches
    commits = subprocess.getoutput(
        f"git log origin/{base_branch}..HEAD --oneline")
    if not commits:
        raise ValueError(
            f"No commits between {base_branch} and {feature_branch}. Cannot create pull request.")

    # Create the PR or update existing one
    if update is not None:
        where = f"gh pr comment {update}"
    else:
        where = f"gh pr create --base '{base_branch}' --head '{feature_branch}' --title '{title}'"

    # Construct command using cat <<EOF to handle special characters safely
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
    # Data submitted by @{author}

    print('++', cmds)

    output = subprocess.getoutput(cmds).strip()

    # Add a comment to the issue if necessary
    update_issue(f'New Pull Request: {output}', False)


def pull_req(feature_branch, author, content, title):
    # gh_token, issue, base_branch
    # Set git configuration

    feature_branch = f'{feature_branch}'

    if not branchinfo(feature_branch):
        print(f'Pull_req: Branch {feature_branch} not found')
        sys.exit(f'Pull_req: Branch {feature_branch} not found')

    cmds = [
        f'git config --global user.email "{author}@users.noreply.github.com" ',
        f'git config --global user.name "{author}" '
        # f'git commit -a --author="{author} <{author}@users.noreply.github.com>" -m "{comment}"'
    ]

    for cmd in cmds:
        print(cmd, ':', subprocess.getoutput(cmd).strip())
    # remote_branch=f'origin/{feature_branch}'
    '''
    gh_token = os.getenv('GH_TOKEN')
    github_repository = os.getenv('GITHUB_REPOSITORY')
    '''
    # feature_branch = os.getenv('FEATURE_BRANCH')

    # Construct the curl command
    # curl_command = (
    #     f'curl -s -H "Authorization: token {gh_token}" '
    #     f'"https://api.github.com/repos/{github_repository}/pulls?state=open&head=origin/{feature_branch}"| jq -r ".[].number"'
    # )

    curl_command = f"gh pr list --head {feature_branch} --state all --json url --jq '.[].url'"

    # Execute the command
    pullrqsts = subprocess.getoutput(curl_command).strip().split('/')[-1]

    # write = False

    # #### sort out existing issue description updates later.

    # # for pr in pullrqsts.split(' '):
    # #     if pr == os.environ["ISSUE_NUMBER"]:
    # #         write = True
    # #         update_issue(f'Overwriting Pull Request Info: |{pr}|',False)
    # #         newpull('main', feature_branch,author,content,title,os.environ["ISSUE_NUMBER"],update = pr)

    # if not write:

    try:
        update = int(pullrqsts)
    except:
        update = None
        # create a new pull request
    newpull('main', feature_branch, author, content,
            title, os.environ["ISSUE_NUMBER"], update)


def push(branch='HEAD'):
    print(os.popen(f'git push -u origin {branch}').read())


def get_tags(owner, repo):
    # Get the tags from the repo
    return requests.get(f'https://api.github.com/repos/{owner}/{repo}/tags').json()


def get_contents(owner, repo, path):
    # Get the tags from the repo
    return requests.get(f'https://api.github.com/repos/{owner}/{repo}/contents/{path}').json()
