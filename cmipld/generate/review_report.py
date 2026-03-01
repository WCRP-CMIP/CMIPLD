#!/usr/bin/env python3
"""
review_report — generate a Markdown review report for a submitted EMD issue.

Fetches the issue from GitHub, parses its body, determines the entity type
from labels, builds the submitted JSON-LD data, then runs the full
ReportBuilder pipeline (field status table, validation errors, link
similarity mermaid, content similarity) and writes the result to a file.

Usage
-----
    # From the repo root (needs gh CLI authenticated):
    python -m cmipld.generate.review_report --issue 42

    # Write to a specific file:
    python -m cmipld.generate.review_report -i 42 -o my_report.md

    # Print to stdout instead of a file:
    python -m cmipld.generate.review_report -i 42 --stdout

    # Skip transformer embeddings (faster, offline):
    python -m cmipld.generate.review_report -i 42 --no-embed

Entry point (after pip install):
    review_report -i 42
"""

import argparse
import json
import sys
from pathlib import Path


# ── reuse helpers from new_issue ─────────────────────────────────────────────

def _import_new_issue():
    try:
        from cmipld.generate import new_issue as ni
        return ni
    except ImportError as e:
        print(f"Error: cannot import cmipld.generate.new_issue — {e}", file=sys.stderr)
        sys.exit(1)


def _folder_url_for_kind(kind: str) -> str:
    """
    Map an issue-script kind (label slug) to an emd: folder URL.
    Mirrors the convention used in generate_grid_cells.py etc.
    """
    mapping = {
        "horizontal_grid_cell":         "emd:horizontal_grid_cells",
        "horizontal_grid_cells":        "emd:horizontal_grid_cells",
        "horizontal_computational_grid": "emd:horizontal_computational_grid",
        "vertical_computational_grid":  "emd:vertical_computational_grid",
        "model_component":              "emd:model_component",
        "model_family":                 "emd:model_family",
        "model":                        "emd:model",
    }
    return mapping.get(kind, f"emd:{kind}s")


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        prog="review_report",
        description="Generate a Markdown review report for a submitted EMD GitHub issue.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  review_report -i 42                   # write to issue_42_report.md
  review_report -i 42 -o report.md      # custom output file
  review_report -i 42 --stdout          # print to terminal
  review_report -i 42 --no-embed        # skip transformer embeddings (faster)
  review_report -i 42 --threshold 60    # flag link overlaps ≥60% (default 80)
""",
    )
    p.add_argument("-i", "--issue", type=int, required=True, metavar="NUMBER",
                   help="GitHub issue number to generate the report for")
    p.add_argument("-o", "--output", metavar="FILE",
                   help="Output file path (default: issue_<N>_report.md)")
    p.add_argument("--stdout", action="store_true",
                   help="Print report to stdout instead of writing a file")
    p.add_argument("--no-embed", action="store_true",
                   help="Skip sentence-transformer embeddings (faster, works offline)")
    p.add_argument("--threshold", type=float, default=80.0, metavar="PCT",
                   help="Link-overlap %% threshold for flagging similar items (default: 80)")
    p.add_argument("--repo", metavar="OWNER/REPO",
                   help="GitHub repository (default: auto-detected from git remote)")
    return p.parse_args()


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    ni   = _import_new_issue()

    # 1. Fetch issue from GitHub
    print(f"Fetching issue #{args.issue} …", flush=True)
    issue = ni.get_issue_from_gh(args.issue)
    print(f"  Title  : {issue['title']}", flush=True)
    print(f"  Author : {issue['author']}", flush=True)

    # 2. Parse body
    parsed = ni.parse_issue_body(issue["body"])

    # 3. Determine type from labels
    labels_raw = issue.get("labels_full", "[]")
    kind = ni.get_issue_type_from_labels(labels_raw)
    print(f"  Kind   : {kind}", flush=True)

    # 4. Build initial JSON-LD data (same as new_issue does before writing)
    data, err = ni.build_data_from_issue(parsed, kind, labels_raw)
    if err or data is None:
        # Fall back: build directly from parsed fields
        print(f"  ⚠ build_data_from_issue: {err} — building from parsed fields", flush=True)
        # Try to derive a validation_key from the issue title
        # "[EMD] Kind: <name>" → "<name>" lowercased, spaces → hyphens
        vk = ""
        title = issue.get("title", "")
        if ":" in title:
            vk = title.split(":", 1)[-1].strip().lower().replace(" ", "-")
        data = {
            "@context": "_context",
            "@id": vk or f"submitted_{args.issue}",
            "@type": [f"wcrp:{kind}", f"esgvoc:{kind.title().replace('_','')}"],
            **({"validation_key": vk} if vk else {}),
            **{k: v for k, v in parsed.items()
               if v and v.lower() not in {"none", "_no response_"}},
        }
    print(f"  Fields : {len([k for k in data if isinstance(k, str) and not k.startswith('@')])}", flush=True)

    # 5. Run handler's run() to add any custom fields (e.g. component_config_id)
    try:
        import importlib.util, os
        handler_path = os.path.join(".github", "ISSUE_SCRIPT", f"{kind}.py")
        if Path(handler_path).exists():
            spec   = importlib.util.spec_from_file_location(kind, handler_path)
            mod    = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.run(parsed, issue, dry_run=True)
            if isinstance(result, dict):
                # Merge non-meta fields into data
                for k, v in result.items():
                    if not k.startswith("_"):
                        data.update(v) if isinstance(v, dict) else None
    except Exception as e:
        print(f"  ⚠ handler run() skipped: {e}", flush=True)

    # 6. Run ReportBuilder
    folder_url = _folder_url_for_kind(kind)
    print(f"  Folder : {folder_url}", flush=True)
    print("Building report …", flush=True)

    try:
        from cmipld.utils.similarity import ReportBuilder
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    report = ReportBuilder(
        folder_url     = folder_url,
        kind           = kind,
        item           = data,
        use_embeddings = not args.no_embed,
        link_threshold = args.threshold,
    ).build()

    # 7. Output
    if args.stdout:
        print(report)
    else:
        out = Path(args.output) if args.output else Path(f"issue_{args.issue}_report.md")
        out.write_text(report, encoding="utf-8")
        print(f"Report written → {out}")


if __name__ == "__main__":
    main()
