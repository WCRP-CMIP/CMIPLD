import os
from ..io import shell  # assuming your shell() prints output and handles errors


def gen_author_str(author):
    
    print(f"🔸 Generating author string for {author}")
    # Normalize author
    if isinstance(author, str):
        author = {'login': author, 'name': author}
        
    author.setdefault('name', author['login'])  # Use login if name is missing
    
    author['name'] = author['name'].replace('-', ' ')  # Remove quotes from name
    if author['name'] == '': author['name'] = author['login']  # Use login if name is empty
    
    return f"{author.get('name',author['login'])} <{author['login']}@users.noreply.github.com>"



def commit_one(location, author, comment, branch=None):
    """Commit changes with specific author and optional branch"""

    author_str = gen_author_str(author)


    # Normalize author for git config commands
    if isinstance(author, str):
        author_login = author
    else:
        author_login = author['login']

    cmds = [
        f'git config user.name "{author_login}";'
        f'git config user.email "{author_login}@users.noreply.github.com";',
        f'git add {location};',
        f'git commit --author="{author_str}" -m "{comment}";'
    ]

    if branch:
        cmds.append(f'git push origin {branch} --force;')
        print(f'🚀 Pushing commit to branch "{branch}" as {author_str}')
        
        cmds.append('git push origin HEAD -f;')
        # cmds.append('git push -f;')


    for cmd in cmds:
        print(f">> {cmd}")
        shell(cmd)
        # os.popen(cmd).read()

def commit(message):
    """Commit all changes with a message"""
    shell(f'git commit -a -m "{message}";')

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

    author_str = gen_author_str(author)

    # Default commit message
    if not message:
        message = f"Re-adding {path}."

    print(f"🔸 Untracking {path}...")
    output = os.popen(f'git rm --cached "{path}"').read()
    print(output)

    print(f"🔸 Committing removal of {path}...")
    output = os.popen(f'git commit -m "Stop tracking {path}"').read()
    print(output)

    print(f"🔸 Re-adding {path} as {author_str}...")
    output = os.popen(f'git add "{path}"').read()
    print(output)

    print(f"🔸 Committing {path} with new author...")
    output = os.popen(f'git commit --author="{author_str}" -m "{message}"').read()
    print(output)

    print(f"✅ {path} recommitted with author {author_str}.")