#!/usr/bin/env python3
"""
Auto-setup script for MkDocs Publisher template with answer reuse.
Detects git/GitHub information and runs copier with smart defaults.
Saves and reuses previous answers for convenience.
"""
import subprocess
import os
import json
import sys
import yaml
from pathlib import Path
from datetime import datetime


def install_dependencies():
    """Install required dependencies."""
    try:
        # pip uninstall copier pydantic typing_extensions typing_inspection
# pip install copier
        subprocess.run('pip uninstall copier pydantic typing_extensions typing_inspection --yes'.split(), check=True)
        subprocess.run(["pip", "install", "copier", "pyyaml", 'mkdocs-literate-nav','y'], check=True)
        print("✅ Dependencies installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Error installing dependencies: {e}")
        sys.exit(1)


def run_command(cmd, capture=True, cwd=None):
    """Run a command and return output or success status."""
    try:
        shell = True
        if capture:
            result = subprocess.run(cmd, shell=shell, capture_output=True, text=True, cwd=cwd)
            return result.stdout.strip() if result.returncode == 0 else None
        else:
            result = subprocess.run(cmd, shell=shell, cwd=cwd)
            return result.returncode == 0
    except:
        return None


def get_github_username():
    """Get GitHub username using gh CLI."""
    # Try gh CLI first (most reliable)
    username = run_command("gh api user --jq .login")
    if username:
        return username
    
    # Fallback: try gh auth status
    auth_output = run_command("gh auth status 2>&1")
    if auth_output and "Logged in to github.com" in auth_output:
        # Extract username from output like "Logged in to github.com as username"
        for line in auth_output.split('\n'):
            if 'as ' in line and 'github.com' in line:
                username = line.split(' as ')[-1].split(' ')[0]
                if username and username != 'github.com':
                    return username
    
    return None


def get_git_config(key, default=""):
    """Get git config value."""
    value = run_command(f"git config --get {key}")
    return value if value else default


def get_remote_info():
    """Get git remote information and extract GitHub username/repo."""
    remote_url = run_command("git remote get-url origin")
    
    if not remote_url:
        return None, None
    
    # Parse GitHub URL
    if 'github.com' in remote_url:
        # Remove common prefixes and suffixes
        repo_path = remote_url
        
        # Handle HTTPS URLs
        if remote_url.startswith('https://github.com/'):
            repo_path = remote_url.replace('https://github.com/', '')
        # Handle SSH URLs
        elif remote_url.startswith('git@github.com:'):
            repo_path = remote_url.replace('git@github.com:', '')
        # Handle HTTPS with credentials
        elif 'https://' in remote_url and '@github.com/' in remote_url:
            repo_path = remote_url.split('@github.com/')[-1]
        
        # Remove .git suffix
        repo_path = repo_path.replace('.git', '')
        
        # Extract username and repo
        if '/' in repo_path:
            parts = repo_path.split('/')
            if len(parts) >= 2:
                username = parts[0]
                repo = parts[1]
                # Clean up any extra characters
                username = username.strip()
                repo = repo.strip()
                if username and repo:
                    return username, repo
    
    return None, None


def get_current_dir_name():
    """Get current directory name."""
    return Path.cwd().name


def read_readme_content():
    """Read README.md content or return fallback message."""
    readme_files = ['./README.md', './readme.md', './Readme.md']
    
    for readme_file in readme_files:
        readme_path = Path(readme_file)
        if readme_path.exists():
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Clean up the README content for MkDocs
                lines = content.split('\n')
                cleaned_lines = []
                skip_first_title = False
                
                for i, line in enumerate(lines):
                    # Skip first H1 title if it looks like a project title
                    if i == 0 and line.startswith('# '):
                        title = line[2:].strip()
                        if any(word in title.lower() for word in ['documentation', 'docs', 'project', 'readme']):
                            skip_first_title = True
                            continue
                    
                    # Skip empty lines after skipped title
                    if skip_first_title and not line.strip():
                        if not cleaned_lines:
                            continue
                    
                    cleaned_lines.append(line)
                
                cleaned_content = '\n'.join(cleaned_lines).strip()
                print(f"✅ Found and loaded README content from {readme_file}")
                
                print(f"   📄 Content length: {len(cleaned_content)} characters")
                return cleaned_content
                
            except Exception as e:
                print(f"⚠️  Error reading {readme_file}: {e}")
                continue
    
    print("⚠️  No README.md found")
    return "Content not found, enter manually here"


def save_answers(data, answers_file=".copier-answers.yml"):
    """Save answers to a YAML file with metadata."""
    try:
        # Add metadata
        answers_with_meta = {
            '_src_path': data.get('template_path', ''),
            '_commit': 'HEAD',
            '_timestamp': datetime.now().isoformat(),
            '_auto_generated': True
        }
        
        # Add the actual answers
        answers_with_meta.update(data)
        
        # Remove template_path from answers (it's stored in _src_path)
        if 'template_path' in answers_with_meta:
            del answers_with_meta['template_path']
        
        with open(answers_file, 'w') as f:
            yaml.dump(answers_with_meta, f, default_flow_style=False, sort_keys=False)
        
        print(f"💾 Saved answers to {answers_file}")
        return True
        
    except Exception as e:
        print(f"⚠️  Error saving answers: {e}")
        return False


def load_previous_answers(answers_file=".copier-answers.yml"):
    """Load previous answers from YAML file."""
    answers_path = Path(answers_file)
    
    if not answers_path.exists():
        return None
    
    try:
        with open(answers_path, 'r') as f:
            answers = yaml.safe_load(f)
        
        if not answers:
            return None
        
        # Extract metadata
        metadata = {
            'src_path': answers.get('_src_path', ''),
            'commit': answers.get('_commit', ''),
            'timestamp': answers.get('_timestamp', ''),
            'auto_generated': answers.get('_auto_generated', False)
        }
        
        # Remove metadata from answers
        data = {k: v for k, v in answers.items() if not k.startswith('_')}
        
        return data, metadata
        
    except Exception as e:
        print(f"⚠️  Error loading previous answers: {e}")
        return None


def prompt_reuse_answers(data, metadata, answers_file):
    """Prompt user to reuse previous answers."""
    print(f"\n📋 Found previous answers in {answers_file}")
    print(f"   📁 Location: {Path(answers_file).absolute()}")
    
    if metadata.get('timestamp'):
        try:
            timestamp = datetime.fromisoformat(metadata['timestamp'])
            print(f"   🕐 Generated: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            print(f"   🕐 Generated: {metadata['timestamp']}")
    
    if metadata.get('src_path'):
        print(f"   📦 Template: {metadata['src_path']}")
    
    print(f"   🤖 Auto-generated: {'Yes' if metadata.get('auto_generated') else 'No'}")
    
    print("\n📄 Previous values:")
    for key, value in data.items():
        if key == 'readme_content':
            print(f"   {key}: {str(value)[:60]}...")
        else:
            print(f"   {key}: {value}")
    
    print("\n🔄 Reuse these previous answers?")
    response = input("[Y/n]: ").strip().lower()
    
    return response in ['', 'y', 'yes']


def detect_template_path():
    """Try to detect template path relative to this script."""
    script_path = Path(__file__).parent
    
    # Common locations to check
    possible_paths = [
        script_path,
        script_path.parent / "copier" / "mkdocs",
        Path.cwd() / "copier" / "mkdocs",
        script_path.parent.parent / "copier" / "mkdocs",
    ]
    
    for path in possible_paths:
        if (path / "copier.yml").exists():
            return str(path)
    
    return None


def run_copier_with_data(template_path, data):
    """Run copier with the provided data."""
    # Build copier command with data arguments
    cmd_parts = ["copier", "copy", template_path, "."]
    
    for key, value in data.items():
        if key != 'template_path':  # Skip template_path, it's already in the command
            cmd_parts.extend(["--data", f"{key}={value}"])
    
    # Add additional flags
    cmd_parts.extend(["--overwrite", "--quiet"])
    
    # Run copier command
    print(f"\n🔄 Running copier...")
    cmd = " ".join(f'"{part}"' if " " in part else part for part in cmd_parts)
    print(f"   {cmd[:100]}...") if len(cmd) > 100 else print(f"   {cmd}")
    
    return run_command(cmd, capture=False)


def print_next_steps(data):
    """Print next steps after successful generation."""
    print("\n✅ Project generated successfully!")
    print("\n📝 Next steps:")
    print("   1. python scripts/sync.py           # Sync content and generate JSON pages")
    print("   2. mkdocs serve                     # Start development server")
    print("   3. mkdocs gh-deploy                 # Deploy to GitHub Pages")
    
    # Show generated files
    generated_files = [
        "scripts/sync.py",
        "README.md", 
        ".github/workflows/deploy.yml"
    ]
    
    print(f"\n📄 Generated files:")
    for file_path in generated_files:
        if Path(file_path).exists():
            print(f"   ✅ {file_path}")
        else:
            print(f"   ❓ {file_path}")
    
    # Check for JSON data folder
    json_folder = data.get('json_data_folder', 'json_data')
    if not Path(json_folder).exists():
        print(f"\n💡 Tip: Create {json_folder}/ folder and add .json files to auto-generate pages")
    
    print(f"\n💾 Answers saved to .copier-answers.yml for future reuse")


def detect_and_run_copier(answers_file):
    """Detect values and run copier (original main logic)."""
    # Detect GitHub username (prioritize gh CLI)
    print("   Checking GitHub authentication...")
    github_username = get_github_username()
    if github_username:
        print(f"   ✅ GitHub user: {github_username}")
    else:
        print("   ⚠️  GitHub CLI not authenticated (run 'gh auth login')")
    
    # Get git information
    print("   Checking git configuration...")
    git_user = get_git_config('user.name', 'Your Name')
    git_email = get_git_config('user.email', 'your.email@example.com')
    
    # Get remote information
    print("   Checking git remote...")
    remote_username, remote_repo = get_remote_info()
    
    # If we have remote info, prioritize it for repo name
    if remote_username and remote_repo:
        print(f"   ✅ Detected from git remote: {remote_username}/{remote_repo}")
        username = remote_username
        repo_name = remote_repo
    else:
        # Fallback to GitHub username or other methods
        username = github_username or remote_username or git_user.lower().replace(' ', '') or 'your-username'
        repo_name = get_current_dir_name()
    
    project_name = repo_name.replace('-', ' ').replace('_', ' ').title()
    
    # Read README content
    print("   Reading README content...")
    readme_content = read_readme_content()
    
    # Get template path
    template_path = None
    if len(sys.argv) > 1:
        template_path = sys.argv[1]
    else:
        template_path = detect_template_path()
    
    if not template_path:
        print("\n❌ Error: Template path not found!")
        print("Usage:")
        print("   python auto-setup.py /path/to/template")
        print("   python auto-setup.py  # (tries to auto-detect)")
        sys.exit(1)
    
    # Build data dictionary with corrected repository info
    data = {
        'project_name': f"{project_name} Documentation",
        'repo_name': repo_name,
        'author_name': git_user,
        'author_email': git_email,
        'github_username': username,
        'site_url': f"https://{username}.github.io/{repo_name}/",
        'repo_url': f"https://github.com/{username}/{repo_name}",
        'json_data_folder': 'json_data',
        'description': f"Documentation for {project_name}",
        'readme_content': readme_content,
        'template_path': template_path,
        'header_color': 'blue',
        'generate_static_files': True,
        'static_files_folder': 'static_output'
    }
    
    print("\n📋 Detected information:")
    for key, value in data.items():
        if key == 'readme_content':
            print(f"   {key}: {str(value)[:60]}...")
        elif key == 'template_path':
            print(f"   {key}: {value}")
        else:
            print(f"   {key}: {value}")
    
    if not Path(template_path).exists():
        print(f"\n❌ Error: Template path does not exist: {template_path}")
        sys.exit(1)
    
    print(f"\n📁 Using template: {template_path}")
    
    # Ask for confirmation
    print(f"\n🚀 Ready to generate project with detected values.")
    confirm = input("Continue? [Y/n]: ").strip().lower()
    
    if confirm and confirm not in ['y', 'yes', '']:
        print("❌ Cancelled by user")
        sys.exit(0)
    
    # Save answers before running copier
    save_answers(data, answers_file)
    
    # Run copier
    success = run_copier_with_data(template_path, data)
    
    if success:
        print_next_steps(data)
    else:
        print("\n❌ Error running copier command")
        print("   Check that copier is installed: pip install copier")
        sys.exit(1)


def main():
    """Main detection and copier execution with answer reuse."""
    print("🔍 Auto-detecting project information...")
    
    # Check for previous answers first
    answers_file = ".copier-answers.yml"
    previous_data = load_previous_answers(answers_file)
    
    if previous_data:
        data, metadata = previous_data
        
        # Prompt to reuse previous answers
        if prompt_reuse_answers(data, metadata, answers_file):
            print("\n✅ Using previous answers!")
            
            # Get template path
            template_path = None
            if len(sys.argv) > 1:
                template_path = sys.argv[1]
            else:
                template_path = metadata.get('src_path') or detect_template_path()
            
            if template_path:
                # Run copier with previous answers
                success = run_copier_with_data(template_path, data)
                if success:
                    print_next_steps(data)
                    return
                else:
                    print("\n⚠️  Failed to run copier with previous answers, detecting new values...")
            else:
                print("\n⚠️  Template path not found, detecting new values...")
        else:
            print("\n🔄 Detecting new values...")
    
    # Detect new values (original logic)
    detect_and_run_copier(answers_file)


if __name__ == "__main__":
    main()
