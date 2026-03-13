"""
TextSimilarityAnalyzer — compare the remaining content fields of a submitted
item against every folder item using transformer embeddings.

    analyzer = TextSimilarityAnalyzer(loader, exclude=link_fields | validated_fields)
    result   = analyzer.analyze(submitted_item)

    result.data   # dict: text_fields, pairs, method
    result.md     # Markdown section string
    result.pairs  # [(other_id, score 0-1), ...]

Excluded automatically (no need to pass these):
  - @-prefixed metadata keys
  - Fields whose short name starts with ``drs`` or ``validation``
  - Link-carrying fields (values containing @id references)

Pass ``exclude`` to additionally drop pydantic-validated fields.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from .graph_loader import GraphLoader, _short_id
from .fingerprint import JSONSimilarityFingerprint
from .analysis import compute_field_similarity
from .pydantic_validator import DEFAULT_SKIP_PREFIXES, short


# ---------------------------------------------------------------------------
# field filtering
# ---------------------------------------------------------------------------

def _is_link(value: Any) -> bool:
    if isinstance(value, dict):
        return "@id" in value or any(_is_link(v) for v in value.values())
    if isinstance(value, list):
        return any(_is_link(v) for v in value)
    return False


def _always_skip(key: str) -> bool:
    if key.startswith("@"):
        return True
    return any(short(key).startswith(p) for p in DEFAULT_SKIP_PREFIXES)


def strip_text_fields(item: dict, exclude: Optional[Set[str]] = None) -> dict:
    """
    Return only the content-bearing text fields of *item*.

    Drops: ``@*`` keys, ``drs*``/``validation*`` short names, link-carrying
    fields, and anything in *exclude* (matched by full key or short name).
    """
    excl       = set(exclude or [])
    excl_short = {short(k) for k in excl}
    return {
        k: v for k, v in item.items()
        if not _always_skip(k)
        and k not in excl
        and short(k) not in excl_short
        and not _is_link(v)
    }


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

class SimilarityResult:
    """
    Returned by ``TextSimilarityAnalyzer.analyze()``.

    Attributes
    ----------
    target_id   : short id of the submitted item
    text_fields : dict of the fields actually compared
    pairs       : [(other_id, score 0-1), ...] sorted descending
    method      : ``"embedding"`` or ``"field-level"``
    """

    def __init__(self, target_id, text_fields, pairs, method):
        self.target_id   = target_id
        self.text_fields = text_fields
        self.pairs       = pairs
        self.method      = method

    @property
    def data(self) -> dict:
        return {
            "target_id":   self.target_id,
            "method":      self.method,
            "text_fields": {short(k): v for k, v in self.text_fields.items()},
            "pairs":       [(oid, round(s * 100, 1)) for oid, s in self.pairs],
        }

    @property
    def md(self) -> str:
        lines = [
            "## 📊 Text Similarity\n",
            f"**Item:** `{self.target_id}` — "
            f"{len(self.text_fields)} fields, method: {self.method}\n",
        ]
        if self.text_fields:
            lines += ["### Fields compared\n", "| Field | Value |", "|-------|-------|"]
            for k, v in sorted(self.text_fields.items(), key=lambda x: short(x[0])):
                dv = str(v)[:60] + ("…" if len(str(v)) > 60 else "")
                lines.append(f"| `{short(k)}` | {dv} |")
            lines.append("")
        else:
            lines.append("_No content fields remained after exclusions._\n")
            return "\n".join(lines)

        if self.pairs:
            lines += ["### Similarity to folder items\n",
                      "| Item | Score | Bar |",
                      "|------|-------|-----|"]
            for oid, score in self.pairs:
                pct = score * 100
                bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                lines.append(f"| `{oid}` | {pct:.1f}% | {bar} |")
            lines.append("")
        return "\n".join(lines)

    def __repr__(self):
        top = self.pairs[0] if self.pairs else None
        top_str = f", closest={top[0]} {top[1]*100:.0f}%" if top else ""
        return f"SimilarityResult({self.target_id!r}, {len(self.text_fields)} fields, {self.method}{top_str})"


# ---------------------------------------------------------------------------
# TextSimilarityAnalyzer
# ---------------------------------------------------------------------------

class TextSimilarityAnalyzer:
    """
    Compare the text fields of a submitted item against all folder items.

    Parameters
    ----------
    loader : GraphLoader
        Loaded folder graph.
    exclude : set[str] | None
        Additional field keys to exclude (link fields, pydantic-validated
        fields).  Default-skip fields are always removed regardless.
    model_name : str
        Sentence-transformer model (default ``all-MiniLM-L6-v2``).
    """

    def __init__(
        self,
        loader: GraphLoader,
        exclude: Optional[Set[str]] = None,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self._folder_items = loader.items
        self.exclude       = set(exclude or [])
        self.model_name    = model_name

    def analyze(self, item: dict, item_id: Optional[str] = None) -> SimilarityResult:
        """
        Compare *item* against every folder item.

        Returns a :class:`SimilarityResult` with ``.data`` and ``.md``.
        """
        target_id   = item_id or _short_id(item.get("@id", "submitted"))
        text_fields = strip_text_fields(item, exclude=self.exclude)

        corpus: Dict[str, dict] = {
            _short_id(fi.get("@id", f"item_{i}")): strip_text_fields(fi, exclude=self.exclude)
            for i, fi in enumerate(self._folder_items)
            if _short_id(fi.get("@id", "")) != target_id
        }

        pairs:  List[Tuple[str, float]] = []
        method = "embedding"

        if text_fields and corpus:
            data_dict = {target_id: text_fields, **corpus}
            fp = JSONSimilarityFingerprint(model_name=self.model_name, include_keys=False)
            fp.load_from_dict(data_dict)
            fp.embed(show_progress=False)
            fp.compute_similarity()
            idx = fp.file_paths.index(target_id)
            pairs = sorted(
                [
                    (fid, round(float(fp.similarity_matrix[idx][i]), 3))
                    for i, fid in enumerate(fp.file_paths)
                    if fid != target_id
                ],
                key=lambda x: x[1],
                reverse=True,
            )

        return SimilarityResult(target_id, text_fields, pairs, method)
