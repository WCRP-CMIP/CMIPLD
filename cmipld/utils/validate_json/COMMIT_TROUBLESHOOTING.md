# Troubleshooting: Why Commits Are Not Being Created

## Issues Fixed

### 1. Missing 'prefix' Key in Repository Info ✅ FIXED
**Problem:** The `get_repository_info()` method didn't extract the repository owner/repo/prefix from the git remote URL, causing a KeyError when validating type fields.

**Solution:** Added code to parse the git remote origin URL and extract:
- `owner` (e.g., "WCRP-CMIP")
- `repo` (e.g., "CMIP-LD")  
- `prefix` (e.g., "WCRP-CMIP/CMIP-LD")

Now the method correctly parses both SSH and HTTPS GitHub URLs.

### 2. Git Manager Only Created with Flags
**Problem:** The `GitCoauthorManager` is only instantiated if you pass `--add-coauthors`, `--use-last-author`, or `--auto-commit`. Without these flags, no git operations happen.

**This is by design**, but you must use the correct flags:

## How to Make Commits Work

### Required Flag
You **MUST** use `--auto-commit` (or `-m`) for the tool to create commits:

```bash
validate_json ./data --auto-commit
```

### Common Issues and Solutions

#### Issue: Running without --auto-commit
```bash
# ❌ This will NOT create commits:
validate_json ./data

# ✅ This WILL create commits:
validate_json ./data --auto-commit
```

#### Issue: Using --dry-run with --auto-commit
```bash
# ❌ This will NOT create commits (dry-run prevents all modifications):
validate_json ./data --auto-commit --dry-run

# ✅ Remove --dry-run to actually commit:
validate_json ./data --auto-commit
```

#### Issue: Git not configured
If git user.name or user.email are not set, commits will fail silently.

**Check git configuration:**
```bash
git config user.name
git config user.email
```

**Fix if missing:**
```bash
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

#### Issue: Not seeing commit messages
The default log level is WARNING, so you won't see INFO level commit messages.

**Solution: Use --verbose flag:**
```bash
validate_json ./data --auto-commit --verbose
```

This will show:
- ✅ Committed {filename} with {N} co-authors
- 📊 Commit Summary
- Number of successful/failed commits

## Recommended Usage

### For Individual Commits with Co-Authors
```bash
validate_json ./data --auto-commit --verbose
```

This will:
1. Validate and fix each JSON file
2. Create an individual commit for each modified file
3. Include all historic contributors as co-authors
4. Show detailed output of what was committed

### To See What Would Be Committed First
```bash
# Step 1: Preview changes
validate_json ./data --dry-run --verbose

# Step 2: Apply changes and commit
validate_json ./data --auto-commit --verbose
```

### Without Co-Authors (Faster)
```bash
validate_json ./data --auto-commit --verbose
```

Note: `--auto-commit` implies `--add-coauthors` by default (see CLI code).

### With Custom Author
```bash
validate_json ./data --auto-commit --use-last-author --verbose
```

Uses the author from each file's last commit instead of the current user.

## Checking If It Worked

After running with `--auto-commit`, check:

```bash
# See recent commits
git log --oneline -10

# See detailed commit with co-authors
git log -1 --format=fuller

# Check what was committed
git diff HEAD~1
```

You should see commits like:
```
fix: validate and update experiments/historical.json

- Added missing required keys
- Fixed ID consistency
- Corrected type prefixes
- Reordered keys for consistency

Co-authored-by: John Doe <john@example.com>
Co-authored-by: Jane Smith <jane@example.com>
```

## Debug Mode

To diagnose issues, run with maximum verbosity:

```bash
validate_json ./data --auto-commit --verbose
```

Look for:
- ✅ Committed {file} - indicates successful commits
- ❌ Failed commits - indicates errors
- 📦 Creating individual commits - shows the process starting
- 📊 Commit Summary - final statistics

## Still Not Working?

If commits still aren't being created after following this guide:

1. **Verify you're using --auto-commit:**
   ```bash
   validate_json ./data --auto-commit --verbose
   ```

2. **Check git configuration:**
   ```bash
   git config user.name
   git config user.email
   git config remote.origin.url
   ```

3. **Verify you're in a git repository:**
   ```bash
   git status
   ```

4. **Check for staged changes:**
   ```bash
   git diff --staged
   ```

5. **Look for error messages in output:**
   Run with `--verbose` and check for warnings or errors about git operations.

## Summary

**To create commits, you MUST use:**
```bash
validate_json <directory> --auto-commit --verbose
```

Without `--auto-commit`, the tool only validates and fixes files but doesn't create any commits.
