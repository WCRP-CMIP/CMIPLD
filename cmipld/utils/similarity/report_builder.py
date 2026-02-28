"""
ReportBuilder — run all pipeline stages and produce a single Markdown report
with an auto-ticked reviewer checklist.

    report = ReportBuilder(
        folder_url = "emd:horizontal_grid_cells",
        kind       = "horizontal_grid_cell",
        item       = submitted_item,
        graph_data = graph_data,       # already fetched — no extra network call
    ).build()

    print(report)
    # or
    ReportBuilder(...).write("report.md")
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import FrozenSet, List, Optional, Set

from .graph_loader       import GraphLoader, _short_id
from .link_analyzer      import LinkAnalyzer
from .pydantic_validator import PydanticValidator, short, is_default_skip
from .text_similarity    import TextSimilarityAnalyzer


def _now() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")


def _checklist_row(field: str, value, validated: bool, failed: bool) -> str:
    tick    = "x" if validated and not failed else " "
    display = str(value)[:80] + ("…" if len(str(value)) > 80 else "")
    tag     = (" ✅ _auto-validated_" if validated else "") + \
              (" ❌ _failed_"         if failed    else "")
    return f"- [{tick}] `{short(field)}`: `{display}`{tag}"


class ReportBuilder:
    """
    Orchestrate the full pipeline into a single Markdown report.

    Parameters
    ----------
    folder_url : str
        Prefixed folder URL, e.g. ``"emd:horizontal_grid_cells"``.
    kind : str
        esgvoc model kind, e.g. ``"horizontal_grid_cell"``.
    item : dict
        The submitted JSON-LD item.
    graph_data : dict | None
        Pre-fetched graph dict (from ``cmipld.expand()``).  When supplied no
        network call is made to load the folder.
    use_embeddings : bool
        Run sentence-transformer embeddings in the text-similarity stage
        (default True; set False for fast/offline runs).
    """

    def __init__(
        self,
        folder_url: str,
        kind: str,
        item: dict,
        graph_data: Optional[dict] = None,
        use_embeddings: bool = True,
    ):
        self.folder_url    = folder_url
        self.kind          = kind
        self.item          = item
        self.item_id       = _short_id(item.get("@id", "submitted"))
        self._graph_data   = graph_data
        self.use_embeddings = use_embeddings

        # Populated during build()
        self.loader      = None
        self.link_result = None
        self.val_result  = None
        self.sim_result  = None
        self._report: Optional[str] = None

    # ------------------------------------------------------------------
    # build
    # ------------------------------------------------------------------

    def build(self) -> str:
        """Run all stages and return the Markdown report string."""
        sections: List[str] = [self._header()]

        # Stage 1 — load graph
        self.loader = GraphLoader(self.folder_url, graph_data=self._graph_data)

        # Stage 2 — links
        try:
            la = LinkAnalyzer(self.loader)
            self.link_result = la.analyze(self.item)
            sections.append(self.link_result.md)
        except Exception as exc:
            sections.append(f"> ⚠️ Link analysis failed: `{exc}`\n")
            self.link_result = None

        # Stage 3 — pydantic
        try:
            self.val_result = PydanticValidator(self.kind, self.item).validate()
            sections.append(self.val_result.md)
        except Exception as exc:
            sections.append(f"> ⚠️ Pydantic validation failed: `{exc}`\n")
            self.val_result = None

        # Stage 4 — text similarity
        link_fields = self.link_result.link_fields if self.link_result else set()
        val_fields  = self.val_result.validated_fields if self.val_result else frozenset()
        try:
            ta = TextSimilarityAnalyzer(
                self.loader,
                exclude=link_fields | set(val_fields),
            )
            self.sim_result = ta.analyze(self.item, item_id=self.item_id)
            sections.append(self.sim_result.md)
        except Exception as exc:
            sections.append(f"> ⚠️ Text similarity failed: `{exc}`\n")
            self.sim_result = None

        # Stage 5 — checklist
        sections.append(self._checklist(val_fields, self.val_result.failed_fields if self.val_result else frozenset()))

        sections.append(self._footer())
        self._report = "\n\n---\n\n".join(sections)
        return self._report

    # ------------------------------------------------------------------
    # sections
    # ------------------------------------------------------------------

    def _header(self) -> str:
        types = ", ".join(self.item.get("@type", []))
        return (
            f"# 📋 Submission Report: `{self.item_id}`\n\n"
            f"**Kind:** `{self.kind}`  \n"
            f"**Folder:** `{self.folder_url}`  \n"
            f"**Type:** `{types}`  \n"
            f"**Generated:** {_now()}\n"
        )

    def _footer(self) -> str:
        return (
            "_Report generated by "
            "[cmipld](https://github.com/WCRP-CMIP/CMIP-LD) "
            "`cmipld.utils.similarity`_\n"
        )

    def _checklist(self, validated: FrozenSet[str], failed: FrozenSet[str]) -> str:
        lines = [
            "## ✏️ Reviewer Checklist\n",
            "_Pre-ticked fields passed Pydantic validation automatically._\n",
        ]
        non_meta = {k: v for k, v in self.item.items() if not is_default_skip(k)}
        if not non_meta:
            lines.append("_No content fields submitted._")
            return "\n".join(lines)

        passing     = {k: v for k, v in non_meta.items() if k in validated}
        failing     = {k: v for k, v in non_meta.items() if k in failed}
        unvalidated = {k: v for k, v in non_meta.items()
                       if k not in validated and k not in failed}

        if passing:
            lines.append("### Auto-validated\n")
            lines += [_checklist_row(k, v, True, False) for k, v in sorted(passing.items())]
            lines.append("")
        if failing:
            lines.append("### Requires attention\n")
            lines += [_checklist_row(k, v, True, True) for k, v in sorted(failing.items())]
            lines.append("")
        if unvalidated:
            lines.append("### Manual review\n")
            lines += [_checklist_row(k, v, False, False) for k, v in sorted(unvalidated.items())]
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # output
    # ------------------------------------------------------------------

    def write(self, path: str) -> str:
        """Write the report to *path* (builds first if not already done)."""
        if self._report is None:
            self.build()
        Path(path).write_text(self._report, encoding="utf-8")
        print(f"Report written → {path}")
        return path

    def __repr__(self):
        state = "built" if self._report else "not built"
        return f"ReportBuilder({self.folder_url!r}, kind={self.kind!r}, {state})"
