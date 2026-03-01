"""
cmipld.utils.similarity.folder_similarity
==========================================
Generate a self-contained ``001_Similarity.html`` adjacency-matrix page for
any cmipld folder that exposes a ``_graph.json`` endpoint.

Usage (standalone — fetches data itself)
-----------------------------------------
    from cmipld.utils.similarity.folder_similarity import FolderSimilarity

    fs = FolderSimilarity("horizontal_grid_cells")
    fs.save("/path/to/output/001_Similarity.html")

Usage (with pre-fetched items list)
-------------------------------------
    items = fetch_data("horizontal_grid_cells", depth=2)
    fs = FolderSimilarity("horizontal_grid_cells", items=items)
    fs.save("/docs/10_EMD_Repository/07_Horizontal_Grid_Cells/001_Similarity.html")

The class
----------
- auto-installs matplotlib/numpy if absent (silent pip)
- computes Jaccard link-similarity and transformer/field-level text-similarity
- applies spectral (Fiedler) ordering so similar items cluster on the diagonal
- upper triangle = link similarity (Red #a40e4C), lower = content (Mustard #f2b30d)
- outputs a fully self-contained HTML file (D3 v7, Source Code Pro, no server needed)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# Brand colours
# ---------------------------------------------------------------------------
RED     = "#a40e4C"
MUSTARD = "#f2b30d"
NAVY    = "#0d1035"
WHITE   = "#ffffff"


# ---------------------------------------------------------------------------
# Self-contained D3 HTML template
# ---------------------------------------------------------------------------
_D3_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: 'Source Code Pro', monospace; background: #ffffff;
         display: flex; flex-direction: column; align-items: center;
         padding: 24px 24px 40px; }
  #chart { position: relative; }
  .tip {
    position: fixed; background: #0d1035; color: #fff;
    padding: 10px 14px; border-radius: 8px; font-size: 12px;
    font-family: 'Source Code Pro', monospace; pointer-events: none;
    opacity: 0; transition: opacity .12s; line-height: 1.9;
    box-shadow: 0 6px 24px rgba(0,0,0,.25); max-width: 240px;
  }
  .tip .tip-link { color: #e8607e; font-weight: 600; }
  .tip .tip-text { color: #f5c842; font-weight: 600; }
  .tip .tip-head { font-weight: 700; font-size: 13px;
                   border-bottom: 1px solid rgba(255,255,255,.2);
                   padding-bottom: 5px; margin-bottom: 5px; }
</style>
</head>
<body>
<div id="chart"></div>
<div class="tip" id="tip"></div>
<script>
const D = __DATA__;
const { ids, link, text, method, folder } = D;

const n = ids.length;
const cellSize = Math.min(60, Math.floor(Math.min(window.innerWidth * 0.72, 480) / n));
const gap      = Math.max(2, Math.round(cellSize * 0.055));
const inner    = cellSize - gap;
const radius   = Math.round(inner * 0.14);
const FONT     = "'Source Code Pro', monospace";

const TITLE_H = 54;
const XLBL_H  = Math.round(cellSize * 0.55);
const LEG_H   = 58;
const margin  = { top: TITLE_H, right: 20,
                  bottom: XLBL_H + LEG_H + 24,
                  left: Math.round(cellSize * 0.88) };

const W = n * cellSize + margin.left + margin.right;
const H = n * cellSize + margin.top  + margin.bottom;

const RED     = '#a40e4C';
const MUSTARD = '#f2b30d';
const NAVY    = '#0d1035';
const WHITE   = '#ffffff';

function hexToRgb(h) {
  return [parseInt(h.slice(1,3),16)/255, parseInt(h.slice(3,5),16)/255, parseInt(h.slice(5,7),16)/255];
}
function blend(hex, a) {
  const [r,g,b] = hexToRgb(hex);
  return `rgb(${Math.round((1-a+r*a)*255)},${Math.round((1-a+g*a)*255)},${Math.round((1-a+b*a)*255)})`;
}

const svg = d3.select('#chart').append('svg').attr('width', W).attr('height', H);
const defs = svg.append('defs');
[['leg-red', RED], ['leg-mustard', MUSTARD]].forEach(([id, col]) => {
  const gr = defs.append('linearGradient').attr('id', id).attr('x1','0%').attr('x2','100%');
  gr.append('stop').attr('offset','0%').attr('stop-color', WHITE);
  gr.append('stop').attr('offset','100%').attr('stop-color', col);
});

// Title
svg.append('text')
  .attr('x', W/2).attr('y', 24)
  .attr('text-anchor','middle').attr('font-family', FONT)
  .attr('font-size', 17).attr('font-weight', 700).attr('fill', NAVY)
  .text('Similarity Matrix — ' + folder);
svg.append('text')
  .attr('x', W/2).attr('y', 41)
  .attr('text-anchor','middle').attr('font-family', FONT)
  .attr('font-size', 9).attr('fill','#999')
  .text(n + ' items  ·  spectrally ordered  ·  text: ' + method);

const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
const tip = d3.select('#tip');

// Cells
const cellData = [];
for (let i=0;i<n;i++) for (let j=0;j<n;j++) cellData.push({i,j});

g.selectAll('.cell').data(cellData).join('rect')
  .attr('class','cell')
  .attr('x',      d => d.j*cellSize + gap/2)
  .attr('y',      d => d.i*cellSize + gap/2)
  .attr('width',  inner).attr('height', inner).attr('rx', radius)
  .attr('fill', d => {
    if (d.i===d.j) return NAVY;
    return d.i < d.j ? blend(RED, link[d.i][d.j]) : blend(MUSTARD, text[d.i][d.j]);
  })
  .style('cursor', d => d.i===d.j ? 'default' : 'pointer')
  .on('mouseover', function(event, d) {
    if (d.i===d.j) return;
    const li=Math.min(d.i,d.j), lj=Math.max(d.i,d.j);
    tip.style('opacity',1).html(
      `<div class="tip-head">${ids[d.i]} ↔ ${ids[d.j]}</div>` +
      `<span class="tip-link">▲ Link</span>&nbsp; ${(link[li][lj]*100).toFixed(1)}%<br>` +
      `<span class="tip-text">▼ Content</span>&nbsp; ${(text[lj][li]*100).toFixed(1)}%`
    );
    d3.select(this).attr('stroke',NAVY).attr('stroke-width',2);
    g.selectAll('.cell').filter(e => e.i!==d.i && e.j!==d.j).attr('opacity',0.35);
  })
  .on('mousemove', ev => tip.style('left',(ev.clientX+14)+'px').style('top',(ev.clientY-10)+'px'))
  .on('mouseout', function() {
    tip.style('opacity',0);
    d3.select(this).attr('stroke','none');
    g.selectAll('.cell').attr('opacity',1);
  });

// Value labels
g.selectAll('.val').data(cellData.filter(d=>d.i!==d.j)).join('text')
  .attr('class','val')
  .attr('x', d => d.j*cellSize + cellSize/2)
  .attr('y', d => d.i*cellSize + cellSize/2)
  .attr('dy','0.35em').attr('text-anchor','middle')
  .attr('font-family', FONT)
  .attr('font-size', Math.max(8, Math.round(cellSize*0.16)))
  .attr('font-weight',600).attr('pointer-events','none')
  .attr('fill', d => {
    const v = d.i<d.j ? link[d.i][d.j] : text[d.i][d.j];
    if (v<0.08) return 'none';
    const [r,gg,b] = hexToRgb(d.i<d.j ? RED : MUSTARD);
    return (0.299*(1-v+r*v) + 0.587*(1-v+gg*v) + 0.114*(1-v+b*v)) < 0.55 ? WHITE : NAVY;
  })
  .text(d => { const v=d.i<d.j?link[d.i][d.j]:text[d.i][d.j]; return v>=0.08?Math.round(v*100)+'%':''; });

// Diagonal labels
g.selectAll('.diag').data(ids).join('text')
  .attr('class','diag')
  .attr('x', (d,i) => i*cellSize+cellSize/2)
  .attr('y', (d,i) => i*cellSize+cellSize/2)
  .attr('dy','0.35em').attr('text-anchor','middle')
  .attr('font-family', FONT)
  .attr('font-size', Math.max(9, Math.round(cellSize*0.18)))
  .attr('font-weight',700).attr('fill',WHITE).attr('pointer-events','none')
  .text(d=>d);

// Axis labels
const lblFs = Math.max(10, Math.round(cellSize*0.17));

g.selectAll('.xlabel').data(ids).join('text')
  .attr('class','xlabel')
  .attr('x', (d,i) => i*cellSize+cellSize/2)
  .attr('y', n*cellSize + Math.round(cellSize*0.26))
  .attr('text-anchor','middle').attr('dominant-baseline','hanging')
  .attr('font-family', FONT).attr('font-size', lblFs)
  .attr('font-weight',600).attr('fill', NAVY)
  .text(d=>d);

g.selectAll('.ylabel').data(ids).join('text')
  .attr('class','ylabel')
  .attr('x', -Math.round(cellSize*0.16))
  .attr('y', (d,i) => i*cellSize+cellSize/2)
  .attr('text-anchor','end').attr('dominant-baseline','middle')
  .attr('font-family', FONT).attr('font-size', lblFs)
  .attr('font-weight',600).attr('fill', NAVY)
  .text(d=>d);

// Diagonal divider
g.append('line')
  .attr('x1',0).attr('y1',0).attr('x2',n*cellSize).attr('y2',n*cellSize)
  .attr('stroke',NAVY).attr('stroke-width',1.5)
  .attr('stroke-dasharray','5,4').attr('opacity',0.22);

// Legend bars
const legY  = n*cellSize + XLBL_H + 22;
const barW  = Math.floor(n*cellSize * 0.43);
const barH  = 13;
const legFs = Math.max(9, Math.round(cellSize * 0.16));

g.append('text').attr('x',0).attr('y', legY-8)
  .attr('text-anchor','start').attr('font-family', FONT)
  .attr('font-size', legFs).attr('font-weight',700).attr('fill', RED)
  .text('▲  link similarity');
g.append('rect').attr('x',0).attr('y', legY)
  .attr('width', barW).attr('height', barH).attr('rx',3).attr('fill','url(#leg-red)');
g.append('text').attr('x',0).attr('y', legY+barH+9)
  .attr('text-anchor','start').attr('font-size', legFs-1).attr('fill','#bbb').attr('font-family', FONT).text('0%');
g.append('text').attr('x', barW).attr('y', legY+barH+9)
  .attr('text-anchor','end').attr('font-size', legFs-1).attr('fill','#bbb').attr('font-family', FONT).text('100%');

const mustX = n*cellSize - barW;
g.append('text').attr('x', mustX).attr('y', legY-8)
  .attr('text-anchor','start').attr('font-family', FONT)
  .attr('font-size', legFs).attr('font-weight',700).attr('fill','#c49000')
  .text('▼  content similarity');
g.append('rect').attr('x', mustX).attr('y', legY)
  .attr('width', barW).attr('height', barH).attr('rx',3).attr('fill','url(#leg-mustard)');
g.append('text').attr('x', mustX).attr('y', legY+barH+9)
  .attr('text-anchor','start').attr('font-size', legFs-1).attr('fill','#bbb').attr('font-family', FONT).text('0%');
g.append('text').attr('x', mustX+barW).attr('y', legY+barH+9)
  .attr('text-anchor','end').attr('font-size', legFs-1).attr('fill','#bbb').attr('font-family', FONT).text('100%');

g.append('text')
  .attr('x', n*cellSize/2).attr('y', legY+barH+28)
  .attr('text-anchor','middle').attr('font-size', 9)
  .attr('font-family', FONT).attr('fill','#ccc')
  .text('hover any cell for details');
</script>
</body></html>"""


# ---------------------------------------------------------------------------
# Dependency helpers
# ---------------------------------------------------------------------------

def _ensure_numpy():
    try:
        import numpy  # noqa: F401
    except ImportError:
        print("  Installing numpy…", flush=True)
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "numpy", "-q"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )


# ---------------------------------------------------------------------------
# FolderSimilarity
# ---------------------------------------------------------------------------

class FolderSimilarity:
    """
    Build a ``001_Similarity.html`` adjacency-matrix visualisation for one
    cmipld folder.

    Parameters
    ----------
    endpoint : str
        Short endpoint name as used by the data_loader helpers, e.g.
        ``"horizontal_grid_cells"``, ``"model_component"``.
    items : list[dict] | None
        Pre-fetched list of item dicts (from ``fetch_data()``).  When *None*
        the class calls ``fetch_data(endpoint)`` itself.
    label : str | None
        Human-readable folder label for the chart title.  Defaults to
        ``endpoint``.
    use_embeddings : bool
        Attempt sentence-transformer embeddings; falls back silently to
        field-level comparison on failure (default True).
    min_items : int
        Minimum items required to render a chart (default 2).
    """

    OUTPUT_FILENAME = "Similarity.html"

    def __init__(
        self,
        endpoint: str,
        items: Optional[List[Dict[str, Any]]] = None,
        label: Optional[str] = None,
        use_embeddings: bool = True,
        min_items: int = 2,
    ):
        self.endpoint      = endpoint
        self._items        = items          # None → fetch lazily in build()
        self.label         = label or endpoint
        self.use_embeddings = use_embeddings
        self.min_items     = min_items
        self._html: Optional[str] = None

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def build(self) -> str:
        """Compute matrices, apply spectral ordering, render and return HTML."""
        _ensure_numpy()
        import numpy as np

        from cmipld.utils.similarity import (
            extract_links, strip_text_fields, compute_field_similarity, short,
        )
        from cmipld.utils.similarity.link_analyzer import _jaccard

        # ── 1. Resolve items ──────────────────────────────────────────
        items = self._items
        if items is None:
            items = self._fetch()

        n = len(items)
        if n < self.min_items:
            raise ValueError(
                f"Only {n} item(s) in '{self.endpoint}'; "
                f"need at least {self.min_items} to build a similarity chart."
            )

        # ── 2. Extract IDs ────────────────────────────────────────────
        ids = []
        for item in items:
            raw_id = (
                item.get("@id") or
                item.get("validation_key") or
                item.get("id") or
                ""
            )
            ids.append(raw_id.split("/")[-1].split(":")[-1] or f"item{len(ids)}")

        # ── 3. Link matrix ────────────────────────────────────────────
        all_links   = [extract_links(item) for item in items]
        link_raw = np.array([
            [_jaccard(all_links[i], all_links[j]) if i != j else 0.0
             for j in range(n)]
            for i in range(n)
        ])
        # Detect degenerate link matrix: all off-diagonal values are identical
        # (typically all 1.0 when items share the same CV references, or all 0.0
        # when extract_links finds no @id refs). In either case the matrix carries
        # no discriminating information — fall back to text for the link triangle.
        off = link_raw[~np.eye(n, dtype=bool)]
        link_degenerate = (
            off.size == 0
            or float(off.std()) < 1e-6         # all same value
            or float(off.mean()) > 0.98         # all near 100%
        )
        if link_degenerate:
            print(
                f"  ⚠ Link matrix degenerate (mean={float(off.mean()):.0%}, "
                f"std={float(off.std()):.4f}) — using text similarity for "
                f"upper triangle too.",
                flush=True,
            )
        link_matrix = np.zeros_like(link_raw)   # placeholder; filled below

        # ── 4. Text matrix ────────────────────────────────────────────
        text_items  = [strip_text_fields(item) for item in items]
        text_method = "field-level"

        if self.use_embeddings:
            try:
                from cmipld.utils.similarity import JSONSimilarityFingerprint
                fp = JSONSimilarityFingerprint(include_keys=False)
                fp.load_from_dict({iid: ti for iid, ti in zip(ids, text_items)})
                fp.embed(show_progress=False)
                fp.compute_similarity()
                text_matrix = np.array(fp.similarity_matrix, dtype=float)
                np.fill_diagonal(text_matrix, 0.0)
                text_method = "embedding (all-MiniLM-L6-v2)"
            except Exception as exc:
                print(f"  ⚠ Embeddings unavailable ({exc}), using field-level.", flush=True)
                text_matrix = self._field_matrix(text_items, n, compute_field_similarity)
        else:
            text_matrix = self._field_matrix(text_items, n, compute_field_similarity)

        # ── 5. Resolve link matrix ───────────────────────────────────
        # Use real link values when informative; mirror text otherwise.
        if link_degenerate:
            link_matrix = text_matrix.copy()   # upper triangle = text too
            link_label  = "text (links uninformative)"
        else:
            link_matrix = link_raw
            link_label  = "jaccard"

        # ── 6. Spectral ordering ──────────────────────────────────────
        A       = (link_matrix + text_matrix) / 2
        D       = np.diag(A.sum(axis=1))
        L       = D - A
        _, evecs = np.linalg.eigh(L)
        fiedler  = evecs[:, 1] if n > 2 else evecs[:, 0]
        order    = np.argsort(fiedler)

        ordered_ids = [ids[i]  for i in order]
        Lo          = link_matrix[np.ix_(order, order)]
        To          = text_matrix[np.ix_(order, order)]

        # ── 7. Render ─────────────────────────────────────────────────
        payload = json.dumps({
            "ids":    ordered_ids,
            "link":   Lo.tolist(),
            "text":   To.tolist(),
            "method": text_method + f" | link: {link_label}",
            "folder": self.label,
        })
        self._html = _D3_TEMPLATE.replace("__DATA__", payload)
        return self._html

    def save(self, path: str) -> Path:
        """Write HTML to *path* (builds first if needed). Creates parent dirs."""
        if self._html is None:
            self.build()
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(self._html, encoding="utf-8")
        return dest

    def save_next_to(self, directory: str) -> Path:
        """Save as ``001_Similarity.html`` inside *directory*."""
        return self.save(str(Path(directory) / self.OUTPUT_FILENAME))

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _fetch(self) -> List[Dict[str, Any]]:
        """Fetch items via cmipld.expand (works on any branch)."""
        import cmipld
        url  = f"emd:{self.endpoint}/_graph.json"
        data = cmipld.expand(url, depth=2)
        ck   = next((k for k in data if "contents" in k.lower()), None)
        if not ck:
            return []
        raw = data[ck]
        return raw if isinstance(raw, list) else [raw]

    @staticmethod
    def _field_matrix(text_items, n, compute_fn):
        import numpy as np
        return np.array([
            [compute_fn(text_items[i], text_items[j])[0] if i != j else 0.0
             for j in range(n)]
            for i in range(n)
        ])

    def __repr__(self):
        state = "built" if self._html else "not built"
        return f"FolderSimilarity({self.endpoint!r}, {len(self._items or [])} items, {state})"
