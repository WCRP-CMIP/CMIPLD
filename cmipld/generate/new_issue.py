import json
import sys
import os
import re
import argparse
import importlib.util
import subprocess
from pathlib import Path

from cmipld.utils.validate_json import JSONValidator

# Resolve paths relative to GITHUB_WORKSPACE (CI) or cwd (local)
def _repo_root() -> str:
    import os
    return os.environ.get('GITHUB_WORKSPACE', os.getcwd())

HANDLER_PATH = '.github/ISSUE_SCRIPT/'
DATA_PATH    = './'

IGNORE_LABELS = {
    'review', 'alpha', 'keep-open', 'delta', 'Review',
    'universal', 'universe', 'pull_req', 'Pull_req', 'critical',
    'emd-submission',   # category marker, not a handler type
    'needs-review',     # workflow label, not a type
}

FOLDER_MAPPING = {
    'institution': 'organisation',
}

# Magic marker embedded in every bot comment so we can find-and-update it.
# One marker per (issue/PR, slot) pair.
_BOT_MARKER_ISSUE = "<!-- emd-bot-issue-status -->"
_BOT_MARKER_PR    = "<!-- emd-bot-pr-report -->"


# ── GitHub comment upsert ─────────────────────────────────────────────────────

def _gh_api(path: str, method: str = "GET", fields: dict | None = None) -> dict | list | None:
    """Thin wrapper around `gh api`."""
    cmd = ["gh", "api", path, "-X", method]
    if fields:
        for k, v in fields.items():
            cmd += ["-f", f"{k}={v}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout) if result.stdout.strip() else None
    except subprocess.CalledProcessError as e:
        print(f"  gh api {method} {path} failed: {e.stderr[:200]}", flush=True)
        return None


def _repo() -> str:
    """owner/repo from gh CLI."""
    try:
        r = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True, text=True, check=True,
        )
        return r.stdout.strip()
    except Exception:
        return os.environ.get("GITHUB_REPOSITORY", "")


def upsert_comment(number: int, body: str, marker: str, on: str = "issue") -> None:
    """
    Create or update a comment containing *marker* on issue or PR *number*.
    on: "issue" or "pr"
    """
    repo = _repo()
    if not repo:
        print("  ⚠ Cannot upsert comment: repo unknown", flush=True)
        return

    path = f"repos/{repo}/issues/{number}/comments"
    comments = _gh_api(path) or []

    existing_id = None
    for c in comments:
        if marker in c.get("body", ""):
            existing_id = c["id"]
            break

    import datetime
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    full_body = body + f"\n\n_Last updated: {ts}_\n\n{marker}"

    if existing_id:
        _gh_api(f"repos/{repo}/issues/comments/{existing_id}", "PATCH",
                {"body": full_body})
        print(f"  Updated comment #{existing_id} on #{number}", flush=True)
    else:
        _gh_api(path, "POST", {"body": full_body})
        print(f"  Created comment on #{number}", flush=True)


def upsert_pr_comment(pr_number: int, body: str, marker: str) -> None:
    """Convenience alias — PRs and issues share the same comment API."""
    upsert_comment(pr_number, body, marker, on="pr")


def update_pr_body(pr_number: int, body: str) -> None:
    """Update the main PR description (not a comment) via gh pr edit."""
    import tempfile, subprocess as _sp
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md',
                                     delete=False, encoding='utf-8') as f:
        f.write(body)
        tmp = f.name
    try:
        _sp.run(["gh", "pr", "edit", str(pr_number), "--body-file", tmp],
                check=True, capture_output=True)
        print(f"  Updated PR #{pr_number} description", flush=True)
    except Exception as e:
        print(f"  ⚠ Could not update PR body: {e}", flush=True)
    finally:
        import os as _os; _os.unlink(tmp)


# ── Guidance loader ───────────────────────────────────────────────────────────

def load_field_guidance(kind: str) -> dict:
    """Return {field_name: guidance_markdown} from GEN_ISSUE_TEMPLATE JSON."""
    candidates = [Path.cwd()]
    ws = os.environ.get("GITHUB_WORKSPACE")
    if ws:
        candidates.append(Path(ws))
    cur = Path.cwd()
    for _ in range(8):
        if (cur / ".github").is_dir():
            candidates.append(cur)
            break
        cur = cur.parent

    for root in candidates:
        for name in [kind, kind + "s"]:
            p = root / ".github" / "GEN_ISSUE_TEMPLATE" / f"{name}.json"
            if p.exists():
                try:
                    return json.loads(p.read_text())["field_guidance"]
                except Exception:
                    pass
    return {}


# ── Validation helpers ────────────────────────────────────────────────────────

_SKIP_VALIDATION = {
    'horizontal_subgrid',
    'horizontal_computational_grid',
    'component_config',
}


def run_pycmipld_validation(data: dict, issue_type: str) -> tuple[bool, str | None]:
    if issue_type in _SKIP_VALIDATION:
        print(f"  ℹ Skipping esgvoc validation for '{issue_type}' (EMD-specific type)", flush=True)
        return True, None
    try:
        from cmipld.utils.esgvoc import pycmipld, DATA_DESCRIPTOR_CLASS_MAPPING
        cls = DATA_DESCRIPTOR_CLASS_MAPPING.get(issue_type)
        if cls is None:
            print(f"  ℹ No esgvoc schema for '{issue_type}' — skipping validation", flush=True)
            return True, None
        instance = pycmipld(cls, **data)
        return instance.data is not None, instance.validation_md
    except Exception as e:
        return False, f"Validation error: {e}"


def build_warning_comment(errors_md: str, failed_fields: list[str],
                           guidance: dict, issue_type: str) -> str:
    lines = [
        "## Submission validation failed\n",
        "The following errors were found. Please edit the issue to correct them. "
        "[How to edit an issue.](https://scribehow.com/embed-preview/Edit_an_Issues_Description_Field_on_GitHub__BFQ9OA50Q9-RbQvQ3r_GEQ?as=slides&size=flexible)\n",
        "> [!WARNING]",
        "> **Validation errors**\n",
    ]
    lines += [f"> {line}" for line in errors_md.strip().splitlines()]
    lines.append("")

    guidance_blocks = []
    for fname in sorted(set(failed_fields)):
        tip = guidance.get(fname, "")
        if tip:
            guidance_blocks.append(
                f"\n<details open><summary><strong>{fname}</strong></summary>\n\n"
                + tip.strip()
                + "\n\n</details>"
            )

    if guidance_blocks:
        lines.append("### Field guidance\n")
        lines.extend(guidance_blocks)

    return "\n".join(lines)


# ── Issue fetching ────────────────────────────────────────────────────────────

def get_issue_from_env():
    issue_number = os.environ.get('ISSUE_NUMBER')
    if issue_number:
        try:
            return get_issue_from_gh(issue_number)
        except Exception:
            pass
    return {
        'body':        os.environ.get('ISSUE_BODY'),
        'labels_full': os.environ.get('ISSUE_LABELS'),
        'number':      issue_number,
        'title':       os.environ.get('ISSUE_TITLE'),
        'author':      os.environ.get('ISSUE_SUBMITTER'),
        'created_at':  os.environ.get('ISSUE_CREATED_AT', ''),
    }


def get_issue_from_gh(issue_number):
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    cmd  = [
        'gh', 'issue', 'view', str(issue_number),
        '--json', 'title,body,author,labels,number,createdAt',
    ]
    if repo:
        cmd += ['--repo', repo]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data   = json.loads(result.stdout)
        labels = [l.get('name', '') for l in data.get('labels', [])]
        return {
            'body':        data.get('body', ''),
            'labels_full': json.dumps(labels),
            'number':      str(data.get('number', issue_number)),
            'title':       data.get('title', ''),
            'author':      data.get('author', {}).get('login', ''),
            'created_at':  data.get('createdAt', ''),
        }
    except subprocess.CalledProcessError as e:
        print(f"Error fetching issue {issue_number}: {e.stderr}")
        sys.exit(1)


def get_issue(issue_number=None):
    if issue_number:
        print(f"Fetching issue #{issue_number} …", flush=True)
        issue = get_issue_from_gh(issue_number)
        print(f"  ✓ {issue['title']}", flush=True)
        os.environ['ISSUE_BODY']      = issue['body'] or ''
        os.environ['ISSUE_LABELS']    = issue['labels_full'] or ''
        os.environ['ISSUE_NUMBER']    = issue['number'] or ''
        os.environ['ISSUE_TITLE']     = issue['title'] or ''
        os.environ['ISSUE_SUBMITTER'] = issue['author'] or ''
        return issue
    return get_issue_from_env()


def parse_issue_body(issue_body):
    if not issue_body:
        return {}
    lines      = issue_body.split('\n')
    issue_data = {}
    current_key = None
    for line in lines:
        if line.startswith('### '):
            current_key = line[4:].strip().replace(' ', '_').replace('-', '_').lower()
            issue_data[current_key] = ''
        elif current_key:
            issue_data[current_key] += line.strip() + ' '
    placeholder = {'not specified', '_no response_', 'none', ''}
    for key in issue_data:
        issue_data[key] = issue_data[key].strip()
        if issue_data[key].lower() in placeholder:
            issue_data[key] = ''
    return issue_data


def parse_labels(labels_str):
    if not labels_str:
        return []
    if isinstance(labels_str, str):
        try:
            labels = json.loads(labels_str)
        except json.JSONDecodeError:
            labels = [l.strip() for l in labels_str.split(',')]
    else:
        labels = labels_str
    return [l for l in labels if l.lower() not in {i.lower() for i in IGNORE_LABELS}]


def get_issue_type_from_labels(labels):
    relevant = parse_labels(labels)
    if not relevant:
        return None
    root = _repo_root()
    for label in relevant:
        abs_path = os.path.join(root, HANDLER_PATH, f"{label}.py")
        if os.path.exists(abs_path):
            print(f"  ✓ Found handler: {abs_path}", flush=True)
            return label
    print(f"  ℹ No specific handler for {relevant} in {root}", flush=True)
    return relevant[0]


def clean_id(value):
    if not value:
        return ''
    return value.lower().strip().replace(' ', '-').replace('_', '-')


def get_output_folder(issue_type):
    return os.path.join(DATA_PATH, FOLDER_MAPPING.get(issue_type, issue_type))


def build_type_array(labels, issue_type):
    types = [f"wcrp:{l}" for l in parse_labels(labels)]
    return types or [f"wcrp:{issue_type}"]


def build_data_from_issue(parsed_issue, issue_type, labels):
    validation_key = (parsed_issue.get('validation_key') or
                      parsed_issue.get('consortium_name') or
                      parsed_issue.get('acronym') or
                      parsed_issue.get('label') or '')
    data_id = clean_id(validation_key)
    if not data_id:
        return None, "No validation key or ID found"

    data = {
        "@context": "_context",
        "@id":      data_id,
        "@type":    build_type_array(labels, issue_type),
    }
    field_mapping = {
        'ui_label':    ['ui_label', 'full_name', 'full_name_of_the_organisation', 'long_label'],
        'description': ['description'],
        'url':         ['url', 'activity_webpage_/_citation', 'webpage', 'website'],
    }
    for data_field, issue_fields in field_mapping.items():
        for issue_field in issue_fields:
            value = parsed_issue.get(issue_field)
            if value and value.lower() not in {'_no response_', 'none', ''}:
                data[data_field] = value.strip()
                break
    ignore = {'issue_type', 'issue_kind', 'validation_key',
              'additional_collaborators', 'collaborators', 'consortium_name',
              'acronym', 'label', 'long_label', 'full_name_of_the_organisation'}
    for key, value in parsed_issue.items():
        if key.lower() not in ignore and key not in data:
            if isinstance(value, str):
                value = value.strip()
                if value and value.lower() not in {'_no response_', 'none', ''}:
                    data[key] = value
    return data, None


def parse_args():
    p = argparse.ArgumentParser(description='Process GitHub issues for CMIP-LD repositories')
    p.add_argument('-i', '--issue', type=int, metavar='NUMBER')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--validate-only', action='store_true',
                   help='Run validation and post warnings/success to the issue, '
                        'then exit. Do NOT write files or create a branch/PR. '
                        'Exit code 0 = passed, 1 = validation errors.')
    return p.parse_args()


def find_existing_pr_for_issue(issue_number: str) -> dict | None:
    """
    Search open PRs for one linked to this issue number.
    Matches on branch name containing the issue number, or PR body containing 'Resolves #<n>'.
    Returns the first matching PR dict, or None.
    """
    repo = _repo()
    if not repo:
        return None
    try:
        result = subprocess.run(
            ["gh", "pr", "list", "--repo", repo, "--state", "open",
             "--json", "number,url,headRefName,title,body"],
            capture_output=True, text=True, check=True,
        )
        prs = json.loads(result.stdout)
    except Exception as e:
        print(f"  ⚠ Could not list PRs: {e}", flush=True)
        return None

    issue_str = str(issue_number)
    patterns = [
        re.compile(rf'(?:^|_|-){re.escape(issue_str)}(?:_|-|$)'),
        re.compile(rf'Resolves\s+#{re.escape(issue_str)}\b', re.IGNORECASE),
    ]
    for pr in prs:
        branch = pr.get('headRefName', '')
        body   = pr.get('body', '') or ''
        if patterns[0].search(branch) or patterns[1].search(body):
            print(f"  ✓ Found existing PR #{pr['number']} for issue #{issue_number} "
                  f"(branch: {branch})", flush=True)
            return pr
    return None


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    from cmipld.utils import git
    from cmipld.utils.git import coauthors
    from cmipld.utils.id_generation import parse_commiters

    args          = parse_args()
    dry_run       = args.dry_run
    validate_only = args.validate_only
    prefix        = "[DRY RUN] " if dry_run else ("[VALIDATE] " if validate_only else "")

    issue        = get_issue(args.issue)
    parsed_issue = parse_issue_body(issue['body'])
    labels       = issue.get('labels_full') or os.environ.get('ISSUE_LABELS', '')
    issue_number = issue.get('number') or os.environ.get('ISSUE_NUMBER', '')
    issue_type   = get_issue_type_from_labels(labels)

    print(f"Issue #{issue_number}: {issue['title']}", flush=True)
    print(f"Author: {issue.get('author')}  |  Type: {issue_type}", flush=True)

    raw_labels = json.loads(labels) if isinstance(labels, str) else (labels or [])
    if not any('emd' in str(l).lower() for l in raw_labels):
        print("Issue has no emd-* label — not an EMD submission, skipping.", flush=True)
        sys.exit(0)

    if not issue_type:
        print("No matching issue type found — not an EMD submission, skipping.", flush=True)
        sys.exit(0)

    # ── Build files_to_write via handler / generic ─────────────────────
    script_path   = os.path.join(_repo_root(), HANDLER_PATH, f"{issue_type}.py")
    files_to_write: dict = {}

    if os.path.exists(script_path):
        spec = importlib.util.spec_from_file_location(issue_type, script_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, 'run'):
            result = mod.run(parsed_issue, issue, dry_run=(dry_run or validate_only))
            if isinstance(result, dict):
                files_to_write = result
            elif result is not None:
                files_to_write = {os.path.join(issue_type, f"{issue_type}.json"): result}

    if not files_to_write:
        data, err = build_data_from_issue(parsed_issue, issue_type, labels)
        if err or data is None:
            print(f"  ❌ {err}", flush=True)
            return
        data_id = data.get('@id', 'unknown')
        files_to_write = {os.path.join(issue_type, f"{data_id}.json"): data}

    guidance = load_field_guidance(issue_type)

    for file_path, data in files_to_write.items():
        if not file_path.startswith('_') and 'validation_key' not in data:
            _id = data.get('@id', '')
            if _id:
                data['validation_key'] = _id.split('/')[-1]

    # ── STEP 1: pycmipld validation ────────────────────────────────────
    print(f"\n{prefix}Running pycmipld validation …", flush=True)
    validation_errors: dict = {}
    for file_path, data in files_to_write.items():
        if file_path.startswith('_'):
            continue
        file_type = file_path.split(os.sep)[0] if os.sep in file_path else issue_type
        passed, errors_md = run_pycmipld_validation(data, file_type)
        if not passed and errors_md:
            validation_errors[file_path] = errors_md

    # ── STEP 2: handler update() for custom checks ─────────────────────
    script_path = os.path.join(_repo_root(), HANDLER_PATH, f"{issue_type}.py")
    if os.path.exists(script_path):
        spec = importlib.util.spec_from_file_location(issue_type, script_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, 'update'):
            mod.update(files_to_write, parsed_issue, issue,
                       dry_run=(dry_run or validate_only))

    # ── STEP 3: If validation failed → post warning, stop ─────────────
    if validation_errors:
        print(f"\n{prefix}Validation failed — posting warnings to issue #{issue_number}", flush=True)
        comment_body = ""
        for file_path, errors_md in validation_errors.items():
            failed_fields = []
            for line in errors_md.splitlines():
                if line.startswith('|') and '---' not in line and 'Field' not in line:
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if parts:
                        failed_fields.append(parts[0].strip('`').split('.')[0])
            comment_body = build_warning_comment(errors_md, failed_fields, guidance, issue_type)

        if not dry_run and issue_number:
            upsert_comment(int(issue_number), comment_body, _BOT_MARKER_ISSUE)
        else:
            print(comment_body, flush=True)
        sys.exit(1)

    print(f"\n{prefix}All validations passed.", flush=True)

    # ── STEP 4: switch to src-data before writing ────────────────────
    if not dry_run and not validate_only:
        from cmipld.utils.io import shell
        shell("git fetch origin src-data")
        shell("git checkout src-data")
        shell("git pull origin src-data")
        print("  ✓ Switched to src-data branch", flush=True)

    if validate_only:
        success_note = (
            "## Validation passed\n\n"
            "All checks passed. The write job will now create the branch and PR."
        )
        if issue_number:
            upsert_comment(int(issue_number), success_note, _BOT_MARKER_ISSUE)
        else:
            print(success_note, flush=True)
        print("\n[VALIDATE] All checks passed — exiting with code 0", flush=True)
        sys.exit(0)

    if dry_run:
        print(f"\n[DRY RUN] Would write: {list(files_to_write.keys())}")
        for file_path, data in files_to_write.items():
            if file_path.startswith('_'):
                continue
            report = data.get('_validation_report', '')
            if report:
                print(f"\n{'='*60}\n[DRY RUN] Review report for: {file_path}\n{'='*60}")
                print(report)
            else:
                print(f"\n[DRY RUN] No review report generated for: {file_path}")
        return

    # ── STEP 5: Write files ────────────────────────────────────────────
    issue_kind = parsed_issue.get('issue_kind', 'new').lower()
    if issue_kind not in ['new', 'modify']:
        issue_kind = 'new'

    all_output_paths = []
    processed_data   = {}

    for file_path, data in files_to_write.items():
        if file_path.startswith('_'):
            continue
        data.setdefault('@context', '_context')
        if '@id' not in data and 'id' in data:
            data['@id'] = data.pop('id')
        if '@type' not in data and 'type' in data:
            data['@type'] = data.pop('type')

        output_path = os.path.join(_repo_root(), DATA_PATH, file_path)

        force_modify_paths = files_to_write.get('_force_modify', set())
        if issue_kind == 'new' and os.path.exists(output_path) \
                and file_path not in force_modify_paths:
            msg = (
                "## File already exists\n\n"
                f"`{output_path}` already exists. Change **Issue Kind** to "
                "_Modify_ to update it, or close this issue if no changes are needed."
            )
            upsert_comment(int(issue_number), msg, _BOT_MARKER_ISSUE)
            return

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        _saved_report = data.get('_validation_report', '')
        _STRIP = {'issue_kind', 'issue_type', 'issue_category',
                  'additional_collaborators', 'collaborators'}
        clean_data = {k: v for k, v in data.items()
                      if not k.startswith('_') and k not in _STRIP}

        _saved_links = {k: v for k, v in clean_data.items()
                        if isinstance(v, list) and not k.startswith('@')}

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, indent=4, ensure_ascii=False)

        validator = JSONValidator(os.path.dirname(output_path), dry_run=False)
        validator.validate_and_fix_json(output_path)

        with open(output_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if _saved_links:
            for k, v in _saved_links.items():
                data[k] = v
                i = 0
                while True:
                    indexed = f"{k}.{i}"
                    if indexed in data:
                        del data[indexed]
                        i += 1
                    else:
                        break
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

        if 'validation_key' not in data and '@id' in data:
            data['validation_key'] = data['@id']
        data['_validation_report'] = _saved_report
        processed_data[file_path] = data
        all_output_paths.append(output_path)
        print(f"  ✓ Written: {output_path}", flush=True)

    # ── STEP 6: git — branch + commit + PR ────────────────────────────
    first_data     = list(processed_data.values())[0]
    issue_kind_cap = issue_kind.capitalize()

    all_ids = []
    for fp, d in processed_data.items():
        fid = d.get('validation_key') or d.get('@id', '')
        if fid and fid not in all_ids:
            all_ids.append(fid)
    validation_key = first_data.get('validation_key', first_data.get('@id', 'unknown'))
    ids_str        = ', '.join(all_ids) if all_ids else validation_key
    title          = f"{issue_kind_cap} {issue_type.capitalize()} : {ids_str}"
    data_id        = first_data.get('@id', 'unknown')

    # ── Check for an existing PR for this issue before creating a new branch ──
    existing_pr = find_existing_pr_for_issue(issue_number)
    if existing_pr:
        branch_name = existing_pr['headRefName']
        print(f"  ↩ Reusing existing branch: {branch_name}", flush=True)
    else:
        branch_name = re.sub(r'[^a-z0-9_-]', '_',
                             f"issue_{issue_number}_{issue_type}_{ids_str}".lower()).strip('_')
        branch_name = re.sub(r'_+', '_', branch_name)[:200]

    author_login  = issue.get('author') or os.environ.get('ISSUE_SUBMITTER', 'unknown')
    extra_collabs = parsed_issue.get('additional_collaborators',
                                     parsed_issue.get('collaborators', ''))
    commiters     = parse_commiters(author_login, extra_collabs)
    collab_str    = ', '.join(commiters[1:]) if len(commiters) > 1 else ''
    author_info   = coauthors.parse_issue_authors(author_login, collab_str)
    commit_msg    = coauthors.build_commit_message(
        f"{issue_kind_cap} {issue_type}: {data_id}",
        author_info['coauthor_lines'],
    )

    git.update_issue_title(title)
    git.newbranch(branch_name)
    for output_path in all_output_paths:
        git.commit_one(output_path, author_info['primary'],
                       comment=commit_msg, branch=branch_name)

    # ── STEP 7: Combine all validation reports ──────────────────────────
    report_parts = []
    for fp, d in processed_data.items():
        r = d.pop('_validation_report', '') or ''
        if r:
            report_parts.append(f"### `{fp}`\n\n{r}")
    report_md = '\n\n---\n\n'.join(report_parts)

    # ── STEP 8: Create / update PR ─────────────────────────────────────
    # Build a combined JSON block covering all written files, not just the first.
    if len(processed_data) == 1:
        data_json = json.dumps(
            {k: v for k, v in first_data.items() if not k.startswith('_')},
            indent=4, ensure_ascii=False,
        )
    else:
        combined = {
            fp: {k: v for k, v in d.items() if not k.startswith('_')}
            for fp, d in processed_data.items()
        }
        data_json = json.dumps(combined, indent=4, ensure_ascii=False)

    print("Creating / updating pull request …", flush=True)
    _saved_issue_num = os.environ.pop('ISSUE_NUMBER', '')
    try:
        git.newpull(
            branch_name,
            author_login,
            data_json,
            title,
            issue_number,
            base_branch='src-data',
        )
    finally:
        if _saved_issue_num:
            os.environ['ISSUE_NUMBER'] = _saved_issue_num

    pr_number = None
    pr_url    = ""
    try:
        prs = git.branch_pull_requests(head=branch_name)
        if prs:
            try:
                subprocess.run(
                    ["gh", "issue", "edit", str(issue_number),
                     "--add-label", "pull_req",
                     "--add-label", "needs-review",
                     "--repo", _repo()],
                    check=True, capture_output=True,
                )
                print(f"  ✓ Added labels: pull_req, needs-review to issue #{issue_number}", flush=True)
            except Exception as e:
                print(f"  ⚠ Could not add labels: {e}", flush=True)
            pr_number = prs[0]['number']
            pr_url    = prs[0].get('url', '')

            try:
                import subprocess as _sp
                _sp.run(
                    ["gh", "pr", "edit", str(pr_number), "--title", title],
                    check=True, capture_output=True,
                )
                print(f"  ✓ Updated PR #{pr_number} title: {title}", flush=True)
            except Exception as e:
                print(f"  ⚠ Could not update PR title: {e}", flush=True)

            import datetime as _dt
            pr_ts   = _dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

            # Build submitter / collaborators footer
            submitter_line = f"**Submitter:** @{author_login}"
            if collab_str:
                collab_handles = ' '.join(f'@{c.strip()}' for c in collab_str.split(',') if c.strip())
                collab_line = f"**Additional collaborators:** {collab_handles}"
            else:
                collab_line = None

            people_section = submitter_line
            if collab_line:
                people_section += f"\n{collab_line}"

            # For multi-file submissions, show each file as its own fenced block
            # so reviewers can see every artefact without reading the diff.
            if len(processed_data) > 1:
                file_blocks = []
                for fp, d in processed_data.items():
                    clean = {k: v for k, v in d.items() if not k.startswith('_')}
                    file_blocks.append(
                        f"**`{fp}`**\n```json\n{json.dumps(clean, indent=4, ensure_ascii=False)}\n```"
                    )
                submitted_section = "### Submitted data\n\n" + "\n\n".join(file_blocks)
            else:
                submitted_section = f"### Submitted data\n\n```json\n{data_json}\n```"

            pr_desc = (
                f"Resolves #{issue_number}\n\n"
                f"> View submitted files in the **Files changed** tab above.\n\n"
                f"{submitted_section}\n\n"
                f"---\n\n"
                f"A full review report is posted as a comment below.  \n"
                f"_Last updated: {pr_ts}_\n\n"
                f"---\n\n"
                f"{people_section}"
            )
            update_pr_body(pr_number, pr_desc)
            upsert_pr_comment(pr_number, report_md, _BOT_MARKER_PR)
    except Exception as e:
        print(f"  ⚠ Could not update PR: {e}", flush=True)

    pr_ref = f"[PR #{pr_number}]({pr_url})" if pr_url else f"branch `{branch_name}`"

    auto_fields = []
    try:
        from cmipld.utils.similarity.report_builder import _validator_covered_fields
        from cmipld.utils.esgvoc import DATA_DESCRIPTOR_CLASS_MAPPING
        auto_fields = sorted(_validator_covered_fields(
            DATA_DESCRIPTOR_CLASS_MAPPING.get(issue_type)))
    except Exception:
        pass
    field_list = ", ".join(f"`{f}`" for f in auto_fields) if auto_fields else "all submitted fields"

    success_lines = [
        "## Automatic checks passed\n",
        f"Automatic checks ({field_list}) all passed. "
        f"{pr_ref} created for review.\n",
    ]

    upsert_comment(int(issue_number), "\n".join(success_lines), _BOT_MARKER_ISSUE)

    print(f"\n✅ Done: {title}", flush=True)


if __name__ == '__main__':
    main()
