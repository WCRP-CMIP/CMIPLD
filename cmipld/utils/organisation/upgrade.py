#!/usr/bin/env python3
"""
Update all the organisation institution files keeping the original authors. 

Usage:
    python upgrade_organisations.py [--dry-run]
    
"""

import sys
from pathlib import Path
import json
import os
import glob
import subprocess
import argparse
from collections import OrderedDict


# Add parent directory to path to import update_ror
sys.path.append(str(Path(__file__).parent))

from cmipld.utils import git,jsontools,organisation

# Path to organization data
repopath = './organisation/'


def update(filepath, author, dry_run=False, update=False, comment='organisation update'):
    mod,stat =jsontools.validate_and_fix_json(filepath)

    if not dry_run and (mod or update):              
    # Commit with original author
        git.commit_one(
            filepath,
            author,
            comment=f"Update {Path(filepath).stem}: {comment}"
        )


def process_organization_file(filepath, dry_run=False):
    """Process a single organization file
    
    Args:
        filepath: Path to the organization file
        dry_run: If True, show what would be done without making changes
        
    Returns:
        True if changes were made/would be made
        False if no changes needed
        None if there was an error
    """
    # Get the last committer using cmipld utility
    author = git.get_last_committer(filepath)
    
    if not author:
        print(f"⚠️  Could not get author for {filepath}, using default...")
        # return None
        author = 'cmip-ipo-bot'
        
    print(f"\n📄 Processing {filepath}")
    print(f"👤 Last committer: {author}")
    
    try:
        # Read the original file content
        with open(filepath, 'r', encoding='utf-8') as f:
            original_content = f.read()
            original_data = json.loads(original_content, object_pairs_hook=OrderedDict)
        
        # Check if it's an institution or consortium
        if '@type' not in original_data:
            print(f"⚠️  No type field in {filepath}, skipping...")
            
            return None
            
        ldtypes = original_data.get('@type', [])
        
        # Process based on type
        if 'wcrp:institution' in ldtypes:
            # Get required fields
            ror = original_data.get('ror')
            validation_key = original_data.get('validation-key')
            
            if not ror or ror == 'pending':
                print(f"⚠️  No valid ROR for {filepath}, skipping...")
                return None
            
            if not dry_run:
                print(f"🔄 Updating institution data from ROR: {ror}")
                try:
                    # Get updated data from ROR
                    new_data = organisation.get_institution(ror, validation_key)
                    
                    # Check if data changed
                    if json.dumps(original_data, sort_keys=True) == json.dumps(new_data, sort_keys=True):
                        print(f"ℹ️  No changes from ROR - data is up to date")
                        update(filepath, author, dry_run, update=False, comment='Updating file')
                        return False
                    
                    # Write updated data directly to file
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(new_data, f, indent=2, ensure_ascii=False)
                        f.write('\n')
                    
                    print(f"✅ Successfully updated from ROR")
                    
                    update(filepath, author, dry_run, update=True, comment='new ROR data')
                    
                    return True
                        
                except Exception as e:
                    print(f"❌ Error getting ROR data: {e}")
                    return None
            else:
                print(f"🔄 Would update institution data from ROR: {ror}")
                return True
                    
        elif 'wcrp:consortium' in ldtypes:
            print(f"ℹ️  Consortium type - no ROR update available")
            update(filepath, author, dry_run, update=False, comment='Updating file order.')
            return False
        else:
            print(f"⚠️  Unknown type in {filepath}, skipping...")
            return None
            
    except Exception as e:
        print(f"❌ Error processing {filepath}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function to process all organization files"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Update organization files from ROR"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Show what would be done without making actual changes"
    )
    
    parser.add_argument(
        "--repo-path",
        type=str,
        default=repopath,
        help="Path to the organization repository"
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🆗️ DRY RUN MODE - No changes will be made")
        print("="*50)
    
    print("🚀 Starting organization file update from ROR...")
    
    # Get all JSON files (excluding graph files and context)
    files = glob.glob(os.path.join(repopath, '*.json'))
    files = [f for f in files if not any(skip in f for skip in ['graph.', '_context_'])]
    
    print(f"📁 Found {len(files)} organization files to check")
    
    # Track results
    successful = 0
    failed = 0
    unchanged = 0
    
    # Process each file
    for filepath in sorted(files):
        result = process_organization_file(filepath, dry_run=args.dry_run)
        if result is None:
            failed += 1
        elif result:
            successful += 1
        else:
            unchanged += 1
    
    # Summary
    print("\n" + "="*50)
    print(f"✅ Successfully updated: {successful} files")
    print(f"ℹ️  Unchanged: {unchanged} files (already up to date)")
    print(f"❌ Failed to process: {failed} files")
    print(f"📊 Total files: {len(files)}")
    
    # Create a branch and push if we made changes
    if successful > 0 and not args.dry_run:
        branch_name = "update-organizations-from-ror"
        print(f"\n🌿 Creating branch: {branch_name}")
        
        try:
            # Create and checkout new branch
            subprocess.run(['git', 'checkout', '-b', branch_name], check=True)
            
            # Push the branch
            print(f"🚀 Pushing branch: {branch_name}")
            subprocess.run(['git', 'push', '-u', 'origin', branch_name], check=True)
            
            print(f"\n✅ All changes pushed to branch: {branch_name}")
            print("📝 Please create a pull request to merge these changes.")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Error with git operations: {e}")
    elif args.dry_run and successful > 0:
        print(f"\n🆗️ DRY RUN: Would have created branch 'update-organizations-from-ror' with {successful} files")
    

# if __name__ == '__main__':
#     main()