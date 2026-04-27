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

REPORT_SKIP_EXACT = frozenset({
    "id", "type", "drs_name",
    "issue_kind", "issue_type", "issue_category",
    "ui_label", "validation_key",
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
            v = resolved if len(resolved) != 1 else resolved[0]
        # Last-write-wins if both a short and long key map to the same stem
        out[sk] = v
    return out


def _diff_table(submitted: dict, existing: dict) -> str:
    """
    Build a Markdown diff table (no wrapper — caller handles the details block).
    Normalises both dicts to short keys and resolves @id/@value wrappers
    so expanded JSON-LD items don't produce duplicate rows.
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


def _build_links_from_folder(
    item: dict,
    folder_items: List[dict],
) -> Dict[str, str]:
    """
    For a submitted item with plain string values, resolve canonical URIs by:
      1. Inferring which fields are CV fields from the existing folder items
      2. Fetching those CV graphs directly to get all valid values
      3. Falling back to the existing folder items for any values not in the graph

    Returns {field_stem: canonical_uri}.
    """
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

    return field_links, field_graphs


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
    ):
        self.folder_url     = folder_url
        self.kind           = kind
        self.item           = item
        self.item_id        = _short_id(item.get("@id", "submitted"))
        self._graph_data    = graph_data
        self.use_embeddings = use_embeddings
        self.link_threshold = link_threshold
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

        # Pydantic validation + covered fields
        val_result  = None
        val_cls     = None
        covered: FrozenSet[str] = frozenset()
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

        # Text similarity — exclude @-keys, drs/validation, link fields,
        # AND validator-covered fields (they have explicit checks)
        link_fields = link_result.link_fields if link_result else set()
        # covered fields may use short names; also exclude by short(k)
        exclude_set = (
            link_fields
            | set(covered)
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
        if val_result and val_result.errors_md:
            sections.append(self._errors_admonition(val_result.errors_md))

        sections.append(self._link_section(link_result, field_links, folder_ids, folder_by_id, field_graphs))
        sections.append(self._text_section(sim_result, folder_ids, folder_by_id, guidance))
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
        return (
            f"## Submission Review — `{self.item_id}`\n\n"
            f"""> [!IMPORTANT]  \n> This report is for use of reviewers only! \n> It is not intended to be used by submitters and may contain technical details and internal links that are not meaningful outside the review process. \n\n"""
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

    def _link_section(
        self,
        link_result,
        field_links: Dict[str, str],
        folder_ids: Dict[str, str],
        folder_by_id: Dict[str, dict],
        field_graphs: Dict[str, str],
    ) -> str:
        if not field_links and link_result is None:
            return "---\n\n### 2. Controlled Vocabulary Links\n\n_Link analysis unavailable._\n"

        lines = [f"---\n\n### 2. Controlled Vocabulary Links\n", "```\nWe are able to compare the controlled aspect of a submission by looking at the links to registered components of the CVs as provided by the dropdown fields. This is the quickest way to identify potential duplicates and overlaps between submissions.\n```\n"]

        if field_links:
            # Total = CV-eligible fields that were submitted with a non-empty value
            total_cv = sum(
                1 for k, v in self.item.items()
                if k in field_graphs
                and not _is_report_skip(k)
                and v not in ("", None, [], {})
            )
            resolved = len(field_links)
            fraction = f"{resolved}/{total_cv}" if total_cv else str(resolved)
            pct      = f"{resolved / total_cv * 100:.0f}%" if total_cv else "—"
            lines.append(f"* Checking that linked files resolve: {fraction} ({pct})*\n")

            # Mermaid diagram
            by_type: Dict[str, List[tuple]] = {}
            for fkey, uri in sorted(field_links.items()):
                cv_type  = uri.split("/")[-2] if uri.count("/") >= 3 else "cv"
                val_stem = uri.split("/")[-1]
                by_type.setdefault(cv_type, []).append((fkey, val_stem, uri))

            lines += ["<details><summary>Graph of links in submission.</summary>\n", "```mermaid", "graph TD"]
            node = _safe_node(self.item_id)
            lines.append(f'    {node}(["{self.item_id}"])')
            lines.append("")

            for cv_type, entries in sorted(by_type.items()):
                sg = _safe_node(f"sg_{cv_type}")
                lines.append(f'    subgraph {sg}["{cv_type}"]')
                for fkey, val_stem, uri in entries:
                    nid       = _safe_node(f"{cv_type}_{val_stem}")
                    click_url = uri + ".json" if "mipcvs.dev" in uri and not uri.endswith(".json") else uri
                    lines.append(f'        {nid}["{val_stem}"]')
                    lines.append(f'        click {nid} "{click_url}" _blank')
                lines.append("    end")
                lines.append("")
                for fkey, val_stem, uri in entries:
                    nid = _safe_node(f"{cv_type}_{val_stem}")
                    lines.append(f'    {node} --> {nid}')

            lines += ["```", "", "</details>", ""]

        if link_result is not None:
            high = [(oid, pct, n_shared, n_file) for oid, pct, n_shared, n_file in link_result.pairs
                    if pct >= self.link_threshold]
            if high:
                lines += [
                    "> [!WARNING]",
                    f"> **{len(high)} existing item(s) share ≥{self.link_threshold:.0f}% link overlap.**"
                    " Review field differences below before merging.\n",
                ]
                for oid, pct, n_shared, n_file in high:
                    bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                    link = self._item_link(oid, folder_ids)
                    diff = _diff_table(self.item, folder_by_id.get(oid, {}))
                    lines.append(f"- [ ] {link} — {n_shared}/{n_file} ({pct:.1f}%) `{bar}`")
                    lines.append(f"\n<details><summary>Compare against {oid}</summary>\n\n{diff}\n\n</details>\n")
                lines.append("")
            else:
                lines.append(
                    f"_No existing items exceed {self.link_threshold:.0f}% link overlap._\n"
                )

            if link_result.pairs:
                lines.append("<details><summary>All CV link comparisons</summary>\n")
                for oid, pct, n_shared, n_file in link_result.pairs:
                    bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                    link = self._item_link(oid, folder_ids)
                    diff = _diff_table(self.item, folder_by_id.get(oid, {}))
                    lines.append(f"- [ ] {link} — {n_shared}/{n_file} ({pct:.1f}%) `{bar}`")
                    lines.append(f"\n<details><summary>Compare against {oid}</summary>\n\n{diff}\n\n</details>\n")
                lines.append("\n</details>\n")

        return "\n".join(lines)

    def _text_section(
        self,
        sim_result,
        folder_ids: Dict[str, str],
        folder_by_id: Dict[str, dict],
        guidance: Dict[str, str] = {},
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
            high_sim = [(oid, s) for oid, s in sim_result.pairs
                        if s * 100 >= self.link_threshold]
            if high_sim:
                lines += [
                    "> [!WARNING]",
                    f"> **{len(high_sim)} existing item(s) exceed {self.link_threshold:.0f}% content similarity.**"
                    " Confirm this submission is not a duplicate.\n",
                ]
                for oid, score in high_sim:
                    pct  = score * 100
                    bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                    link = self._item_link(oid, folder_ids)
                    diff = _diff_table(self.item, folder_by_id.get(oid, {}))
                    lines.append(f"- [ ] {link} — {pct:.1f}% `{bar}`")
                    lines.append(f"\n<details><summary>Compare against {oid}</summary>\n\n{diff}\n\n</details>\n")
                lines.append("")
            else:
                lines.append(
                    f"_No existing items exceed {self.link_threshold:.0f}% content similarity._\n"
                )

            lines.append("<details><summary>All content comparisons</summary>\n")
            for oid, score in sim_result.pairs:
                pct  = score * 100
                bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                link = self._item_link(oid, folder_ids)
                diff = _diff_table(self.item, folder_by_id.get(oid, {}))
                lines.append(f"- [ ] {link} — {pct:.1f}% `{bar}`")
                lines.append(f"\n<details><summary>Compare against {oid}</summary>\n\n{diff}\n\n</details>\n")
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
