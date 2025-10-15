#!/usr/bin/env python3
"""
Verify the cleanup and reorganization was successful
"""

from pathlib import Path
import sys


def check_file_exists(path, should_exist=True):
    """Check if file exists and print status."""
    p = Path(path)
    exists = p.exists()
    
    if should_exist and exists:
        print(f"✅ {path}")
        return True
    elif not should_exist and not exists:
        print(f"✅ {path} (correctly absent)")
        return True
    elif should_exist and not exists:
        print(f"❌ MISSING: {path}")
        return False
    else:
        print(f"❌ SHOULD NOT EXIST: {path}")
        return False


def main():
    print("🔍 Verifying CMIP-LD Git Reorganization\n")
    
    checks = []
    
    print("📦 New Files Created:")
    checks.append(check_file_exists("cmipld/utils/git/git_validation_utils.py", True))
    checks.append(check_file_exists("cmipld/utils/git/__init__.py", True))
    checks.append(check_file_exists("examples/example_clean_usage.py", True))
    
    print("\n🗑️  Redundant Files Moved:")
    checks.append(check_file_exists("del/validate_json/update_files.py", True))
    checks.append(check_file_exists("del/old_git_integration/git_integration.py.backup", True))
    checks.append(check_file_exists("cmipld/utils/validate_json/update_files.py", False))
    
    print("\n📚 Documentation Created:")
    checks.append(check_file_exists("INDEX.md", True))
    checks.append(check_file_exists("COMPLETE_CLEANUP_SUMMARY.md", True))
    checks.append(check_file_exists("CLEANUP_GUIDE.md", True))
    checks.append(check_file_exists("GIT_REORGANIZATION_SUMMARY.md", True))
    checks.append(check_file_exists("QUICK_REFERENCE.md", True))
    checks.append(check_file_exists("REDUNDANT_FILES_MANIFEST.md", True))
    checks.append(check_file_exists("del/README.md", True))
    
    print("\n🔧 Scripts Created:")
    checks.append(check_file_exists("move_redundant_files.py", True))
    checks.append(check_file_exists("move_redundant_files.sh", True))
    
    print("\n" + "=" * 60)
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✅ ALL CHECKS PASSED ({passed}/{total})")
        print("\n🎉 Reorganization completed successfully!")
        print("\nNext steps:")
        print("  1. Review documentation in INDEX.md")
        print("  2. Try: python examples/example_clean_usage.py")
        print("  3. Follow CLEANUP_GUIDE.md for remaining refactoring")
        return 0
    else:
        print(f"❌ SOME CHECKS FAILED ({passed}/{total} passed)")
        print("\nPlease review the failed checks above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
