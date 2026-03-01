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
})

_TYPE_RE = re.compile(
    r"(wcrp:|esgvoc:)|/docs/contents/|/(universal|constants|emd)$"
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def _is_report_skip(key: str) -> bool:
    if is_default_skip(key):
        return True
    return short(key) in REPORT_SKIP_EXACT


def _compact_val(v: Any, max_len: int = 80) -> str:
    if isinstance(v, dict):
        s = v.get("@id", "").split("/")[-1] or v.get("@value", str(v))
    elif isinstance(v, list):
        s = ", ".join(_compact_val(e, 40) for e in v)
    else:
        s = str(v)
    return (s[:max_len] + "…") if len(s) > max_len else s


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

def _build_links_from_folder(item: dict, folder_items: List[dict]) -> Dict[str, str]:
    """
    For a submitted item with plain string values, resolve canonical URIs
    by searching the folder graph items (which have full URI @id refs).

    Returns {field_stem: canonical_uri}.
    """
    value_to_uri: Dict[str, str] = {}
    for fi in folder_items:
        for key, val in fi.items():
            if key.startswith("@"):
                continue
            if isinstance(val, dict) and "@id" in val:
                uri = val["@id"]
                if _is_data_link(uri):
                    stem = uri.split("/")[-1]
                    for variant in [stem, stem.replace("-", "_"), stem.replace("_", "-")]:
                        value_to_uri[variant] = uri
            elif isinstance(val, list):
                for elem in val:
                    if isinstance(elem, dict) and "@id" in elem:
                        uri = elem["@id"]
                        if _is_data_link(uri):
                            stem = uri.split("/")[-1]
                            for variant in [stem, stem.replace("-", "_"), stem.replace("_", "-")]:
                                value_to_uri[variant] = uri

    field_links: Dict[str, str] = {}
    for key, val in item.items():
        if _is_report_skip(key):
            continue
        if isinstance(val, str) and val:
            for probe in [val.strip(), val.lower().strip(),
                          val.replace("_", "-"), val.replace("-", "_"),
                          val.lower().replace("_", "-")]:
                if probe in value_to_uri:
                    field_links[short(key)] = value_to_uri[probe]
                    break
    return field_links


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
        link_threshold: float = 80.0,
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
        try:
            field_links = _build_links_from_folder(self.item, folder_items)
            enriched = dict(self.item)
            for fname, uri in field_links.items():
                enriched[fname] = {"@id": uri}
            link_result = LinkAnalyzer(loader).analyze(enriched)
        except Exception:
            pass

        # Text similarity — exclude @-keys, drs/validation, link fields,
        # AND validator-covered fields (they have explicit checks)
        link_fields = link_result.link_fields if link_result else set()
        # covered fields may use short names; also exclude by short(k)
        exclude_set = (
            link_fields
            | set(covered)                           # short model field names
            | REPORT_SKIP_EXACT
            | {f"@{k}" for k in REPORT_SKIP_EXACT}  # @-prefixed variants
        )
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

        sections.append(self._link_section(link_result, field_links, folder_ids))
        sections.append(self._text_section(sim_result, folder_ids, guidance))
        sections.append(self._footer())

        self._report = "\n\n---\n\n".join(s for s in sections if s.strip())
        return self._report

    def _load_graph(self) -> GraphLoader:
        if self._graph_data is not None:
            return GraphLoader(self.folder_url, graph_data=self._graph_data)
        try:
            import cmipld
            url  = f"{self.folder_url.rstrip('/')}/_graph.json"
            data = cmipld.expand(url, depth=4)
            return GraphLoader(self.folder_url, graph_data=data)
        except Exception:
            return GraphLoader(self.folder_url)

    def write(self, path: str) -> str:
        if self._report is None:
            self.build()
        Path(path).write_text(self._report, encoding="utf-8")
        return path

    # ── sections ──────────────────────────────────────────────────────────────

    def _header(self) -> str:
        types = ", ".join(self.item.get("@type", []))
        return (
            f"# Review Report: `{self.item_id}`\n\n"
            f"| | |\n|---|---|\n"
            f"| **Kind** | `{self.kind}` |\n"
            f"| **Folder** | `{self.folder_url}` |\n"
            f"| **Type** | `{types}` |\n"
            f"| **Generated** | {_now()} |\n"
        )

    def _checklist(self, val_result, covered: FrozenSet[str]) -> str:
        """
        Three subsections:
          Automatically validated  — submitted, has explicit validator, ✅/❌
          Schema fields            — submitted or not, in model, no validator
          Not in schema            — submitted, unknown to model, ⚠️
        """
        lines = ["## Field Checklist\n"]

        # Treat empty strings as null — display as 'null' but still include
        def _display(v):
            if v in ("", None, [], {}):
                return "null"
            return v

        submitted = {
            k: _display(v) for k, v in self.item.items()
            if not _is_report_skip(k)
        }
        # Exclude genuine nulls from schema matching (don't count as submitted)
        submitted_nonnull = {k: v for k, v in submitted.items() if v != "null"}
        submitted_short   = {short(k): v for k, v in submitted.items()}

        if val_result is None:
            lines.append("_No pydantic model — all fields need manual review._\n")
            for k, v in sorted(submitted.items(), key=lambda x: short(x[0])):
                lines.append(f"- [x] ⚠️ `{short(k)}`: {_compact_val(v)}")
            lines.append("")
            return "\n".join(lines)

        model_meta = val_result._model_meta
        failed     = val_result.failed_fields

        # ── 1. Automatically validated ─────────────────────────────────
        auto_rows = []
        for fname, info in sorted(model_meta.items()):
            if fname in REPORT_SKIP_EXACT or fname not in covered:
                continue
            badge = "**required**" if info["required"] else "_optional_"
            if fname in submitted_short:
                display   = _compact_val(submitted_short[fname])
                orig_keys = [k for k in submitted if short(k) == fname]
                orig_key  = orig_keys[0] if orig_keys else fname
                icon      = "❌" if orig_key in failed else "✅"
                auto_rows.append(f"- [x] {icon} `{fname}` ({badge}): {display}")
            else:
                # Not submitted but explicitly validated — mark complete (ran, nothing to do)
                auto_rows.append(f"- [x] `{fname}` ({badge}): _not submitted_")

        if auto_rows:
            lines.append("### Automatically validated\n")
            lines.extend(auto_rows)
            lines.append("")

        # ── 2. Schema fields (no explicit validator) ───────────────────
        schema_rows = []
        for fname, info in sorted(model_meta.items()):
            if fname in REPORT_SKIP_EXACT or fname in covered:
                continue
            badge = "**required**" if info["required"] else "_optional_"
            if fname in submitted_short:
                display = _compact_val(submitted_short[fname])
                schema_rows.append(f"- [x] `{fname}` ({badge}): {display}")
            else:
                # Required not submitted → [x] (must be addressed)
                # Optional not submitted → [-] (known gap, not critical)
                if info["required"]:
                    schema_rows.append(f"- [x] `{fname}` ({badge}): null")
                else:
                    schema_rows.append(f"- [ ] `{fname}` ({badge})")

        if schema_rows:
            lines.append("### Schema fields\n")
            lines.extend(schema_rows)
            lines.append("")

        # ── 3. Not in schema ───────────────────────────────────────────
        extra = [
            k for k in sorted(val_result.unmodelled_fields, key=short)
            if not _is_report_skip(k)
        ]
        if extra:
            lines.append("### Not in schema — manual review\n")
            for k in extra:
                display = _compact_val(submitted.get(k, ""))
                lines.append(f"- [ ] ⚠️ `{short(k)}`: {display}")
            lines.append("")

        return "\n".join(lines)

    def _errors_admonition(self, errors_md: str) -> str:
        # Strip rows that are only about skipped fields (drs_name, id, type)
        # to avoid showing an empty warning block
        kept_rows = []
        for line in errors_md.strip().splitlines():
            if line.startswith("|") and "---" not in line and "Field" not in line:
                # Check if this row is for a skipped field
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if parts and short(parts[0].strip("`")) in REPORT_SKIP_EXACT:
                    continue
            kept_rows.append(line)

        # Rebuild — if only headers remain, suppress the whole block
        data_rows = [r for r in kept_rows
                     if r.startswith("|") and "---" not in r and "Field" not in r]
        if not data_rows:
            return ""

        filtered_md = "\n".join(kept_rows)
        return (
            "> [!WARNING]\n"
            "> **Validation errors** — these fields failed the esgvoc schema "
            "check and must be corrected before merging.\n>\n"
            + "\n".join(f"> {line}" for line in filtered_md.splitlines())
            + "\n"
        )

    def _link_section(
        self,
        link_result,
        field_links: Dict[str, str],
        folder_ids: Dict[str, str],
    ) -> str:
        if not field_links and link_result is None:
            return "## Link Similarity (RDF)\n\n_Link analysis unavailable._\n"

        lines = [
            "## Link Similarity (RDF)\n",
            f"**{len(field_links)} semantic links** resolved from submitted values.\n",
        ]

        # Mermaid — LR layout, group CV nodes by type using subgraphs
        if field_links:
            # Group by CV type (second-to-last path segment)
            by_type: Dict[str, List[tuple]] = {}
            for fkey, uri in sorted(field_links.items()):
                cv_type  = uri.split("/")[-2] if uri.count("/") >= 3 else "cv"
                val_stem = uri.split("/")[-1]
                by_type.setdefault(cv_type, []).append((fkey, val_stem, uri))

            lines += ["### Link graph\n", "```mermaid", "graph TD"]
            node = _safe_node(self.item_id)
            lines.append(f'    {node}(["{self.item_id}"])')
            lines.append("")

            for cv_type, entries in sorted(by_type.items()):
                sg = _safe_node(f"sg_{cv_type}")
                lines.append(f'    subgraph {sg}["{cv_type}"]')
                for fkey, val_stem, uri in entries:
                    nid      = _safe_node(f"{cv_type}_{val_stem}")
                    click_url = uri + ".json" if "mipcvs.dev" in uri and not uri.endswith(".json") else uri
                    lines.append(f'        {nid}["{val_stem}"]')
                    lines.append(f'        click {nid} "{click_url}" _blank')
                lines.append("    end")
                lines.append("")
                for fkey, val_stem, uri in entries:
                    nid = _safe_node(f"{cv_type}_{val_stem}")
                    lines.append(f'    {node} --> {nid}')

            lines += ["```", ""]

        # Similarity table with hyperlinks
        if link_result is not None:
            high = [(oid, pct) for oid, pct in link_result.pairs
                    if pct >= self.link_threshold]
            if high:
                lines += [
                    "> [!WARNING]",
                    f"> **High link similarity** — {len(high)} existing item(s) share "
                    f"≥{self.link_threshold:.0f}% of the same CV links. "
                    "Check these are not duplicates before merging.\n",
                    "| Item | Overlap |",
                    "|------|---------|",
                ]
                for oid, pct in high:
                    bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                    link = self._item_link(oid, folder_ids)
                    lines.append(f"| {link} | {pct:.1f}% {bar} |")
                lines.append("")
            else:
                lines.append(
                    f"_No existing items exceed {self.link_threshold:.0f}% link overlap._\n"
                )

            if link_result.pairs:
                lines += [
                    "",
                    "<details><summary>All link comparisons</summary>\n",
                    "| Item | Overlap |",
                    "|------|---------|",
                ]
                for oid, pct in link_result.pairs:
                    bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                    link = self._item_link(oid, folder_ids)
                    lines.append(f"| {link} | {pct:.1f}% {bar} |")
                lines += ["", "</details>", ""]

        return "\n".join(lines)

    def _text_section(
        self,
        sim_result,
        folder_ids: Dict[str, str],
        guidance: Dict[str, str] = {},
    ) -> str:
        if sim_result is None:
            return "## Content Similarity\n\n_Text similarity analysis unavailable._\n"

        lines = [
            "## Content Similarity\n",
            f"**Method:** {sim_result.method}  \n"
            f"**Fields compared:** {len(sim_result.text_fields)}\n",
        ]

        if not sim_result.text_fields:
            lines.append("_No content fields remain after exclusions._\n")
            return "\n".join(lines)

        # Per-field collapsible dropdowns
        lines.append("### Fields used (click to view guidance)\n")
        for k, v in sorted(sim_result.text_fields.items(), key=lambda x: short(x[0])):
            fname   = short(k)
            display = _compact_val(v, 60)
            tip     = guidance.get(fname, "No notes given.")
            lines.append(
                f"\n<details><summary><code>{fname}</code>: {display}</summary>\n\n"
                + tip.strip()
                + "\n\n</details>"
            )
        lines.append("")

        if sim_result.pairs:
            # Warning box if any item exceeds threshold
            high_sim = [(oid, s) for oid, s in sim_result.pairs if s * 100 >= self.link_threshold]
            if high_sim:
                lines += [
                    "> [!WARNING]",
                    f"> **High content similarity** — {len(high_sim)} item(s) are "
                    f"≥{self.link_threshold:.0f}% similar in content fields. "
                    "Verify this is not a duplicate.\n",
                ]

            lines += [
                "### Content similarity to folder items\n",
                "| Item | Score | Bar |",
                "|------|-------|-----|",
            ]
            for oid, score in sim_result.pairs:
                pct  = score * 100
                bar  = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                flag = " ⚠️" if pct >= self.link_threshold else ""
                link = self._item_link(oid, folder_ids)
                lines.append(f"| {link} | {pct:.1f}% | {bar}{flag} |")
            lines.append("")

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
            "_Report generated by "
            "[cmipld](https://github.com/WCRP-CMIP/CMIP-LD) "
            "`cmipld.utils.similarity.ReportBuilder`_\n"
        )

    def __repr__(self):
        state = "built" if self._report else "not built"
        return f"ReportBuilder({self.folder_url!r}, kind={self.kind!r}, {state})"
