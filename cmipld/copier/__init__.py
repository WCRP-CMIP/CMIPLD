#!/usr/bin/env python3
"""
CMIPLD Copier CLI - Install and update templates.

Usage:
    cmipcopier list                   # List available templates
    cmipcopier documentation          # Install documentation template
    cmipcopier documentation update   # Update existing documentation
    cmipcopier workflows              # Install workflows template
    cmipcopier workflows update       # Update existing workflows
"""

import argparse
import subprocess
import sys
import os
import re
import shutil
from pathlib import Path


REPO_URL = "https://github.com/WCRP-CMIP/CMIPLD.git"
LOCAL_TEMPLATE_PATH = None  # Set via --local flag
TEMPLATES = {
    "documentation": "MkDocs documentation site with shadcn theme",
    "workflows": "Complete GitHub Actions workflow setup for CMIP repositories",
}


def run_command(cmd: list, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    kwargs = {"check": check}
    if capture:
        kwargs["capture_output"] = True
        kwargs["text"] = True
    return subprocess.run(cmd, **kwargs)


def get_repo_info() -> dict:
    """Get repo info from gh CLI or git remote."""
    info = {
        "repo_owner": "WCRP-CMIP",
        "repo_name": Path.cwd().name,
        "description": "",
    }
    
    # Try gh CLI first
    if shutil.which("gh"):
        try:
            result = run_command(
                ["gh", "repo", "view", "--json", "owner,name,description", "-q", 
                 "[.owner.login, .name, .description] | @tsv"],
                capture=True, check=False
            )
            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split("\t")
                if len(parts) >= 2:
                    info["repo_owner"] = parts[0]
                    info["repo_name"] = parts[1]
                if len(parts) >= 3:
                    info["description"] = parts[2]
                return info
        except Exception:
            pass
    
    # Fallback to git remote
    try:
        result = run_command(["git", "remote", "get-url", "origin"], capture=True, check=False)
        if result.returncode == 0:
            url = result.stdout.strip()
            match = re.search(r'github\.com[:/]([^/]+)/([^/.]+)', url)
            if match:
                info["repo_owner"] = match.group(1)
                info["repo_name"] = match.group(2).replace(".git", "")
    except Exception:
        pass
    
    return info


def clone_template() -> str:
    """Clone the CMIPLD repo to a temp directory, return path."""
    global LOCAL_TEMPLATE_PATH
    
    if LOCAL_TEMPLATE_PATH:
        print(f"Using local template: {LOCAL_TEMPLATE_PATH}")
        return LOCAL_TEMPLATE_PATH
    
    tmp_dir = "/tmp/cmipld-template"
    
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    
    print(f"Cloning CMIPLD templates...")
    run_command(["git", "clone", "--depth=1", REPO_URL, tmp_dir])
    
    return tmp_dir


def list_templates():
    """List available templates."""
    print("\nAvailable CMIPLD templates:\n")
    for name, desc in TEMPLATES.items():
        print(f"  {name:20} - {desc}")
    print()


def install_template(template: str, destination: str = "."):
    """Install a template to destination."""
    if template not in TEMPLATES:
        print(f"Error: Unknown template '{template}'")
        print(f"Available templates: {', '.join(TEMPLATES.keys())}")
        sys.exit(1)
    
    if not shutil.which("copier"):
        print("Error: copier not found. Install with: pip install copier")
        sys.exit(1)
    
    # Clone template repo
    tmp_dir = clone_template()
    template_path = os.path.join(tmp_dir, "copier", template)
    
    if not os.path.exists(template_path):
        print(f"Error: Template path not found: {template_path}")
        sys.exit(1)
    
    # Check for existing answers file
    answers_file_map = {
        "documentation": ".copier-answers-documentation.yml",
        "workflows": ".copier-answers-workflows.yml"
    }
    answers_file = os.path.join(destination, answers_file_map.get(template, ".copier-answers.yml"))
    
    # Get repo info
    info = get_repo_info()
    print(f"Detected: {info['repo_owner']}/{info['repo_name']}")
    
    # Build copier command
    cmd = [
        "copier", "copy",
        "--overwrite",  # Overwrite on conflicts
        template_path, destination,
        "--data", f"repo_owner={info['repo_owner']}",
        "--data", f"repo_name={info['repo_name']}",
    ]
    
    # If answers file exists, use it for defaults (non-interactive)
    if os.path.exists(answers_file):
        print(f"Found existing configuration: {os.path.basename(answers_file)}")
        print("Using saved answers (non-interactive mode)")
        cmd.extend(["--defaults", "--answers-file", answers_file])
    else:
        print(f"No existing configuration found")
        print("Interactive mode: please answer questions")
    
    if info["description"]:
        cmd.extend(["--data", f"description={info['description']}"])
    
    print(f"Installing {template} template...")
    run_command(cmd, check=False)
    
    print("\n✅ Template installed successfully!")
    if template == "workflows":
        print(f"📝 Configuration saved to: {os.path.basename(answers_file)}")
        print("🚀 You can now:")
        print("   - Push to src-data branch to trigger src-data-change workflow")
        print("   - Push to docs branch to trigger docs-change workflow")
        print("   - Go to Actions tab to manually run any workflow")
        print(f"\n💡 To update: Just run 'cmipcopier {template}' again (uses saved config)")
    elif template == "documentation":
        print(f"📝 Configuration saved to: {os.path.basename(answers_file)}")
        print("🚀 Run 'mkdocs serve' from src/mkdocs to preview.")
        print(f"\n💡 To update: Run 'cmipcopier {template} update'")


def update_template(template: str, destination: str = "."):
    """Update an existing project from template."""
    if template not in TEMPLATES:
        print(f"Error: Unknown template '{template}'")
        sys.exit(1)
    
    if not shutil.which("copier"):
        print("Error: copier not found. Install with: pip install copier")
        sys.exit(1)
    
    # Each template has its own answers file
    answers_file_map = {
        "documentation": ".copier-answers-documentation.yml",
        "workflows": ".copier-answers-workflows.yml"
    }
    
    answers_file = os.path.join(destination, answers_file_map.get(template, ".copier-answers.yml"))
    
    if not os.path.exists(answers_file):
        print(f"Note: No {os.path.basename(answers_file)} found")
        print(f"Running install instead of update...")
        install_template(template, destination)
        return
    
    # Clone template repo
    tmp_dir = clone_template()
    template_path = os.path.join(tmp_dir, "copier", template)
    
    print(f"Updating {template} template...")
    print(f"Using configuration from: {os.path.basename(answers_file)}")
    
    cmd = [
        "copier", "copy",
        "--force",
        "--overwrite",  # Overwrite on conflicts
        "--defaults",
        "--answers-file", answers_file,
        template_path, destination
    ]
    
    run_command(cmd, check=False)
    
    print("\n✅ Template updated successfully!")


def main():
    global LOCAL_TEMPLATE_PATH
    
    parser = argparse.ArgumentParser(
        description="CMIPLD Copier CLI - Install and update templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cmipcopier list                   List available templates
  cmipcopier documentation          Install documentation template
  cmipcopier documentation update   Update existing documentation
  cmipcopier workflows              Install workflows template
  cmipcopier workflows update       Update existing workflows
  cmipcopier workflows --local /path/to/CMIP-LD   Use local template
        """
    )
    
    parser.add_argument(
        "template",
        nargs="?",
        help="Template name (e.g., 'documentation', 'workflows') or 'list'"
    )
    parser.add_argument(
        "action",
        nargs="?",
        default="install",
        choices=["install", "update"],
        help="Action to perform (default: install)"
    )
    parser.add_argument(
        "-d", "--destination",
        default=".",
        help="Destination directory (default: current directory)"
    )
    parser.add_argument(
        "-l", "--local",
        help="Use local CMIPLD repo path instead of cloning from GitHub"
    )
    
    args = parser.parse_args()
    
    if args.local:
        LOCAL_TEMPLATE_PATH = args.local
    
    if not args.template or args.template == "list":
        list_templates()
        return
    
    if args.action == "update":
        update_template(args.template, args.destination)
    else:
        install_template(args.template, args.destination)


if __name__ == "__main__":
    main()
