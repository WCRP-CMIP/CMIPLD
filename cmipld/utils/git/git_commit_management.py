import os
import subprocess

def commit_one(location, author, comment, branch=None):
    """Commit changes with specific author and optional branch"""
    
    if 'name' not in author and 'login' not in author:
        author = {'login': author, 'name': author}
    
    cmds = [
        f'git config --global user.email "{author.login}@users.noreply.github.com"',
        f'git config --global user.name "{author.name}"',
        f'git add {location} ',
        f'git commit -a --author="{author.name} <{author.login}@users.noreply.github.com>" -m "{comment}"'
    ]

    if branch:
        cmds.append(f'git push origin {branch} --force')
        print(f'>> pushing commit to branch {branch} as author={author}')

    cmds.append(f'git push -f ')

    for cmd in cmds:
        print(cmd, ':', subprocess.getoutput(cmd).strip())

def commit(message):
    """Commit all changes with a message"""
    print(os.popen(f'git commit -a -m "{message}"').read())

def addfile(file):
    """Stage a specific file"""
    print(os.popen(f'git add {file}').read())

def addall():
    """Stage all changes"""
    print(os.popen('git add -A').read())

def push(branch='HEAD'):
    """Push changes to the specified branch"""
    print(os.popen(f'git push -u origin {branch}').read())
