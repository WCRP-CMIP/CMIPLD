"""
dev - Quick git development workflow

Performs: git pull, git add -A, git commit -m 'development', git push
"""

import subprocess
import sys


def main():
    args = sys.argv[1:]

    if args and args[0] in ('-h', '--help'):
        print(__doc__.strip())
        print("\nUsage: dev [commit message]")
        print("\nWarning: Makes automatic commits. Use with caution in production repositories.")
        return

    message = ' '.join(args) if args else 'development'

    steps = [
        ("Adding all changes...",          ["git", "add", "-A"]),
        (f"Committing: '{message}'",        ["git", "commit", "-m", message]),
        ("Pulling latest changes...",      ["git", "pull", "--rebase"]),
        ("Pushing to remote...",           ["git", "push"]),
    ]

    print("Starting development workflow...", flush=True)
    for msg, cmd in steps:
        print(msg, flush=True)
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
            sys.exit(result.returncode)

    print("Development workflow complete!", flush=True)


if __name__ == "__main__":
    main()
