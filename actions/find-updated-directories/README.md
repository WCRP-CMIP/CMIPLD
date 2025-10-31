# Find Updated Directories Action

Finds directories that have been modified between the base branch and current HEAD.

## Inputs

| Name | Description | Required | Default |
|------|-------------|----------|---------|
| `base-branch` | Base branch to compare against | No | `production` |

## Outputs

| Name | Description |
|------|-------------|
| `directories` | JSON array of updated directory names |

## Usage

### From This Repository

```yaml
jobs:
  find-changes:
    runs-on: ubuntu-latest
    outputs:
      dirs: ${{ steps.find.outputs.directories }}
    steps:
      - uses: ./actions/find-updated-directories
        id: find
        with:
          base-branch: production
      
      - name: Display results
        run: echo "Updated directories: ${{ steps.find.outputs.directories }}"
```

### From Another Repository

```yaml
jobs:
  find-changes:
    runs-on: ubuntu-latest
    outputs:
      dirs: ${{ steps.find.outputs.directories }}
    steps:
      - uses: WCRP-CMIP/CMIP-LD/actions/find-updated-directories@main
        id: find
        with:
          base-branch: production
      
      - name: Display results
        run: echo "Updated directories: ${{ steps.find.outputs.directories }}"
```

### With Matrix Strategy

```yaml
jobs:
  find-changes:
    runs-on: ubuntu-latest
    outputs:
      dirs: ${{ steps.find.outputs.directories }}
    steps:
      - uses: WCRP-CMIP/CMIP-LD/actions/find-updated-directories@main
        id: find
        with:
          base-branch: production
  
  process-changes:
    needs: find-changes
    runs-on: ubuntu-latest
    strategy:
      matrix:
        directory: ${{ fromJson(needs.find-changes.outputs.dirs) }}
    steps:
      - name: Process directory
        run: echo "Processing ${{ matrix.directory }}"
```

### Using Different Base Branch

```yaml
- uses: WCRP-CMIP/CMIP-LD/actions/find-updated-directories@main
  id: find
  with:
    base-branch: develop  # Compare against develop instead
```

### Using Specific Version Tag

```yaml
- uses: WCRP-CMIP/CMIP-LD/actions/find-updated-directories@v1.0.0
  id: find
  with:
    base-branch: production
```

## Example Output

```json
["experiment", "activity", "source_type"]
```
