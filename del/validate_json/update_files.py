import json,glob
import subprocess
from pathlib import Path
from cmipld.utils.validate_json.git_integration import GitCoauthorManager


git = GitCoauthorManager(enable_coauthors=True, use_last_author=True)


files = glob.glob('*/*.json')
print(f"Found {len(files)} JSON files")


# # Update JSON
# with open(filepath, 'r') as f:
#     data = json.load(f)
# data["last_modified"] = "2025-10-13"
# with open(filepath, 'w') as f:
#     json.dump(data, f, indent=4)

# # Get last commit message
# last_msg = subprocess.run(
#     ['git', 'log', '-n', '1', '--pretty=format:%B', '--', filepath],
#     capture_output=True, text=True
# ).stdout.strip()






# git.track_file_modification(filepath)
# last_msg = git.get_last_commit_message(filepath)
# print(f"Last commit message for {filepath}:\n{last_msg}")
# # git.create_commit_with_coauthors(message=last_msg, files=[filepath])


