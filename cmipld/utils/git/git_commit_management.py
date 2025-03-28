import os
from ..io import shell  # assuming your shell() prints output and handles errors

def commit_one(location, author, comment, branch=None):
    """Commit changes with specific author and optional branch"""

    # Normalize author
    if isinstance(author, str):
        author = {'login': author, 'name': author}

    author_str = f"{author['name']} <{author['login']}@users.noreply.github.com>"

    cmds = [
        f'git add {location}',
        f'git commit -a --author="{author_str}" -m "{comment}"'
    ]

    if branch:
        cmds.append(f'git push origin {branch} --force')
        print(f'🚀 Pushing commit to branch "{branch}" as {author_str}')

    cmds.append('git push -f')

    for cmd in cmds:
        print(f">> {cmd}")
        shell(cmd)

def commit(message):
    """Commit all changes with a message"""
    shell(f'git commit -a -m "{message}"')

def addfile(file):
    """Stage a specific file"""
    shell(f'git add {file}')

def addall():
    """Stage all changes"""
    shell('git add -A')

def push(branch='HEAD'):
    """Push changes to the specified branch"""
    shell(f'git push -u origin {branch}')

def recommit_file(path, author, message=None):
    """Recommit a file with a new author and message"""

    # Normalize author
    if isinstance(author, str):
        author = {'login': author, 'name': author}

    author_str = f"{author['name']} <{author['login']}>"

    # Default message
    if not message:
        message = f"Re-adding {path}."

    print(f"🔸 Untracking {path}...")
    shell(f'git rm --cached "{path}"')
    shell(f'git commit -m "Stop tracking {path}"')

    print(f"🔸 Re-adding {path} as {author_str}...")
    shell(f'git add "{path}"')
    shell(f'git commit -m "{message}" --author="{author_str}"')

    print(f"✅ {path} recommitted with author {author_str}.")
