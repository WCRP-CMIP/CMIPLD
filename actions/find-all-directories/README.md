# Find All Directories Action

Finds all top-level subdirectories in the repository (excluding hidden directories).

## Outputs

| Name | Description |
|------|-------------|
| `directories` | JSON array of all directory names |

## Usage

### From This Repository

```yaml
jobs:
  find-all:
    runs-on: ubuntu-latest
    outputs:
      dirs: ${{ steps.find.outputs.directories }}
    steps:
      - uses: ./actions/find-all-directories
        id: find
      
      - name: Display results
        run: echo "All directories: ${{ steps.find.outputs.directories }}"
```

### From Another Repository

```yaml
jobs:
  find-all:
    runs-on: ubuntu-latest
    outputs:
      dirs: ${{ steps.find.outputs.directories }}
    steps:
      - uses: WCRP-CMIP/CMIP-LD/actions/find-all-directories@main
        id: find
      
      - name: Display results
        run: echo "All directories: ${{ steps.find.outputs.directories }}"
```

### With Matrix Strategy

```yaml
jobs:
  find-all:
    runs-on: ubuntu-latest
    outputs:
      dirs: ${{ steps.find.outputs.directories }}
    steps:
      - uses: WCRP-CMIP/CMIP-LD/actions/find-all-directories@main
        id: find
  
  process-all:
    needs: find-all
    runs-on: ubuntu-latest
    strategy:
      matrix:
        directory: ${{ fromJson(needs.find-all.outputs.dirs) }}
    steps:
      - name: Process directory
        run: echo "Processing ${{ matrix.directory }}"
```

### Combined Usage with Conditional

```yaml
name: Process Directories

on:
  workflow_dispatch:
    inputs:
      updated:
        description: 'Process only updated directories'
        type: boolean
        default: false

jobs:
  find-directories:
    runs-on: ubuntu-latest
    outputs:
      dirs: ${{ steps.updated.outputs.directories || steps.all.outputs.directories }}
    steps:
      - uses: WCRP-CMIP/CMIP-LD/actions/find-updated-directories@main
        id: updated
        if: ${{ inputs.updated == true }}
        with:
          base-branch: production
      
      - uses: WCRP-CMIP/CMIP-LD/actions/find-all-directories@main
        id: all
        if: ${{ inputs.updated == false }}
  
  process:
    needs: find-directories
    runs-on: ubuntu-latest
    strategy:
      matrix:
        directory: ${{ fromJson(needs.find-directories.outputs.dirs) }}
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      
      - name: Process directory
        run: validate_json "${{ matrix.directory }}" --verbose
```

### Using Specific Version Tag

```yaml
- uses: WCRP-CMIP/CMIP-LD/actions/find-all-directories@v1.0.0
  id: find
```

## Example Output

```json
["actions", "cmipld", "copier", "notebooks", "static"]
```
