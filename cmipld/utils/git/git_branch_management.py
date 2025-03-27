import os
import subprocess

def getbranch():
    """Get the current git branch name"""
    return subprocess.getoutput('git rev-parse --abbrev-ref HEAD').strip()

def newbranch(branch):
    """Create or switch to a new branch"""
    branch = branch.replace(' ', '-')
    print(os.popen(f"git pull").read())
    print(os.popen(f"git checkout -b {branch} || git checkout {branch}").read())
    print(os.popen(f"git pull").read())
    print(os.popen(f'git branch --set-upstream-to=origin/{branch}').read())

def branchinfo(feature_branch):
    """Check if a branch exists and get its info"""
    binfo = subprocess.getoutput(
        f"git rev-parse --verify {feature_branch}").strip()
    if 'fatal' in binfo:
        return False
    return binfo

def reset_branch(feature_branch):
    """Reset a branch to main"""
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
