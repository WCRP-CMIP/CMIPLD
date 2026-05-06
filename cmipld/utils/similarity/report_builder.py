"""
ReportBuilder — structured Markdown review report for a submitted JSON-LD item.

Sections
--------
1. Field checklist  — GitHub checkboxes. Green tick only on fields covered by
                      an explicit pydantic validator function (field_validator
                      or model_validator, extracted from source). Red cross on
                      explicit failures. Unticked = not submitted.
2. Validation errors — pydantic error table in a [!WARNING] admonition.
3. Link similarity  — folder graph fetched via cmipld.expand (depth=4).
                      Submitted plain values mapped to canonical URIs via the
                      folder's own items. Mermaid with click hyperlinks.
                      Similarity table links to the actual files.
4. Text similarity  — on all fields that are NOT: @-keys, drs/validation,
                      link-carrying, or explicitly validator-covered.
"""

from __future__ import annotations

import datetime
import inspect
import re
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set

from .graph_loader       import GraphLoader, _short_id
from .link_analyzer      import LinkAnalyzer
from .pydantic_validator import PydanticValidator, short, is_default_skip
from .text_similarity    import TextSimilarityAnalyzer, strip_text_fields

# Fields whose values are short IDs (not full HTTP URIs) that should be
# resolved to canonical links in the report. Covers both in-repo folders
# and external CVs where the base URL is known.
# Maps field_stem -> base URI; canonical URI = base + "/" + value
SHORT_ID_LINK_FIELDS: Dict[str, str] = {
    "horizontal_subgrids":   "https://emd.mipcvs.dev/horizontal_subgrid",
    "horizontal_grid_cells": "https://emd.mipcvs.dev/horizontal_grid_cell",
    "horizontal_grid_cell":  "https://emd.mipcvs.dev/horizontal_grid_cell",  # context spelling
    "cell_variable_type":    "https://constants.mipcvs.dev/cell_variable_type",
}

# Keep old name as alias so existing references don't break
INREPO_LINK_FIELDS = SHORT_ID_LINK_FIELDS

REPORT_SKIP_EXACT = frozenset({
    "id", "type", "drs_name",
    "issue_kind", "issue_type", "issue_category",
    "ui_label", "validation_key",
    "alias",
})

_DIFF_IGNORE = frozenset({"@id", "@type", "@context", "validation_key", "ui_label","alias"})

_TYPE_RE = re.compile(
    r"(wcrp:|esgvoc:)|/docs/contents/|/(universal|constants|emd)$"
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def _write_step_summary(report: str) -> None:
    """
    Append the markdown report to the GitHub Actions step summary file
    ($GITHUB_STEP_SUMMARY). No-ops silently outside of Actions.
    """
    import os
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    try:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(report)
            f.write("\n")
    except Exception:
        pass


def _is_report_skip(key: str) -> bool:
    if is_default_skip(key):
        return True
    return short(key) in REPORT_SKIP_EXACT


def _compact_val(v: Any, max_len: int = 80) -> str:
    if isinstance(v, dict):
        raw = v.get("@id", "").split("/")[-1] or v.get("@value", v)
        s = str(raw)
    elif isinstance(v, list):
        s = ", ".join(_compact_val(e, 40) for e in v)
    else:
        s = str(v)
    return (s[:max_len] + "…") if len(s) > max_len else s


def _table_cell(v: Any, max_len: int = 60) -> str:
    """Compact value safe for use inside a markdown table cell."""
    s = _compact_val(v, max_len)
    # Escape pipe characters and collapse newlines so the cell stays on one row
    s = s.replace("|", "\\|").replace("\n", " ").replace("\r", "")
    return s


def _is_data_link(uri: str) -> bool:
    if _TYPE_RE.search(uri):
        return False
    parts = [p for p in uri.replace("https://", "").split("/") if p]
    return len(parts) >= 3


def _safe_node(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", s)


def _item_url(item_id: str) -> str:
    """
    Build a hyperlink URL for a folder item.
    If the id contains 'mipcvs.dev', append '.json'.
    Otherwise use the id as-is.
    """
    if not item_id:
        return ""
    # item_id may be a short stem like 'g100' or a full URL
    if item_id.startswith("http"):
        url = item_id
        if "mipcvs.dev" in url and not url.endswith(".json"):
            url = url + ".json"
        return url
    return ""


def _normalise_for_diff(item: dict) -> dict:
    """
    Flatten an item to short keys and resolve @id / @value wrappers.
    Handles expanded JSON-LD (full URI keys) and plain short-key dicts.
    """
    out: Dict[str, Any] = {}
    for k, v in item.items():
        if k in _DIFF_IGNORE:
            continue
        sk = short(k)
        if sk in _DIFF_IGNORE:
            continue
        # Resolve @id / @value wrappers produced by JSON-LD expansion
        if isinstance(v, dict):
            if "@id" in v:
                v = v["@id"].split("/")[-1]   # stem of the URI
            elif "@value" in v:
                v = v["@value"]
        elif isinstance(v, list):
            resolved = []
            for elem in v:
                if isinstance(elem, dict) and "@id" in elem:
                    resolved.append(elem["@id"].split("/")[-1])
                elif isinstance(elem, dict) and "@value" in elem:
                    resolved.append(elem["@value"])
                else:
                    resolved.append(elem)
            # Sort lists so comparison is order-independent (e.g. variable
            # type lists submitted in different order still compare equal)
            resolved = sorted(str(x) for x in resolved)
            v = resolved if len(resolved) != 1 else resolved[0]
        # Last-write-wins if both a short and long key map to the same stem
        out[sk] = v
    return out


def _text_diff(submitted_text_fields: dict, existing: dict, text_field_keys: set,
               exclude_set: Optional[Set[str]] = None) -> str:
    """
    Diff on text fields — table format.
    When all fields match, shows identical message plus the full table.
    """
    s = {short(k): v for k, v in submitted_text_fields.items()}

    if exclude_set:
        e_stripped = strip_text_fields(existing, exclude=exclude_set)
    else:
        e_stripped = existing
    e = _normalise_for_diff(e_stripped)

    _blank = (None, "", [], {})
    diff_rows = []
    all_rows  = []

    for k in sorted(set(s) | set(e)):
        s_val = s.get(k)
        e_val = e.get(k)
        if s_val in _blank and e_val in _blank:
            continue
        s_str = _table_cell(s_val) if s_val not in _blank else "_null_"
        e_str = _table_cell(e_val) if e_val not in _blank else "_null_"
        all_rows.append(f"| `{k}` | {e_str} | {s_str} |")
        if s_val != e_val:
            diff_rows.append(f"| `{k}` | {e_str} | {s_str} |")

    header = "| Field | Existing | Submitted |\n|-------|----------|-----------|\n"

    if not all_rows:
        return "_No comparable text fields found._"

    if not diff_rows:
        return (
            "_Compared text fields are identical — this is likely a duplicate._\n\n"
            + header
            + "\n".join(all_rows)
        )

    return header + "\n".join(diff_rows)


def _link_diff(submitted: dict, existing: dict, link_field_names: Set[str]) -> str:
    """
    Diff restricted to only the CV-linked fields — table format.
    """
    s = _normalise_for_diff(submitted)
    e = _normalise_for_diff(existing)

    all_link_keys = {k for k in (set(s) | set(e)) if k in link_field_names or short(k) in link_field_names}

    _blank = (None, "", [], {})
    rows = []
    for k in sorted(all_link_keys):
        s_val = s.get(k)
        e_val = e.get(k)
        if s_val in _blank and e_val in _blank:
            continue
        s_str = _table_cell(s_val) if s_val not in _blank else "_null_"
        e_str = _table_cell(e_val) if e_val not in _blank else "_null_"
        rows.append(f"| `{k}` | {e_str} | {s_str} |")

    if not rows:
        return "_No CV link fields found in either item._"

    return (
        "| Field | Existing | Submitted |\n"
        "|-------|----------|-----------|\n"
        + "\n".join(rows)
    )


def _diff_table(submitted: dict, existing: dict) -> str:
    """
    Build a Markdown diff table on ALL fields (no wrapper — caller handles details block).
    Normalises both dicts to short keys and resolves @id/@value wrappers.
    """
    s = _normalise_for_diff(submitted)
    e = _normalise_for_diff(existing)

    rows = []
    for k in sorted(set(s) | set(e)):
        s_val = s.get(k)
        e_val = e.get(k)
        if s_val == e_val:
            continue
        s_str = _table_cell(s_val) if s_val not in (None, "", [], {}) else "_null_"
        e_str = _table_cell(e_val) if e_val not in (None, "", [], {}) else "_null_"
        rows.append(f"| `{k}` | {e_str} | {s_str} |")

    if not rows:
        return "_No field differences found._"

    return (
        "| Field | Existing | Submitted |\n"
        "|-------|----------|-----------|\n"
        + "\n".join(rows)
    )


# ── validator coverage — source-file approach (like create_readme.py) ─────────

def _validator_covered_fields(cls) -> FrozenSet[str]:
    """
    Extract the field names covered by explicit pydantic validator functions
    by reading the model's source file (mirrors create_readme.extract_validators).

    - @field_validator('field1', 'field2') → covers those fields
    - @model_validator: parse self.fieldname patterns from function body

    Returns frozenset of model field names that have a dedicated check.
    """
    if cls is None:
        return frozenset()

    covered: set = set()
    try:
        source_file = inspect.getfile(cls)
        with open(source_file, "r", encoding="utf-8") as f:
            lines = f.read().split("\n")
    except Exception:
        return frozenset()

    i = 0
    while i < len(lines):
        line = lines[i]

        if "@field_validator" in line:
            # Extract quoted field names from the decorator line
            fields = re.findall(r"[\"']([^\"']+)[\"']", line)
            fields = [f for f in fields if f not in ("before", "after", "mode", "wrap")]
            covered.update(fields)

        elif "@model_validator" in line:
            # Find the def line
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith("def "):
                j += 1
            if j < len(lines):
                # Collect function body
                base_indent = len(lines[j]) - len(lines[j].lstrip())
                func_lines = [lines[j]]
                k = j + 1
                while k < len(lines):
                    curr = lines[k]
                    if curr.strip() == "":
                        func_lines.append(curr)
                        k += 1
                        continue
                    curr_indent = len(curr) - len(curr.lstrip())
                    if curr_indent <= base_indent and (
                        curr.strip().startswith("def ") or curr.strip().startswith("@")
                    ):
                        break
                    func_lines.append(curr)
                    k += 1
                src = "\n".join(func_lines)
                # self.fieldname
                covered.update(re.findall(r"self\.([a-z_][a-z0-9_]*)", src))
                i = k
                continue
        i += 1

    return frozenset(f for f in covered if f not in REPORT_SKIP_EXACT)


# ── link construction for unregistered items ──────────────────────────────────

def _infer_cv_graphs_from_folder(folder_items: List[dict]) -> Dict[str, str]:
    """
    Infer CV graph URLs by inspecting the @id URIs in existing folder items.

    When an existing item has:
        {"grid_type": {"@id": "https://.../WCRP-constants/grid_type/regular-latitude-longitude"}}

    We infer that the graph for grid_type lives at:
        "https://.../WCRP-constants/grid_type/_graph.json"

    Keys are compressed to their short form (e.g. the full URI
    https://emd.mipcvs.dev/docs/contents/HorizontalGridCell/grid_type
    becomes just "grid_type") so they match the plain keys in submitted items.
    """
    field_graphs: Dict[str, str] = {}
    for fi in folder_items:
        for key, val in fi.items():
            compressed = short(key)   # e.g. full URI → "grid_type"
            if compressed.startswith("@") or compressed in field_graphs:
                continue
            uri = None
            if isinstance(val, dict) and "@id" in val:
                uri = val["@id"]
            elif isinstance(val, list):
                for elem in val:
                    if isinstance(elem, dict) and "@id" in elem:
                        uri = elem["@id"]
                        break
            if uri and _is_data_link(uri):
                graph_url = uri.rsplit("/", 1)[0] + "/_graph.json"
                field_graphs[compressed] = graph_url
    return field_graphs


def _fetch_cv_graph(graph_url: str) -> Dict[str, str]:
    """
    Fetch a single CV graph and return a lookup of value variants → canonical URI.

    Uses _find_contents_key to handle fully-expanded JSON-LD where "contents"
    may have become a full URI key. Falls back to building URIs from the graph
    base URL + validation_key when @id is missing or in prefixed form.
    """
    try:
        import cmipld
        from .graph_loader import _find_contents_key

        with cmipld.ensure_remote():
            data = cmipld.expand(graph_url, depth=2)

        base_url     = graph_url.replace("/_graph.json", "")
        contents_key = _find_contents_key(data)
        entries      = data.get(contents_key, []) if contents_key else []

        lookup: Dict[str, str] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue

            raw_id = entry.get("@id", "")
            vk     = entry.get("validation_key", "")

            if raw_id and isinstance(raw_id, str) and not raw_id.startswith("_"):
                if raw_id.startswith("http"):
                    uri = raw_id
                else:
                    stem = raw_id.split("/")[-1].split(":")[-1]
                    uri  = f"{base_url}/{stem}"
            elif vk:
                uri = f"{base_url}/{vk}"
            else:
                continue

            stem = uri.split("/")[-1]
            for variant in [stem, stem.replace("-", "_"), stem.replace("_", "-")]:
                lookup[variant] = uri

            for field in ("validation_key", "ui_label"):
                val = entry.get(field, "")
                if val and isinstance(val, str):
                    lookup[val]         = uri
                    lookup[val.lower()] = uri

        return lookup
    except Exception:
        return {}


def _fetch_inrepo_item(uri: str) -> dict:
    """
    Fetch a single in-repo EMD item by its canonical URI.
    Returns the JSON dict, or {} on any failure.
    """
    try:
        import urllib.request as _req
        import json as _json
        url = uri.rstrip('/') + '.json'
        with _req.urlopen(url, timeout=5) as r:
            return _json.loads(r.read().decode())
    except Exception:
        return {}


def _build_links_from_folder(
    item: dict,
    folder_items: List[dict],
) -> Dict[str, str]:
    """
    For a submitted item with plain string values, resolve canonical URIs by:
      1. Resolving known in-repo short-ID fields directly from INREPO_LINK_FIELDS
      2. Inferring which fields are CV fields from the existing folder items
      3. Fetching those CV graphs directly to get all valid values
      4. Falling back to the existing folder items for any values not in the graph

    Returns {field_stem: canonical_uri}.
    """
    # ── 0. Resolve known in-repo linked fields ──────────────────────────────
    # These fields contain short IDs like "g114-mass" that reference other
    # EMD folders, not external CVs, so _infer_cv_graphs_from_folder never
    # picks them up. Build the canonical URI directly from the base URL.
    field_links_inrepo: Dict[str, str] = {}
    for key, val in item.items():
        field_stem = short(key)
        base = INREPO_LINK_FIELDS.get(field_stem)
        if base is None:
            continue
        candidates = val if isinstance(val, list) else [val]
        for candidate in candidates:
            # candidate may be a plain string (raw submission) or a full dict
            # (after validate_data substitution in horizontal_computational_grid update())
            if isinstance(candidate, str) and candidate:
                sid = candidate.strip().lower()
            elif isinstance(candidate, dict):
                raw = candidate.get("@id") or candidate.get("validation_key") or ""
                sid = raw.split("/")[-1].strip().lower()
            else:
                continue
            if sid:
                field_links_inrepo[field_stem] = f"{base.rstrip('/')}/{sid}"

    # ── 1. Infer CV graph URLs from existing folder items ───────────────────
    field_graphs = _infer_cv_graphs_from_folder(folder_items)

    # ── 2. Fetch each CV graph and build per-field lookup ───────────────────
    _graph_cache: Dict[str, Dict[str, str]] = {}
    for field, graph_url in field_graphs.items():
        if graph_url not in _graph_cache:
            _graph_cache[graph_url] = _fetch_cv_graph(graph_url)

    # ── 3. Build fallback lookup from existing folder items ─────────────────
    value_to_uri: Dict[str, str] = {}
    for fi in folder_items:
        for key, val in fi.items():
            if key.startswith("@"):
                continue
            
            # dict
            if isinstance(val, dict) and "@id" in val:
                uri = val["@id"]
                if _is_data_link(uri):
                    stem = uri.split("/")[-1]
                    for variant in [stem, stem.replace("-", "_"), stem.replace("_", "-")]:
                        value_to_uri[variant] = uri
            # list 
            elif isinstance(val, list):
                for elem in val:
                    if isinstance(elem, dict) and "@id" in elem:
                        uri = elem["@id"]
                        if _is_data_link(uri):
                            stem = uri.split("/")[-1]
                            for variant in [stem, stem.replace("-", "_"), stem.replace("_", "-")]:
                                value_to_uri[variant] = uri

    # ── 4. Match submitted values against the combined lookup ────────────────
    field_links: Dict[str, str] = {}
    for key, val in item.items():
        if _is_report_skip(key):
            continue
        candidates = [val] if not isinstance(val, list) else val
        field_cv = _graph_cache.get(field_graphs.get(key, ""), {})

        for candidate in candidates:
            if not isinstance(candidate, str) or not candidate:
                continue
            probes = [
                candidate.strip(),
                candidate.lower().strip(),
                candidate.replace("_", "-"),
                candidate.replace("-", "_"),
                candidate.lower().replace("_", "-"),
            ]
            matched = False
            # Check field-specific CV graph first (most accurate)
            for probe in probes:
                if probe in field_cv:
                    field_links[short(key)] = field_cv[probe]
                    matched = True
                    break
            # Fall back to the general folder-item lookup
            if not matched:
                for probe in probes:
                    if probe in value_to_uri:
                        field_links[short(key)] = value_to_uri[probe]
                        break

    return {**field_links_inrepo, **field_links}, field_graphs


# ── field_guidance loader ────────────────────────────────────────────────────

def _load_field_guidance(kind: str, repo_root: Optional[Path] = None) -> Dict[str, str]:
    """
    Load field_guidance dict from .github/GEN_ISSUE_TEMPLATE/{kind}.json.

    In a GitHub Actions run GITHUB_WORKSPACE points to the repo root.
    Locally we walk up from this file to find the repo root containing
    .github/GEN_ISSUE_TEMPLATE/.

    Returns {field_name: guidance_markdown} or {} if not found.
    """
    import os, json as _json

    # Candidate roots: explicit arg, GITHUB_WORKSPACE env, walk-up from cwd
    candidates: List[Path] = []
    if repo_root:
        candidates.append(repo_root)
    ws = os.environ.get("GITHUB_WORKSPACE")
    if ws:
        candidates.append(Path(ws))
    # Walk up from cwd looking for .github directory
    cur = Path.cwd()
    for _ in range(8):
        if (cur / ".github").is_dir():
            candidates.append(cur)
            break
        cur = cur.parent

    for root in candidates:
        for name in [kind, kind + "s"]:
            candidate = root / ".github" / "GEN_ISSUE_TEMPLATE" / f"{name}.json"
            if candidate.exists():
                try:
                    data = _json.loads(candidate.read_text(encoding="utf-8"))
                    return data.get("field_guidance", {})
                except Exception:
                    pass

    # Fallback: fetch from GitHub raw URL (works in CI after branch switch)
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if repo:
        import urllib.request
        for name in [kind, kind + "s"]:
            url = (f"https://raw.githubusercontent.com/{repo}/refs/heads/main"
                   f"/.github/GEN_ISSUE_TEMPLATE/{name}.json")
            try:
                with urllib.request.urlopen(url, timeout=5) as r:
                    data = _json.loads(r.read().decode())
                    return data.get("field_guidance", {})
            except Exception:
                pass
    return {}


# ── ReportBuilder ─────────────────────────────────────────────────────────────

class ReportBuilder:
    def __init__(
        self,
        folder_url: str,
        kind: str,
        item: dict,
        graph_data: Optional[dict] = None,
        use_embeddings: bool = True,
        link_threshold: float = 85.0,
        val_result=None,
    ):
        self.folder_url       = folder_url
        self.kind             = kind
        self.item             = item
        self.item_id          = _short_id(item.get("@id", "submitted"))
        self._graph_data      = graph_data
        self.use_embeddings   = use_embeddings
        self.link_threshold   = link_threshold
        self._pre_val_result  = val_result   # pre-computed ValidationResult from new_issue.py
        self._report: Optional[str] = None

    def build(self) -> str:
        if self.use_embeddings:
            try:
                from .folder_similarity import _ensure_sentence_transformers
                _ensure_sentence_transformers()
            except Exception:
                pass

        loader       = self._load_graph()
        folder_items = loader.items

        # Pydantic validation — use pre-computed result if passed in, else run now
        val_result  = None
        val_cls     = None
        covered: FrozenSet[str] = frozenset()
        if self._pre_val_result is not None:
            val_result = self._pre_val_result
            try:
                from cmipld.utils.esgvoc import DATA_DESCRIPTOR_CLASS_MAPPING
                val_cls = DATA_DESCRIPTOR_CLASS_MAPPING.get(self.kind)
                covered = _validator_covered_fields(val_cls)
            except Exception:
                pass
        else:
            try:
                from cmipld.utils.esgvoc import DATA_DESCRIPTOR_CLASS_MAPPING
                val_cls  = DATA_DESCRIPTOR_CLASS_MAPPING.get(self.kind)
                covered  = _validator_covered_fields(val_cls)
                val_result = PydanticValidator(self.kind, self.item).validate()
            except Exception:
                pass

        # Link analysis — resolve submitted plain values to canonical URIs
        link_result = None
        field_links: Dict[str, str] = {}
        # Also collect the full @id of each folder item for table links
        folder_ids: Dict[str, str] = {
            _short_id(fi.get("@id", f"item_{i}")): fi.get("@id", "")
            for i, fi in enumerate(folder_items)
        }
        # Build a lookup: short_id -> full item dict (for diff tables)
        folder_by_id: Dict[str, dict] = {
            _short_id(fi.get("@id", f"item_{i}")): fi
            for i, fi in enumerate(folder_items)
        }
        try:
            field_links, field_graphs = _build_links_from_folder(
                self.item, folder_items,
            )
            enriched = dict(self.item)
            for fname, uri in field_links.items():
                enriched[fname] = {"@id": uri}
            link_result = LinkAnalyzer(loader).analyze(enriched)
        except Exception:
            field_links  = {}
            field_graphs = {}
            pass

        # Text similarity — exclude @-keys, drs/validation, CV link fields,
        # and report-skip metadata. Do NOT exclude pydantic-covered fields —
        # validators check schema constraints, not content, so those fields
        # are still meaningful to compare numerically.
        link_fields = link_result.link_fields if link_result else set()
        exclude_set = (
            link_fields
            | REPORT_SKIP_EXACT
            | {f"@{k}" for k in REPORT_SKIP_EXACT}
        )
        # Exclude blank description fields — they add noise without meaning
        if not (self.item.get("description") or "").strip():
            exclude_set = exclude_set | {"description"}
        sim_result = None
        try:
            sim_result = TextSimilarityAnalyzer(
                loader,
                exclude=exclude_set,
            ).analyze(self.item, item_id=self.item_id)
        except Exception:
            pass

        # Load field guidance from GEN_ISSUE_TEMPLATE JSON
        guidance = _load_field_guidance(self.kind)

        sections: List[str] = [
            self._header(),
            self._checklist(val_result, covered),
        ]
        # Only show the "Schema validation failed" admonition when validation
        # ACTUALLY failed. The report is only built after STEP 1 validation
        # passed (otherwise new_issue.py exits before getting here), so this
        # branch is rarely taken — but when somebody runs ReportBuilder
        # directly on raw data (no pre-computed val_result), it can still
        # trigger and we need to be honest about the result.
        #
        # Previously this admonition appeared whenever errors_md was non-empty,
        # which is misleading because pycmipld emits warnings/info in
        # validation_md even on success. Reviewers were seeing "validation
        # failed" on submissions that had successfully produced a PR.
        if val_result and not val_result.passed and val_result.errors_md:
            sections.append(self._errors_admonition(val_result.errors_md))
        elif val_result and val_result.passed and val_result.errors_md:
            # Validation passed but pycmipld returned notes — show them under
            # a non-alarming header so reviewers can still see the diagnostic
            # output (same content as fed to pydantic on the massaged copy).
            sections.append(self._validation_notes(val_result.errors_md))

        sections.append(self._link_section(link_result, field_links, folder_ids, folder_by_id, field_graphs, sim_result))
        sections.append(self._text_section(sim_result, folder_ids, folder_by_id, guidance, exclude_set))
        sections.append(self._footer())

        self._report = "\n\n".join(s for s in sections if s.strip())
        _write_step_summary(self._report)
        return self._report

    def _load_graph(self) -> GraphLoader:
        if self._graph_data is not None:
            return GraphLoader(self.folder_url, graph_data=self._graph_data)
        # Try _graph.json first, then _graph.jsonld, then give up gracefully.
        # Always strip local mappings so emd: resolves to the remote URL.
        try:
            import cmipld
            url  = f"{self.folder_url.rstrip('/')}/_graph.json"
            with cmipld.ensure_remote():
                data = cmipld.expand(url, depth=4)
            return GraphLoader(self.folder_url, graph_data=data)
        except Exception:
            pass
        try:
            return GraphLoader(self.folder_url)  # tries _graph.jsonld via _fetch()
        except Exception:
            print(f"  ⚠ Could not load graph for {self.folder_url} — similarity sections will be empty", flush=True)
            return GraphLoader(self.folder_url, graph_data=None, _empty=True)

    def write(self, path: str) -> str:
        if self._report is None:
            self.build()
        Path(path).write_text(self._report, encoding="utf-8")
        return path

    # ── sections ──────────────────────────────────────────────────────────────

    def _header(self) -> str:
        types = ", ".join(
            t.split(":")[-1] for t in self.item.get("@type", [])
            if not _TYPE_RE.search(t)
        ) or ", ".join(self.item.get("@type", []))
        # Header now serves both reviewers (on the PR) and submitters (on the
        # issue). Replaced the old "reviewers only" disclaimer with a short
        # explanation of what the three sections below mean.
        return (
            f"`{self.item_id}`\n\n"
            f"> [!NOTE]\n"
            f"> This report has three parts:\n"
            f">   **1. Field Status** — every schema field, with what was submitted.\n"
            f">   **2. Controlled Vocabulary Links** — how submitted values match registered CV entries.\n"
            f">   **3. Content Similarity** — overlap with existing items (potential duplicates).\n"
            f">\n"
            f"> **Legend** — `[x]` validated by schema or explicitly missing required · `[ ]` needs manual check · `← failed` schema error · `← missing` required but absent · `← extra` not in schema.\n\n"
            f"| Property | Value |\n"
            f"|----------|-------|\n"
            f"| **Type** | `{self.kind}` |\n"
            f"| **Submitted ID** | `{self.item_id}` |\n"
            f"| **Generated** | {_now()} |\n"
        )

    def _checklist(self, val_result, covered: FrozenSet[str]) -> str:
        """
  
        Compact checkbox list.
        [x] = reviewed (validated or explicitly missing required)
        [ ] = needs manual review
        Legend line explains the status suffixes.
       
        """

        def _display(v: Any) -> str:
            if v in ("", None, [], {}):
                return "_not submitted_"
            return f"`{_table_cell(v, 50)}`"

        submitted       = {k: v for k, v in self.item.items() if not _is_report_skip(k)}
        submitted_short = {short(k): v for k, v in submitted.items()}

        lines = [
            "---\n",
            "### 1. Field Status\n",
            # "> `[x]` reviewed automatically · `[ ]` needs manual check "
            # "· `← failed` schema error · `← missing` required but absent · "
            # "`← extra` not in schema\n",
        ]

        if val_result is None:
            lines.append("_No pydantic model — all fields require manual review._\n")
            for k, v in sorted(submitted.items(), key=lambda x: short(x[0])):
                lines.append(f"- [ ] `{short(k)}`: {_display(v)} ← extra")
            return "\n".join(lines) + "\n"

        model_meta = val_result._model_meta
        failed     = val_result.failed_fields

        # Pre-compute summary counts so reviewers see the headline numbers
        # (X submitted, Y validated, Z need review, N missing required)
        # before scanning the per-field list.
        n_submitted_total  = 0    # any model field present in submission
        n_validated        = 0    # schema-validated (covered) and not failed
        n_failed           = 0    # schema-validated but failed
        n_manual           = 0    # submitted but no custom check → reviewer judgement
        n_missing_required = 0    # required schema field absent from submission
        n_extra            = sum(
            1 for k in val_result.unmodelled_fields if not _is_report_skip(k)
        )
        for fname, info in model_meta.items():
            if fname in REPORT_SKIP_EXACT:
                continue
            if fname in submitted_short:
                n_submitted_total += 1
                if fname in covered:
                    orig_key = next((k for k in submitted if short(k) == fname), fname)
                    if orig_key in failed:
                        n_failed += 1
                    else:
                        n_validated += 1
                else:
                    n_manual += 1
            elif info.get("required"):
                n_missing_required += 1

        summary_bits = []
        if n_submitted_total:
            summary_bits.append(f"**{n_submitted_total} submitted**")
        if n_validated:
            summary_bits.append(f"✅ {n_validated} validated")
        if n_manual:
            summary_bits.append(f"👀 {n_manual} need manual review")
        if n_failed:
            summary_bits.append(f"❌ {n_failed} failed")
        if n_missing_required:
            summary_bits.append(f"⚠️ {n_missing_required} required missing")
        if n_extra:
            summary_bits.append(f"❓ {n_extra} extra")
        if summary_bits:
            lines.append(" · ".join(summary_bits) + "\n")

        # Schema fields — sorted: failed first, then passed validated, then manual, then absent
        entries: List[tuple] = []  # (sort_key, checkbox, text)

        for fname, info in sorted(model_meta.items()):
            if fname in REPORT_SKIP_EXACT:
                continue
            req = " _(required)_" if info["required"] else ""

            if fname in submitted_short:
                val = submitted_short[fname]
                if fname in covered:
                    orig_key = next((k for k in submitted if short(k) == fname), fname)
                    if orig_key in failed:
                        entries.append((0, "[x]", f"`{fname}`{req}: {_display(val)} ← **failed**"))
                    else:
                        entries.append((1, "[x]", f"`{fname}`{req}: {_display(val)}"))
                else:
                    entries.append((2, "[ ]", f"`{fname}`{req}: {_display(val)}"))
            else:
                if info["required"]:
                    entries.append((3, "[x]", f"`{fname}`{req}: _not submitted_ ← **missing**"))
                else:
                    entries.append((4, "[ ]", f"`{fname}`{req}"))

        # Extra fields not in schema
        for k in sorted(val_result.unmodelled_fields, key=short):
            if _is_report_skip(k):
                continue
            val = submitted.get(k, "")
            entries.append((5, "[ ]", f"`{short(k)}`: {_display(val)} ← extra"))

        entries.sort(key=lambda e: e[0])
        for _, cb, text in entries:
            lines.append(f"- {cb} {text}")

        lines.append("")
        return "\n".join(lines)

    def _errors_admonition(self, errors_md: str) -> str:
        kept_rows = []
        for line in errors_md.strip().splitlines():
            if line.startswith("|") and "---" not in line and "Field" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if parts and short(parts[0].strip("`")) in REPORT_SKIP_EXACT:
                    continue
            kept_rows.append(line)

        data_rows = [r for r in kept_rows
                     if r.startswith("|") and "---" not in r and "Field" not in r]
        if not data_rows:
            return ""

        filtered_md = "\n".join(kept_rows)
        return (
            "> [!CAUTION]\n"
            "> **Schema validation failed** — the following errors must be resolved before this submission can be merged.\n>\n"
            + "\n".join(f"> {line}" for line in filtered_md.splitlines())
            + "\n"
        )

    def _validation_notes(self, errors_md: str) -> str:
        """
        Render pycmipld's validation_md as informational notes when validation
        passed. Same content as would be shown to the submitter in the issue
        comment if validation had failed — but framed as 'pydantic notes'
        rather than 'failed' because the model instance was successfully
        constructed (passed=True) and the PR therefore exists.
        """
        kept_rows = []
        for line in errors_md.strip().splitlines():
            if line.startswith("|") and "---" not in line and "Field" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if parts and short(parts[0].strip("`")) in REPORT_SKIP_EXACT:
                    continue
            kept_rows.append(line)

        data_rows = [r for r in kept_rows
                     if r.startswith("|") and "---" not in r and "Field" not in r]
        if not data_rows:
            return ""

        filtered_md = "\n".join(kept_rows)
        return (
            "<details><summary>Pydantic validation notes "
            "(<em>same data fed to the schema — passed</em>)</summary>\n\n"
            "> [!NOTE]\n"
            "> The submission passed schema validation (otherwise this PR would not exist). "
            "These are the diagnostic rows pycmipld emitted on the massaged copy of the data — "
            "shown here for transparency, not as blockers.\n>\n"
            + "\n".join(f"> {line}" for line in filtered_md.splitlines())
            + "\n\n</details>\n"
        )

    def _link_section(
        self,
        link_result,
        field_links: Dict[str, str],
        folder_ids: Dict[str, str],
        folder_by_id: Dict[str, dict],
        field_graphs: Dict[str, str],
        sim_result=None,
    ) -> str:
        if not field_links and link_result is None and not any(
            self.item.get(f) for f in INREPO_LINK_FIELDS
        ):
            return "---\n\n### 2. Controlled Vocabulary Links\n\n_Link analysis unavailable._\n"

        # Build content score lookup from sim_result for use in compare-against
        content_scores: Dict[str, float] = {}
        if sim_result:
            content_scores = {oid: round(s * 100, 1) for oid, s in sim_result.pairs}

        lines = [f"---\n\n### 2. Controlled Vocabulary Links\n", "```\nWe are able to compare the controlled aspect of a submission by looking at the links to registered components of the CVs as provided by the dropdown fields. This is the quickest way to identify potential duplicates and overlaps between submissions.\n```\n"]

        # Count in-repo linked fields for the resolved fraction
        inrepo_present = sum(
            1 for f in INREPO_LINK_FIELDS
            if self.item.get(f) not in (None, "", [], {})
        )

        if field_links or inrepo_present:
            # Total = CV-eligible fields + in-repo link fields with a value
            total_cv = sum(
                1 for k, v in self.item.items()
                if k in field_graphs
                and not _is_report_skip(k)
                and v not in ("", None, [], {})
            ) + inrepo_present
            resolved = len(field_links) + inrepo_present
            fraction = f"{resolved}/{total_cv}" if total_cv else str(resolved)
            pct      = f"{resolved / total_cv * 100:.0f}%" if total_cv else "—"
            lines.append(f"**Checking that linked files resolve: {fraction} ({pct})**\n")

            # Mermaid diagram
            # Build by_type from CV-resolved field_links
            by_type: Dict[str, List[tuple]] = {}
            for fkey, uri in sorted(field_links.items()):
                cv_type  = uri.split("/")[-2] if uri.count("/") >= 3 else "cv"
                val_stem = uri.split("/")[-1]
                by_type.setdefault(cv_type, []).append((fkey, val_stem, uri, {}))

            # Also inject in-repo link fields directly from self.item.
            # Values may be plain strings (raw submission) OR full dicts
            # (after validate_data substitution), so handle both.
            # When a dict is present its data is used directly for Mermaid
            # expansion — no server fetch needed.
            for field_stem, base_url in INREPO_LINK_FIELDS.items():
                val = None
                for k, v in self.item.items():
                    if short(k) == field_stem:
                        val = v
                        break
                if not val or val in ("", [], {}):
                    continue
                cv_type = base_url.rstrip("/").split("/")[-1]
                vals = val if isinstance(val, list) else [val]
                for v in vals:
                    if not v:
                        continue
                    if isinstance(v, str):
                        sid  = v.strip().lower()
                        data = {}
                    elif isinstance(v, dict):
                        raw  = v.get("@id") or v.get("validation_key") or ""
                        sid  = raw.split("/")[-1].strip().lower()
                        data = v
                    else:
                        continue
                    if not sid:
                        continue
                    uri = f"{base_url.rstrip('/')}/{sid}"
                    if not any(vs == sid for _, vs, _, _ in by_type.get(cv_type, [])):
                        by_type.setdefault(cv_type, []).append((field_stem, sid, uri, data))

            lines += ["<details><summary>Graph of links in submission.</summary>\n", "```mermaid", "graph TD"]
            node = _safe_node(self.item_id)
            lines.append(f'    {node}(["{self.item_id}"])')
            lines.append("")

            for cv_type, entries in sorted(by_type.items()):
                sg = _safe_node(f"sg_{cv_type}")
                lines.append(f'    subgraph {sg}["{cv_type}"]')
                for entry in entries:
                    fkey, val_stem, uri = entry[0], entry[1], entry[2]
                    # entry may be a 3-tuple (CV fields) or 4-tuple (in-repo, with data dict)
                    inline_data = entry[3] if len(entry) == 4 else {}
                    nid       = _safe_node(f"{cv_type}_{val_stem}")
                    click_url = uri + ".json" if "mipcvs.dev" in uri and not uri.endswith(".json") else uri
                    lines.append(f'        {nid}["{val_stem}"]')
                    lines.append(f'        click {nid} "{click_url}" _blank')

                    # Expand horizontal_subgrid nodes: use inline dict data if
                    # available (from validate_data), otherwise fetch from server.
                    if cv_type == "horizontal_subgrid":
                        sg_data = inline_data if inline_data else _fetch_inrepo_item(uri)
                        grid_cell = sg_data.get("horizontal_grid_cells")
                        if grid_cell and isinstance(grid_cell, str):
                            gc_nid  = _safe_node(f"gc_{val_stem}")
                            gc_url  = f"{INREPO_LINK_FIELDS['horizontal_grid_cells']}/{grid_cell}.json"
                            lines.append(f'        {gc_nid}["grid: {grid_cell}"]')
                            lines.append(f'        click {gc_nid} "{gc_url}" _blank')
                            lines.append(f'        {nid} --> {gc_nid}')
                        vtypes = sg_data.get("cell_variable_type", [])
                        if isinstance(vtypes, str):
                            vtypes = [vtypes]
                        for vt in sorted(vtypes):
                            vt_nid = _safe_node(f"vt_{val_stem}_{vt}")
                            lines.append(f'        {vt_nid}("{vt}")')
                            lines.append(f'        {nid} --> {vt_nid}')

                lines.append("    end")
                lines.append("")
                for entry in entries:
                    val_stem = entry[1]
                    nid = _safe_node(f"{cv_type}_{val_stem}")
                    lines.append(f'    {node} --> {nid}')

            lines += ["```", "", "</details>", ""]

        if link_result is not None:
            high = [(oid, pct, n_shared, n_sub) for oid, pct, n_shared, n_sub in link_result.pairs
                    if pct >= self.link_threshold]
            if high:
                lines += [
                    "> [!WARNING]",
                    f"> **{len(high)} existing item(s) share ≥{self.link_threshold:.0f}% link overlap.**"
                    " Review field differences below before merging.\n",
                ]
                # Checkbox list with link% and content%
                for oid, pct, n_shared, n_sub in high:
                    link   = self._item_link(oid, folder_ids)
                    cscore = content_scores.get(oid)
                    cscore_str = f"{cscore:.1f}%" if cscore is not None else "—"
                    lines.append(f"- [ ] {link} ({pct:.1f}% | {cscore_str})")
                lines.append("")
                # Sequential collapsibles — no checkboxes, no content score in summary
                for oid, pct, n_shared, n_sub in high:
                    bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                    url  = folder_ids.get(oid, "")
                    if url and "mipcvs.dev" in url and not url.endswith(".json"):
                        url += ".json"
                    cscore = content_scores.get(oid)
                    cscore_str = f"{cscore:.1f}%" if cscore is not None else "—"
                    summary = f"<a href='{url}'>{oid}</a> `{bar}` — Links: {n_shared}/{n_sub} ({pct:.1f}% | {cscore_str})"
                    diff = _link_diff(self.item, folder_by_id.get(oid, {}), set(field_links.keys()))
                    lines.append(f'<div style="padding-left:1.5em"><details><summary>{summary}</summary>\n\n{diff}\n\n</details></div>\n')
            else:
                lines.append(
                    f"_No existing items exceed {self.link_threshold:.0f}% link overlap._\n"
                )

            if link_result.pairs:
                lines.append("<details><summary>All CV link comparisons</summary>\n")
                for oid, pct, n_shared, n_sub in link_result.pairs:
                    bar    = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                    url    = folder_ids.get(oid, "")
                    if url and "mipcvs.dev" in url and not url.endswith(".json"):
                        url += ".json"
                    cscore = content_scores.get(oid)
                    cscore_str = f"{cscore:.1f}%" if cscore is not None else "—"
                    summary = f"<a href='{url}'>{oid}</a> `{bar}` — Links: {n_shared}/{n_sub} ({pct:.1f}% | {cscore_str})"
                    # Auto-expand items above 50% link overlap so reviewers see
                    # the diff immediately without an extra click — the wrapper
                    # itself ("All CV link comparisons") stays collapsed.
                    open_attr = " open" if pct > 50 else ""
                    lines.append(f'<div style="padding-left:1.5em"><details{open_attr}><summary>{summary}</summary>\n\n{_link_diff(self.item, folder_by_id.get(oid, {}), set(field_links.keys()))}\n\n</details></div>\n')
                lines.append("\n</details>\n")

        return "\n".join(lines)

    def _text_section(
        self,
        sim_result,
        folder_ids: Dict[str, str],
        folder_by_id: Dict[str, dict],
        guidance: Dict[str, str] = {},
        exclude_set: Optional[Set[str]] = None,
    ) -> str:
        if sim_result is None:
            return "---\n\n### 3. Content Similarity\n\n_Content similarity analysis unavailable._\n"

        lines = [f"---\n\n### 3. Content Similarity\n","```\nWhen it comes to free text and numerical entries, direct comparisons are more difficult. Instead we use a combination of text similarity and field exclusions to identify items that contain similar content. We exclude fields that carry links (they are covered by the previous section) and fields that have explicit pydantic validators (they have explicit checks) to focus on content that is not already being checked by other means.\n```\n"]

        if not sim_result.text_fields:
            lines.append("_No free-text fields remain after exclusions._\n")
            return "\n".join(lines)

        lines.append(
            f"_{len(sim_result.text_fields)} field(s) compared using {sim_result.method}._\n"
        )

        # Fields used — compact table rather than per-field dropdowns
        lines += [
            "<details><summary>Fields included in comparison</summary>\n",
            "| Field | Value |",
            "|-------|-------|",
        ]
        for k, v in sorted(sim_result.text_fields.items(), key=lambda x: short(x[0])):
            fname   = short(k)
            display = _table_cell(v, 60)
            tip     = guidance.get(fname, "")
            label   = f"`{fname}`" if not tip else f"[`{fname}`](# \"{_table_cell(tip, 80)}\")"
            lines.append(f"| {label} | {display} |")
        lines += ["", "</details>", ""]

        if sim_result.pairs:
            text_field_keys = set(sim_result.text_fields.keys()) | {short(k) for k in sim_result.text_fields}
            high_sim = [(oid, s) for oid, s in sim_result.pairs
                        if s * 100 >= self.link_threshold]
            if high_sim:
                lines += [
                    "> [!WARNING]",
                    f"> **{len(high_sim)} existing item(s) exceed {self.link_threshold:.0f}% content similarity.**"
                    " Confirm this submission is not a duplicate.\n",
                ]
                # Checkbox list with content%
                for oid, score in high_sim:
                    pct  = score * 100
                    lines.append(f"- [ ] {self._item_link(oid, folder_ids)} ({pct:.1f}%)")
                lines.append("")
                # Sequential collapsibles
                for oid, score in high_sim:
                    pct  = score * 100
                    bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                    url  = folder_ids.get(oid, "")
                    if url and "mipcvs.dev" in url and not url.endswith(".json"):
                        url += ".json"
                    diff = _text_diff(sim_result.text_fields, folder_by_id.get(oid, {}), text_field_keys, exclude_set)
                    is_identical = diff.startswith("_Compared text fields are identical")
                    identical_flag = "  <span style='color:red'><b>identical</b></span>" if is_identical else ""
                    summary = f"<a href='{url}'>{oid}</a> `{bar}` — {pct:.1f}%{identical_flag}"
                    lines.append(f'<div style="padding-left:1.5em"><details><summary>{summary}</summary>\n\n{diff}\n\n</details></div>\n')
            else:
                lines.append(
                    f"_No existing items exceed {self.link_threshold:.0f}% content similarity._\n"
                )

            lines.append("<details><summary>All content comparisons</summary>\n")
            for oid, score in sim_result.pairs:
                pct  = score * 100
                bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                url  = folder_ids.get(oid, "")
                if url and "mipcvs.dev" in url and not url.endswith(".json"):
                    url += ".json"
                diff = _text_diff(sim_result.text_fields, folder_by_id.get(oid, {}), text_field_keys, exclude_set)
                is_identical = diff.startswith("_Compared text fields are identical")
                identical_flag = "  <span style='color:red'><b>identical</b></span>" if is_identical else ""
                summary = f"<a href='{url}'>{oid}</a> `{bar}` — {pct:.1f}%{identical_flag}"
                # Auto-expand comparisons above 50% similarity so reviewers can
                # spot near-duplicates immediately. The wrapper stays collapsed.
                open_attr = " open" if pct > 50 else ""
                lines.append(f'<div style="padding-left:1.5em"><details{open_attr}><summary>{summary}</summary>\n\n{diff}\n\n</details></div>\n')
            lines.append("\n</details>\n")

        return "\n".join(lines)

    @staticmethod
    def _item_link(short_id: str, folder_ids: Dict[str, str]) -> str:
        """
        Return a Markdown link for a short item id.
        If the full @id contains 'mipcvs.dev', append '.json'.
        """
        full_id = folder_ids.get(short_id, "")
        if full_id:
            url = full_id
            if "mipcvs.dev" in url and not url.endswith(".json"):
                url = url + ".json"
            return f"[`{short_id}`]({url})"
        return f"`{short_id}`"

    def _footer(self) -> str:
        return (
            "---\n"
            "_Generated by [cmipld](https://github.com/WCRP-CMIP/CMIP-LD) · "
            f"{_now()}_\n"
        )

    def __repr__(self):
        state = "built" if self._report else "not built"
        return f"ReportBuilder({self.folder_url!r}, kind={self.kind!r}, {state})"


# ── Dedicated subgrid report ──────────────────────────────────────────────────

def build_subgrid_report(data: dict, folder_items: list | None = None) -> str:
    """
    Generate a focused review report for a horizontal_subgrid record.

    Unlike the full ReportBuilder (which is designed for records with a
    pydantic model and many fields), subgrid records have exactly two
    meaningful linked fields defined in their context:

        horizontal_grid_cell(s) — @type:@id, links to horizontal_grid_cell folder
        cell_variable_type      — @type:@id, links to constants CV

    This function produces a compact Markdown report that:
      1. Clearly identifies the record as a subgrid with its @id
      2. Resolves and displays both linked fields with clickable URLs
      3. Compares against all existing subgrid folder items using Jaccard
         similarity on those same linked fields, flagging close matches

    Parameters
    ----------
    data : dict
        The subgrid record dict (with plain string values for linked fields).
    folder_items : list[dict] | None
        Existing subgrid records from the folder graph. When None, comparison
        is skipped (no network access attempted).
    """
    sid = _short_id(data.get("@id", "submitted"))

    # ── 1. Resolve linked fields ───────────────────────────────────────────
    # Grid cell — field may be 'horizontal_grid_cells' (plural, data key)
    # or 'horizontal_grid_cell' (singular, context key)
    gc_base = SHORT_ID_LINK_FIELDS["horizontal_grid_cells"]
    gc_val  = (
        data.get("horizontal_grid_cells")
        or data.get("horizontal_grid_cell")
        or ""
    )
    if isinstance(gc_val, dict):
        gc_val = gc_val.get("@id", "").split("/")[-1]
    gc_val = gc_val.strip().lower() if gc_val else ""
    gc_uri = f"{gc_base}/{gc_val}" if gc_val else ""

    # Variable types
    cvt_base = SHORT_ID_LINK_FIELDS["cell_variable_type"]
    cvt_raw  = data.get("cell_variable_type", [])
    if isinstance(cvt_raw, str):
        cvt_raw = [cvt_raw]
    cvt_vals = sorted(
        (v.strip().lower() if isinstance(v, str) else v.get("@id", "").split("/")[-1])
        for v in cvt_raw
        if v
    )
    cvt_uris = [(v, f"{cvt_base}/{v}") for v in cvt_vals]

    # ── 2. Build link set for Jaccard comparison ───────────────────────────
    own_links: set[str] = set()
    if gc_uri:
        own_links.add(gc_uri)
    own_links.update(uri for _, uri in cvt_uris)

    # ── 3. Compare against existing subgrid items ──────────────────────────
    comparisons: list[tuple[str, float]] = []
    if folder_items:
        for fi in folder_items:
            other_id = _short_id(fi.get("@id", ""))
            if not other_id or other_id == sid:
                continue
            other_links: set[str] = set()

            # Grid cell from existing item
            fi_gc = fi.get("horizontal_grid_cells") or fi.get("horizontal_grid_cell") or ""
            if isinstance(fi_gc, dict):
                fi_gc = fi_gc.get("@id", "").split("/")[-1]
            fi_gc = fi_gc.strip().lower() if fi_gc else ""
            if fi_gc:
                other_links.add(f"{gc_base}/{fi_gc}")

            # Variable types from existing item
            fi_cvt = fi.get("cell_variable_type", [])
            if isinstance(fi_cvt, str):
                fi_cvt = [fi_cvt]
            for v in fi_cvt:
                v_str = v.strip().lower() if isinstance(v, str) else v.get("@id", "").split("/")[-1]
                if v_str:
                    other_links.add(f"{cvt_base}/{v_str}")

            union = own_links | other_links
            score = len(own_links & other_links) / len(union) if union else 0.0
            comparisons.append((other_id, round(score * 100, 1)))

        comparisons.sort(key=lambda x: x[1], reverse=True)

    # ── 4. Render Markdown ─────────────────────────────────────────────────
    lines = [
        f"`{sid}` *(horizontal_subgrid)*\n",
        f"> [!IMPORTANT]  \n"
        f"> This report is for use of reviewers only!\n",
        "---\n",
        "### Linked Fields\n",
    ]

    # Grid cell
    if gc_uri:
        click_url = gc_uri + ".json"
        lines.append(f"- **`horizontal_grid_cell`** → [{gc_val}]({click_url})")
    else:
        lines.append("- **`horizontal_grid_cell`** → _not specified_")

    # Variable types
    if cvt_uris:
        vt_links = ", ".join(f"[{v}]({u}.json)" for v, u in cvt_uris)
        lines.append(f"- **`cell_variable_type`** → {vt_links}")
    else:
        lines.append("- **`cell_variable_type`** → _none_")

    lines.append("")

    # Comparison table
    if comparisons:
        high = [(oid, pct) for oid, pct in comparisons if pct >= 80.0]
        if high:
            lines += [
                "> [!WARNING]",
                f"> **{len(high)} existing subgrid(s) share ≥80% link overlap.**"
                " Confirm this is not a duplicate.\n",
            ]
        lines.append("<details><summary>Similarity against existing subgrids</summary>\n")
        lines += [
            "| Subgrid | Overlap |",
            "|---------|---------|" ,
        ]
        for oid, pct in comparisons:
            bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
            lines.append(f"| `{oid}` | {pct:.0f}% `{bar}` |")
        lines.append("\n</details>\n")
    else:
        lines.append("_No existing subgrids to compare against._\n")

    lines.append(
        "---\n"
        f"_Generated by [cmipld](https://github.com/WCRP-CMIP/CMIP-LD) · {_now()}_\n"
    )

    return "\n".join(lines)
