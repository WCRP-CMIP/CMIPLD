"""
LinkAnalyzer — extract external @id links from JSON-LD items and compare
them to every item in the folder.

    analyzer = LinkAnalyzer(loader)
    result   = analyzer.analyze(submitted_item)

    result.data          # dict: links, link_fields, pairs, ...
    result.md            # Markdown section string
    result.links         # set of external URI strings
    result.link_fields   # set of field names that carry links
    result.pairs         # [(other_id, overlap_pct), ...]
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Set, Tuple

from .graph_loader import GraphLoader, _find_contents_key, _short_id
from .pydantic_validator import short


# ---------------------------------------------------------------------------
# link extraction
# ---------------------------------------------------------------------------

def _rdflib_links(item: dict) -> Set[str]:
    try:
        import rdflib
        g = rdflib.Graph()
        g.parse(data=json.dumps(item), format="json-ld")
        return {str(o) for _, _, o in g if isinstance(o, rdflib.URIRef)}
    except Exception:
        return set()


def _walk_links(obj: Any) -> Set[str]:
    if isinstance(obj, dict):
        out = set()
        for k, v in obj.items():
            if k == "@id" and isinstance(v, str):
                out.add(v)
            else:
                out |= _walk_links(v)
        return out
    if isinstance(obj, list):
        return {l for elem in obj for l in _walk_links(elem)}
    return set()


def extract_links(item: dict) -> Set[str]:
    """
    Return all external URI references from a JSON-LD item.

    Handles both forms found in expanded folder items:
    - Dict form:   {"grid_type": {"@id": "https://...constants/grid_type/triangular"}}
    - String form: {"grid_type": "https://...constants/grid_type/triangular"}
    """
    own = item.get("@id", "")

    # Try rdflib first (catches everything in valid JSON-LD)
    links = _rdflib_links(item)

    if not links:
        # Walk @id dict refs
        links = _walk_links(item)
        # Also catch plain URI string values (expanded folder items use these)
        for k, v in item.items():
            if k.startswith("@"):
                continue
            if isinstance(v, str) and v.startswith("http") and v != own:
                links.add(v)
            elif isinstance(v, list):
                for elem in v:
                    if isinstance(elem, str) and elem.startswith("http") and elem != own:
                        links.add(elem)

    links.discard(own)
    # Discard type/context URIs — only keep leaf value URIs (3+ path segments)
    links = {u for u in links if len([p for p in u.replace("https://", "").split("/") if p]) >= 3}
    return links


def _link_fields(item: dict) -> Set[str]:
    """Top-level field names whose values carry @id references."""
    return {k for k, v in item.items() if not k.startswith("@") and _walk_links(v)}


def _jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    union = len(a | b)
    return len(a & b) / union if union else 0.0


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------

class LinkResult:
    """
    Returned by ``LinkAnalyzer.analyze()``.

    Attributes
    ----------
    target_id   : short id of the submitted item
    links       : external URI references found in the item
    link_fields : top-level field names that carry those links
    pairs       : [(other_id, overlap_pct), ...] sorted descending
    """

    def __init__(self, target_id, links, link_fields, pairs, total_folder_items):
        self.target_id         = target_id
        self.links             = links
        self.link_fields       = link_fields
        self.pairs             = pairs
        self.total_folder_items = total_folder_items

    @property
    def data(self) -> dict:
        return {
            "target_id":          self.target_id,
            "links":              sorted(self.links),
            "link_fields":        sorted(short(f) for f in self.link_fields),
            "pairs":              self.pairs,
            "total_folder_items": self.total_folder_items,
        }

    @property
    def md(self) -> str:
        lines = [
            "## 🔗 Link Similarity\n",
            f"**Item:** `{self.target_id}` — "
            f"{len(self.links)} external links across {len(self.link_fields)} fields\n",
        ]
        if self.links:
            lines += ["### Links\n"] + [f"- `{l}`" for l in sorted(self.links)] + [""]
            lines += ["### Link-carrying fields\n"] + \
                     [f"- `{short(f)}`" for f in sorted(self.link_fields)] + [""]
        if self.pairs:
            lines += [
                "### Overlap with folder items\n",
                "| Item | Shared/Submitted | Link % |",
                "|------|-----------------|--------|",
            ]
            for oid, pct, n_shared, n_submitted in self.pairs:
                bar = "█" * int(pct / 10) + "░" * (10 - int(pct / 10))
                lines.append(f"| `{oid}` | {n_shared}/{n_submitted} | {pct:.1f}% `{bar}` |")
        else:
            lines.append("_No link overlap found with existing folder items._")
        return "\n".join(lines)

    def __repr__(self):
        top = self.pairs[0] if self.pairs else None
        top_str = f", closest={top[0]} {top[1]:.0f}%" if top else ""
        return f"LinkResult({self.target_id!r}, {len(self.links)} links{top_str})"


# ---------------------------------------------------------------------------
# LinkAnalyzer
# ---------------------------------------------------------------------------

class LinkAnalyzer:
    """
    Compare a submitted item's external links against every folder item.

    Parameters
    ----------
    loader : GraphLoader
        Loaded graph for the folder being submitted into.
    """

    def __init__(self, loader: GraphLoader):
        self._folder_links: Dict[str, Set[str]] = {
            _short_id(item.get("@id", f"item_{i}")): extract_links(item)
            for i, item in enumerate(loader.items)
            if not _short_id(item.get("@id", "")).startswith("_")
        }

    def analyze(self, item: dict) -> LinkResult:
        """
        Extract links from *item* and compare against the folder.

        Returns a :class:`LinkResult` with ``.data`` and ``.md`` properties.
        """
        target_id = _short_id(item.get("@id", "submitted"))
        links     = extract_links(item)
        lfields   = _link_fields(item)

        n_submitted = len(links)

        pairs: List[Tuple[str, float, int, int]] = sorted(
            (
                (
                    oid,
                    round(len(links & other) / n_submitted * 100, 1) if n_submitted else 0.0,
                    len(links & other),   # n_shared
                    n_submitted,          # denominator = submission link count
                )
                for oid, other in self._folder_links.items()
                if oid != target_id
            ),
            key=lambda x: x[1],
            reverse=True,
        )

        return LinkResult(target_id, links, lfields, pairs, len(self._folder_links))
