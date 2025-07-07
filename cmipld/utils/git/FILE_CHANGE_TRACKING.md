# File Change Tracking Functions

This document describes the new file change tracking functions added to the CMIP-LD library's Git utilities. These functions work with both **local Git repositories** and **remote public GitHub repositories**.

## ✨ Key Features

- **Local & Remote Support**: Works with local Git repos and remote GitHub repositories
- **Flexible Filtering**: Filter by directory paths and exclude unwanted files
- **Multiple Date Formats**: Support various date formats including relative dates
- **Detailed Information**: Get commit details, authors, and messages
- **Convenience Functions**: Easy-to-use functions for common scenarios

## New Functions

### 1. `get_files_changed_since_date()`

Get all files changed since a specific date from all commits.

**Parameters:**
- `since_date` (str): Date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
- `branch` (str, optional): Branch to check (default: 'main')
- `base_path_filter` (str, optional): Base path to filter files (e.g., 'src-data/' to only include files in src-data directory)
- `exclude_paths` (list, optional): List of paths to exclude (e.g., ['.git/', '__pycache__/'])

**Returns:**
- `list`: List of unique file paths that were changed since the date

**Example:**
```python
from cmipld.utils.git import get_files_changed_since_date

# Local repository: Get all files changed since January 1, 2024
files = get_files_changed_since_date('2024-01-01')

# Remote repository: Specify owner and repo
files = get_files_changed_since_date('2024-01-01', owner='WCRP-CMIP', repo='CMIP6Plus_CVs')

# Remote repository: Use repo URL
files = get_files_changed_since_date('2024-01-01', repo_url='https://github.com/WCRP-CMIP/CMIP6Plus_CVs')

# Get only files in src-data directory
files = get_files_changed_since_date('2024-01-01', base_path_filter='src-data')

# Exclude build and cache files
files = get_files_changed_since_date('2024-01-01', exclude_paths=['build/', '__pycache__/'])
```

### 2. `get_files_changed_between_dates()`

Get all files changed between two specific dates.

**Parameters:**
- `start_date` (str): Start date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
- `end_date` (str): End date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
- `branch` (str, optional): Branch to check (default: 'main')
- `base_path_filter` (str, optional): Base path to filter files
- `exclude_paths` (list, optional): List of paths to exclude

**Returns:**
- `list`: List of unique file paths that were changed between the dates

**Example:**
```python
from cmipld.utils.git import get_files_changed_between_dates

# Local repository: Get files changed between January and June 2024
files = get_files_changed_between_dates('2024-01-01', '2024-06-01')

# Remote repository: Using owner/repo parameters
files = get_files_changed_between_dates(
    '2024-01-01', 
    '2024-06-01',
    owner='WCRP-CMIP',
    repo='CMIP6Plus_CVs'
)

# Filter to only files in src-data
files = get_files_changed_between_dates(
    '2024-01-01', 
    '2024-06-01',
    base_path_filter='src-data'
)
```

### 3. `get_files_changed_with_details()`

Get detailed information about files changed since a specific date.

**Parameters:**
- `since_date` (str): Date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
- `branch` (str, optional): Branch to check (default: 'main')
- `base_path_filter` (str, optional): Base path to filter files
- `exclude_paths` (list, optional): List of paths to exclude

**Returns:**
- `list`: List of dictionaries with file details containing:
  - `path`: File path
  - `commit_hash`: Commit hash
  - `author`: Author name
  - `email`: Author email
  - `date`: Commit date
  - `message`: Commit message

**Example:**
```python
from cmipld.utils.git import get_files_changed_with_details

# Local repository: Get detailed information about all changes since January 2024
details = get_files_changed_with_details('2024-01-01')

# Remote repository: Get detailed information
details = get_files_changed_with_details(
    '2024-01-01',
    owner='WCRP-CMIP',
    repo='CMIP6Plus_CVs'
)

for detail in details:
    print(f"File: {detail['path']}")
    print(f"Author: {detail['author']}")
    print(f"Date: {detail['date']}")
    print(f"Message: {detail['message']}")
    print(f"Commit: {detail['commit_hash']}")
    print()
```

### 4. `get_files_changed_from_github_url()`

Convenience function to get files changed from a GitHub URL.

**Parameters:**
- `github_url` (str): GitHub repository URL (e.g., 'https://github.com/user/repo')
- `since_date` (str): Date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
- `branch` (str, optional): Branch to check (default: 'main')
- `base_path_filter` (str, optional): Base path to filter files
- `exclude_paths` (list, optional): List of paths to exclude

**Returns:**
- `list`: List of unique file paths that were changed since the date

**Example:**
```python
from cmipld.utils.git import get_files_changed_from_github_url

# Get files changed in a remote repository
files = get_files_changed_from_github_url(
    'https://github.com/WCRP-CMIP/CMIP6Plus_CVs',
    '2024-01-01'
)
```

### 5. `get_files_changed_from_repo_shorthand()`

Convenience function to get files changed using 'owner/repo' shorthand notation.

**Parameters:**
- `repo_shorthand` (str): Repository in 'owner/repo' format (e.g., 'WCRP-CMIP/CMIP6Plus_CVs')
- `since_date` (str): Date in format 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'
- `branch` (str, optional): Branch to check (default: 'main')
- `base_path_filter` (str, optional): Base path to filter files
- `exclude_paths` (list, optional): List of paths to exclude

**Returns:**
- `list`: List of unique file paths that were changed since the date

**Example:**
```python
from cmipld.utils.git import get_files_changed_from_repo_shorthand

# Get files changed using shorthand notation
files = get_files_changed_from_repo_shorthand(
    'WCRP-CMIP/CMIP6Plus_CVs',
    '2024-01-01',
    base_path_filter='src-data'
)
```

## Usage Examples

### Basic Usage (Local Repository)

```python
from cmipld.utils.git import get_files_changed_since_date

# Get all files changed since a specific date in local repo
files = get_files_changed_since_date('2024-01-01')
print(f"Found {len(files)} files changed since 2024-01-01")
for file in files:
    print(f"- {file}")
```

### Remote Repository Usage

```python
from cmipld.utils.git import (
    get_files_changed_since_date,
    get_files_changed_from_github_url,
    get_files_changed_from_repo_shorthand
)

# Method 1: Using owner/repo parameters
files = get_files_changed_since_date(
    '2024-01-01',
    owner='WCRP-CMIP',
    repo='CMIP6Plus_CVs'
)

# Method 2: Using repo URL
files = get_files_changed_since_date(
    '2024-01-01',
    repo_url='https://github.com/WCRP-CMIP/CMIP6Plus_CVs'
)

# Method 3: Using convenience function with GitHub URL
files = get_files_changed_from_github_url(
    'https://github.com/WCRP-CMIP/CMIP6Plus_CVs',
    '2024-01-01'
)

# Method 4: Using convenience function with shorthand
files = get_files_changed_from_repo_shorthand(
    'WCRP-CMIP/CMIP6Plus_CVs',
    '2024-01-01'
)
```

### Advanced Filtering

```python
from cmipld.utils.git import get_files_changed_since_date

# Local repository: Get only data files, excluding build artifacts
files = get_files_changed_since_date(
    '2024-01-01',
    base_path_filter='src-data',
    exclude_paths=['build/', '__pycache__/', '.git/', 'node_modules/']
)

# Remote repository: Same filtering with remote repo
files = get_files_changed_since_date(
    '2024-01-01',
    owner='WCRP-CMIP',
    repo='CMIP6Plus_CVs',
    base_path_filter='src-data',
    exclude_paths=['build/', '__pycache__/', '.git/', 'node_modules/']
)
```

### Getting Detailed Information

```python
from cmipld.utils.git import get_files_changed_with_details

# Local repository: Get detailed commit information
details = get_files_changed_with_details('2024-01-01')

# Remote repository: Get detailed information
details = get_files_changed_with_details(
    '2024-01-01',
    owner='WCRP-CMIP',
    repo='CMIP6Plus_CVs'
)

# Group by author
authors = {}
for detail in details:
    author = detail['author']
    if author not in authors:
        authors[author] = []
    authors[author].append(detail['path'])

for author, files in authors.items():
    print(f"{author}: {len(files)} files")
```

## Date Formats

The functions accept various date formats:
- `'2024-01-01'` - Date only
- `'2024-01-01 12:00:00'` - Date and time
- `'2024-01-01T12:00:00'` - ISO format
- `'1 week ago'` - Relative dates (Git's natural language, local repos only)
- `'2024-01-01 --author="John Doe"'` - With additional Git log options (local repos only)

**Note**: Remote repositories using the GitHub API work best with standard date formats (YYYY-MM-DD).

## Error Handling

All functions include comprehensive error handling:
- **Local repositories**: Returns empty lists if Git commands fail
- **Remote repositories**: Returns empty lists if GitHub API calls fail
- **Network issues**: Gracefully handles connection problems
- **Authentication**: Works with public repositories without authentication
- **Rate limiting**: Handles GitHub API rate limits gracefully

Error messages are printed to help with debugging, but functions will not raise exceptions under normal circumstances.

## Remote Repository Support

The functions support three ways to specify remote repositories:

### 1. Owner/Repo Parameters
```python
files = get_files_changed_since_date(
    '2024-01-01',
    owner='WCRP-CMIP',
    repo='CMIP6Plus_CVs'
)
```

### 2. Repository URL
```python
files = get_files_changed_since_date(
    '2024-01-01',
    repo_url='https://github.com/WCRP-CMIP/CMIP6Plus_CVs'
)
```

### 3. Convenience Functions
```python
# Using GitHub URL
files = get_files_changed_from_github_url(
    'https://github.com/WCRP-CMIP/CMIP6Plus_CVs',
    '2024-01-01'
)

# Using shorthand notation
files = get_files_changed_from_repo_shorthand(
    'WCRP-CMIP/CMIP6Plus_CVs',
    '2024-01-01'
)
```

## Rate Limiting

When working with remote repositories, the functions use the GitHub API which has rate limits:
- **Unauthenticated requests**: 60 per hour
- **Authenticated requests**: 5,000 per hour

For heavy usage, consider setting up GitHub authentication or using local repository clones.

## Integration

These functions are automatically available when importing from the git utils module:

```python
from cmipld.utils.git import (
    get_files_changed_since_date,
    get_files_changed_between_dates,
    get_files_changed_with_details,
    get_files_changed_from_github_url,
    get_files_changed_from_repo_shorthand
)
```

Or import the entire git module:

```python
from cmipld.utils import git

# Local repository
files = git.get_files_changed_since_date('2024-01-01')

# Remote repository
files = git.get_files_changed_from_repo_shorthand('WCRP-CMIP/CMIP6Plus_CVs', '2024-01-01')
```
