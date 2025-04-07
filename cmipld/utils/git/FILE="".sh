FILE=""
COAUTHOR_EMAIL="$2"



#!/bin/bash

COAUTHOR_NAME="CMIP-IPO"
FILE="LICENSE-CC-BY"
COAUTHOR_EMAIL="$COAUTHOR_NAME@users.noreply.github.com"

# Get the last commit hash that modified the file
LAST_COMMIT=$(git log -n 1 --pretty=format:%H -- "$FILE")

if [ -z "$LAST_COMMIT" ]; then
    echo "No commits found for file: $FILE"
    exit 1
fi

echo "Appending co-author: $COAUTHOR_NAME <$COAUTHOR_EMAIL> to commit $LAST_COMMIT"

# Define the commit hash and the new body to append
COMMIT_HASH=$LAST_COMMIT
NEW_BODY="  Co-authored-by: $COAUTHOR_NAME <$COAUTHOR_EMAIL>"

# Check out the specific commit
# Use 'git switch' if you're using a newer Git version
git switch --detach $COMMIT_HASH  # Detach HEAD at the specific commit

# Get the current commit message
COMMIT_MSG=$(git log --format=%B -n 1 $COMMIT_HASH)

# Create the updated commit message by appending the co-author
# Ensure the co-author line is on a new line
UPDATED_COMMIT_MSG="$COMMIT_MSG"$'\n'"$NEW_BODY"  # Append co-author line

# Amend the commit with the new message
echo "$UPDATED_COMMIT_MSG" | git commit --amend --no-edit --file=-

# Optional: If this commit was pushed to a remote, force-push the changes
git push origin main --force

# Optionally, return to your original branch
git switch -













#!/bin/bash

COAUTHOR_NAME="CMIP-IPO"
FILE="LICENSE-CC-BY"
COAUTHOR_EMAIL="$COAUTHOR_NAME@users.noreply.github.com"

# Get the last commit hash that modified the file
LAST_COMMIT=$(git log -n 1 --pretty=format:%H -- "$FILE")

if [ -z "$LAST_COMMIT" ]; then
    echo "No commits found for file: $FILE"
    exit 1
fi

echo "Appending co-author: $COAUTHOR_NAME <$COAUTHOR_EMAIL> to commit $LAST_COMMIT"

# Define the commit hash and the new body to append
COMMIT_HASH=$LAST_COMMIT
NEW_BODY="  Co-authored-by: $COAUTHOR_NAME <$COAUTHOR_EMAIL>"



# Ensure the commit date stays the same
COMMIT_DATE=$(git show -s --format=%ci $COMMIT_HASH)

# Get the current commit message
COMMIT_MSG=$(git log --format=%B -n 1 $COMMIT_HASH)

# Create the updated commit message by appending the co-author
# Ensure the co-author line is on a new line
NEW_MESSAGE="$COMMIT_MSG; $NEW_BODY"  # Append co-author line


# Rebase non-interactively and amend the commit message
GIT_COMMITTER_DATE="$COMMIT_DATE" git rebase --onto $(git rev-parse ${COMMIT_HASH}^1) $COMMIT_HASH^ --exec \
"git commit --amend --no-edit --message '$NEW_MESSAGE'"

# Optionally, force-push to the remote if the commit is already published
git push --force


















# Check out the specific commit
git switch --detach $COMMIT_HASH  # Detach HEAD at the specific commit

# Get the current commit message
COMMIT_MSG=$(git log --format=%B -n 1 $COMMIT_HASH)

# Create the updated commit message by appending the co-author
UPDATED_COMMIT_MSG="$COMMIT_MSG"$'\n'"$NEW_BODY"  # Append co-author line

# Amend the commit with the new message
echo "$UPDATED_COMMIT_MSG" | git commit --amend --no-edit --file=-

# Rebase onto the original commit to keep the same commit hash
git rebase --onto $COMMIT_HASH^ $COMMIT_HASH

# # Switch back to the main branch
# git switch main

# Force-push the amended commit to the remote repository
git push origin main --force

# # Optionally, return to your original branch
# git switch -