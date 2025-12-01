ssh-keygen -t ed25519 -C "github_key" -f ~/.ssh/github_key -N ""

eval "$(ssh-agent -s)"
ssh-add ~/.ssh/github_key



#!/bin/bash



git config user.email "daniel.ellis@ext.esa.int"
git config user.name "Daniel Ellis"


# Simple one-liner to convert current repo from HTTPS to SSH
git remote set-url origin "$(git remote get-url origin | sed 's|https://github.com/|git@github.com:|' | sed 's|\.git$||').git"

echo "✓ Remote URL updated to SSH"
git remote -v