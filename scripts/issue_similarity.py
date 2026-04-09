#!/usr/bin/env python3
"""
Compare a src-data JSON file against all GitHub issues (open + closed)
to find which issue it came from, and flag duplicate/similar issues.

Usage:
    python issue_similarity.py <path/to/file.json> [--repo OWNER/REPO] [--threshold 70]
    python issue_similarity.py --all <src-data-dir>  [--repo OWNER/REPO]
    python issue_similarity.py --duplicates          [--repo OWNER/REPO]
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


# ── GitHub ────────────────────────────────────────────────────────────────────

def get_issues(repo: str) -> list[dict]:
    print(f"  Fetching issues from {repo}...", flush=True)
    result = subprocess.run(
        ["gh", "issue", "list", "--repo", repo, "--state", "all",
         "--limit", "500", "--json", "number,title,body,labels,state,closedAt"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def parse_issue_fields(body: str) -> dict:
    """Extract ### field values from a GitHub issue body."""
    if not body:
        return {}
    fields = {}
    current_key = None
    for line in body.split("\n"):
        if line.startswith("### "):
            current_key = line[4:].strip().lower().replace(" ", "_").replace("-", "_")
            fields[current_key] = ""
        elif current_key:
            fields[current_key] += line.strip() + " "
    placeholder = {"_no response_", "none", "not specified", ""}
    return {k: v.strip() for k, v in fields.items()
            if v.strip().lower() not in placeholder}


def issue_to_text(issue: dict) -> str:
    parts = [issue.get("title", "")]
    for v in parse_issue_fields(issue.get("body", "")).values():
        parts.append(v)
    return " ".join(parts).lower()


# ── File ──────────────────────────────────────────────────────────────────────

def file_to_text(data: dict) -> str:
    skip = {"@context", "@id", "@type", "validation_key"}
    parts = []
    for k, v in data.items():
        if k in skip:
            continue
        if isinstance(v, (str, int, float)) and v not in (None, ""):
            parts.append(str(v))
        elif isinstance(v, list):
            parts.extend(str(x) for x in v if x is not None)
    return " ".join(parts).lower()


# ── Similarity ────────────────────────────────────────────────────────────────

def jaccard(a: str, b: str) -> float:
    ta = set(re.findall(r"[\w.+-]+", a))
    tb = set(re.findall(r"[\w.+-]+", b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


_NUMERIC = re.compile(r"_(resolution|number|longitude|latitude|cells|truncation)")

def numeric_bonus(data: dict, issue_fields: dict) -> float:
    """Bonus 0-0.3 when numeric fields match exactly."""
    matches = total = 0
    for k, v in data.items():
        if not _NUMERIC.search(k):
            continue
        total += 1
        for fk, fv in issue_fields.items():
            if any(p in fk for p in k.split("_") if len(p) > 2):
                try:
                    if abs(float(str(v)) - float(str(fv))) < 0.001:
                        matches += 1
                        break
                except (ValueError, TypeError):
                    if str(v).strip().lower() == str(fv).strip().lower():
                        matches += 1
                        break
    return (matches / total) * 0.3 if total else 0.0


# ── Core ──────────────────────────────────────────────────────────────────────

def compare_file_to_issues(data: dict, issues: list[dict], threshold: float) -> list[dict]:
    file_text = file_to_text(data)
    results = []
    for issue in issues:
        issue_fields = parse_issue_fields(issue.get("body", ""))
        score = min(1.0, jaccard(file_text, issue_to_text(issue))
                    + numeric_bonus(data, issue_fields))
        if score >= threshold:
            results.append({
                "issue": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "score": round(score * 100, 1),
                "labels": [l["name"] for l in issue.get("labels", [])],
            })
    return sorted(results, key=lambda x: x["score"], reverse=True)


def find_duplicate_issues(issues: list[dict], threshold: float = 0.6) -> list[dict]:
    texts = [(i, issue_to_text(i)) for i in issues]
    pairs = []
    for idx, (ia, ta) in enumerate(texts):
        for ib, tb in texts[idx + 1:]:
            score = jaccard(ta, tb)
            if score >= threshold:
                pairs.append({
                    "a": ia["number"], "title_a": ia["title"], "state_a": ia["state"],
                    "b": ib["number"], "title_b": ib["title"], "state_b": ib["state"],
                    "score": round(score * 100, 1),
                })
    return sorted(pairs, key=lambda x: x["score"], reverse=True)


# ── Display ───────────────────────────────────────────────────────────────────

def icon(state): return "✅" if state == "closed" else "🔵"


def print_file_matches(filepath: str, matches: list[dict]):
    print(f"\n{'='*60}\n  File: {filepath}\n{'='*60}")
    if not matches:
        print("  No matching issues found above threshold.")
        return
    print(f"  {'#':<6} {'Score':<8} {'St':<3} Title")
    print(f"  {'-'*55}")
    for m in matches:
        print(f"  #{m['issue']:<5} {m['score']:>5.1f}%  {icon(m['state'])}  {m['title'][:60]}")


def print_duplicate_issues(pairs: list[dict]):
    if not pairs:
        print("\n  No duplicate issues found.")
        return
    print(f"\n{'='*60}\n  ⚠️  Potentially duplicate issues\n{'='*60}")
    for p in pairs:
        print(f"  {icon(p['state_a'])}#{p['a']:<5} ↔ {icon(p['state_b'])}#{p['b']:<5}  "
              f"{p['score']:>5.1f}%  {p['title_a'][:35]} / {p['title_b'][:35]}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def get_repo() -> str:
    try:
        r = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
            capture_output=True, text=True, check=True,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser(description="Compare src-data files to GitHub issues")
    parser.add_argument("file", nargs="?", help="JSON file to compare")
    parser.add_argument("--all", metavar="DIR", help="Compare all JSON files in a directory")
    parser.add_argument("--duplicates", action="store_true",
                        help="Check issues against each other for duplicates")
    parser.add_argument("--repo", help="GitHub repo owner/repo (defaults to current)")
    parser.add_argument("--threshold", type=float, default=25.0,
                        help="Minimum similarity %% to show (default: 25)")
    args = parser.parse_args()

    if not args.file and not args.all and not args.duplicates:
        parser.print_help()
        sys.exit(1)

    repo = args.repo or get_repo()
    if not repo:
        print("ERROR: Could not determine repo. Pass --repo OWNER/REPO")
        sys.exit(1)

    issues = get_issues(repo)
    print(f"  Loaded {len(issues)} issues "
          f"({sum(1 for i in issues if i['state']=='open')} open, "
          f"{sum(1 for i in issues if i['state']=='closed')} closed)")

    if args.duplicates:
        pairs = find_duplicate_issues(issues, threshold=0.6)
        print_duplicate_issues(pairs)

    threshold = args.threshold / 100.0

    files = []
    if args.file:
        files = [Path(args.file)]
    elif args.all:
        files = sorted(f for f in Path(args.all).rglob("*.json")
                       if not f.name.startswith("_"))

    for fpath in files:
        try:
            data = json.loads(fpath.read_text())
        except Exception as e:
            print(f"  SKIP {fpath}: {e}")
            continue
        matches = compare_file_to_issues(data, issues, threshold)
        print_file_matches(str(fpath), matches)


if __name__ == "__main__":
    main()
