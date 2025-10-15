# del/ - Archived Redundant Files

This folder contains files that were moved out of active development.

## Contents

### validate_json/
- **update_files.py** - Test/scratch file (DELETED from production)
  - Incomplete implementation
  - Contains commented-out experimental code
  - Not imported anywhere

### old_git_integration/
- **git_integration.py.backup** - Backup before refactoring
  - Original version saved before moving functions to utils/git
  - Keep for rollback if needed

## Timeline

- Created: 2025-10-13
- Review after: 2025-11-01
- Delete by: 2025-12-01

## Restore

If needed:
```bash
python move_redundant_files.py --restore
```

See ../REDUNDANT_FILES_MANIFEST.md for details.
