# Get the base GitHub URL of the repository
repo_url=$(git config --get remote.origin.url)

# If URL is in SSH format (git@github.com:username/repo.git), convert to HTTPS
if [[ $repo_url =~ ^git@github\.com ]]; then
  repo_url="https://github.com/$(echo $repo_url | sed 's/^git@github.com:/\//;s/\.git$//')"
else
  # Otherwise it's already in HTTPS format, so we just clean it up
  repo_url="https://github.com/$(echo $repo_url | sed 's/\.git$//')"
fi

# Get the current directory relative to the root of the repository
relative_path=$(pwd | sed "s|$(git rev-parse --show-toplevel)||" | sed 's|^/||')

# Combine base URL and the relative path to get the full URL for the folder
extended_url="$repo_url/tree/main/$relative_path"

# Print the URL
echo "GitHub URL for the current folder: $extended_url"
