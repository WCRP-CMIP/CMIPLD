"""
GraphLoader — fetch and parse a folder's _graph JSON-LD file.

    loader = GraphLoader("emd:horizontal_grid_cells", graph_data=raw_dict)

    loader.items                    # list of item dicts
    loader.to_data_dict()           # {short_id: item}
    loader.get("g100")              # single item by id
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional


def _short_id(full_id: str) -> str:
    return full_id.split("/")[-1] if "/" in full_id else full_id


def _find_contents_key(data: dict) -> Optional[str]:
    for k in data:
        if "contents" in k.lower():
            return k
    return None


class GraphLoader:
    """
    Load all entries from a folder's _graph JSON-LD file.

    Parameters
    ----------
    folder_url : str
        Prefixed URL, e.g. ``"emd:horizontal_grid_cells"``.
    graph_data : dict | None
        Pass an already-fetched dict (e.g. from ``cmipld.expand()``) to skip
        the network call entirely.
    graph_suffix : str
        Appended to *folder_url* when fetching (default ``_graph.jsonld``).
    depth : int
        Expansion depth for ``cmipld.get()`` (default 2, ignored when
        *graph_data* is supplied).
    """

    def __init__(
        self,
        folder_url: str,
        graph_data: Optional[dict] = None,
        graph_suffix: str = "_graph.jsonld",
        depth: int = 2,
        _empty: bool = False,
    ):
        self.folder_url   = folder_url.rstrip("/")
        self.graph_suffix = graph_suffix
        self.depth        = depth

        self.raw: dict = {}
        self.items: List[dict] = []

        if _empty:
            pass  # leave items empty — graph unavailable
        elif graph_data is not None:
            self._ingest(graph_data)
        else:
            self._fetch()

    # ------------------------------------------------------------------
    # loading
    # ------------------------------------------------------------------

    def _fetch(self):
        import cmipld
        url = f"{self.folder_url}/{self.graph_suffix}"
        self._ingest(cmipld.get(url, depth=self.depth))

    def _ingest(self, data: dict):
        self.raw = data
        if not data:
            self.items = []  # empty dict means no items available
            return
        key = _find_contents_key(data)
        if key is None:
            self.items = [data]
        else:
            contents = data[key]
            self.items = contents if isinstance(contents, list) else [contents]

    # ------------------------------------------------------------------
    # access
    # ------------------------------------------------------------------

    def get(self, item_id: str) -> Optional[dict]:
        """Return an item by short or full ``@id``."""
        for item in self.items:
            full = item.get("@id", "")
            if full == item_id or _short_id(full) == item_id:
                return item
        return None

    def to_data_dict(self) -> Dict[str, dict]:
        """Return ``{short_id: item}`` mapping."""
        out: Dict[str, dict] = {}
        for i, item in enumerate(self.items):
            key = _short_id(item.get("@id", f"item_{i}"))
            out[key] = item
        return out

    def __repr__(self):
        ids = [_short_id(i.get("@id", "?")) for i in self.items]
        return f"GraphLoader({self.folder_url!r}, {len(self.items)} items: {ids})"
