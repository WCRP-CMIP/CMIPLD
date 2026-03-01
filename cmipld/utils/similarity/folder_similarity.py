"""
cmipld.utils.similarity.folder_similarity
==========================================
Generate a self-contained Similarity.html adjacency-matrix page.

New in this version
-------------------
- Full display names via validation_key field (e.g. "MPI-ESM" not "mpi-esm")
- filter_field parameter: extracts per-item tags and renders client-side
  filter buttons in the HTML (e.g. filter by scientific_domain)
- x-axis labels rotated 90° with up to 50-char truncation
- Diagonal labels sized to fit within their cell
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any


# ---------------------------------------------------------------------------
# Helpers for extracting fields from expanded JSON-LD items
# ---------------------------------------------------------------------------

def _get_field_value(item: dict, field_suffix: str) -> Optional[str]:
    """Return the scalar value of the first key whose last URL segment
    matches *field_suffix*.  Handles {'@value': ...}, {'@id': ...}, str."""
    for k, v in item.items():
        if k.split('/')[-1] != field_suffix and k != field_suffix:
            continue
        if isinstance(v, dict):
            return v.get('@value') or (v.get('@id', '').split('/')[-1] or None)
        if isinstance(v, list) and v:
            first = v[0]
            if isinstance(first, dict):
                return first.get('@value') or (first.get('@id', '').split('/')[-1] or None)
            return str(first)
        if isinstance(v, str):
            return v
    return None


def _get_tags(item: dict, field_suffix: str) -> List[str]:
    """Return ALL tag values for *field_suffix*, supporting list-valued fields."""
    tags: List[str] = []
    for k, v in item.items():
        if k.split('/')[-1] != field_suffix and k != field_suffix:
            continue
        if isinstance(v, dict):
            val = v.get('@value') or v.get('@id', '').split('/')[-1]
            if val:
                tags.append(str(val))
        elif isinstance(v, list):
            for entry in v:
                if isinstance(entry, dict):
                    val = entry.get('@value') or entry.get('@id', '').split('/')[-1]
                    if val:
                        tags.append(str(val))
                elif isinstance(entry, str):
                    tags.append(entry)
        elif isinstance(v, str):
            tags.append(v)
    return tags


def _get_label(item: dict) -> str:
    """Best display name: validation_key → @id stem."""
    vk = _get_field_value(item, 'validation_key')
    if vk and vk.strip():
        return vk.strip()
    raw = item.get('@id', '')
    return raw.split('/')[-1].split(':')[-1] or 'unknown'


# ---------------------------------------------------------------------------
# D3 HTML template
# ---------------------------------------------------------------------------
_D3_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Source+Code+Pro:wght@400;600;700&display=swap" rel="stylesheet">
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Source Code Pro', monospace; background: #ffffff;
    display: flex; flex-direction: column; align-items: center;
    padding: 24px 24px 40px;
  }
  #filter-bar {
    display: flex; flex-wrap: wrap; gap: 6px; justify-content: center;
    margin-bottom: 16px; min-height: 0;
  }
  .fbtn {
    padding: 4px 11px; border-radius: 20px; border: 1.5px solid #ccc;
    background: #fff; cursor: pointer; font-family: 'Source Code Pro', monospace;
    font-size: 11px; color: #555; transition: all .15s;
  }
  .fbtn:hover  { border-color: #0d1035; color: #0d1035; }
  .fbtn.active { background: #0d1035; border-color: #0d1035; color: #fff; font-weight: 600; }
  #chart { position: relative; }
  .tip {
    position: fixed; background: #0d1035; color: #fff;
    padding: 10px 14px; border-radius: 8px; font-size: 12px;
    font-family: 'Source Code Pro', monospace; pointer-events: none;
    opacity: 0; transition: opacity .12s; line-height: 1.9;
    box-shadow: 0 6px 24px rgba(0,0,0,.25); max-width: 280px;
  }
  .tip .tip-link { color: #e8607e; font-weight: 600; }
  .tip .tip-text { color: #f5c842; font-weight: 600; }
  .tip .tip-head { font-weight: 700; font-size: 13px;
                   border-bottom: 1px solid rgba(255,255,255,.2);
                   padding-bottom: 5px; margin-bottom: 5px; }
</style>
</head>
<body>
<div id="filter-bar"></div>
<div id="chart"></div>
<div class="tip" id="tip"></div>
<script>
const D = __DATA__;
const { ids, link, text, method, folder, meta } = D;

const n       = ids.length;
const FONT    = "'Source Code Pro', monospace";
const RED     = '#a40e4C';
const MUSTARD = '#f2b30d';
const NAVY    = '#0d1035';
const WHITE   = '#ffffff';

// ── Layout ────────────────────────────────────────────────────────────────
const cellSize = Math.min(60, Math.floor(Math.min(window.innerWidth * 0.72, 480) / n));
const gap      = Math.max(2, Math.round(cellSize * 0.055));
const inner    = cellSize - gap;
const radius   = Math.round(inner * 0.14);

// x-axis height: rotated labels, max 50 chars, monospace ~0.61 * fontSize px wide
const lblFs   = Math.max(8, Math.round(cellSize * 0.145));
const maxLLen = Math.max(...meta.map(m => Math.min(m.label.length, 50)));
// x-axis: rotated labels need XLBL_H vertical space (text length × char width)
const XLBL_H  = Math.ceil(maxLLen * lblFs * 0.62) + 12;
// y-axis: horizontal labels, left margin = longest label × char width
const YLBL_W  = Math.ceil(maxLLen * lblFs * 0.62) + 16;
const LEG_H   = 62;
const TITLE_H = 54;
const margin  = {
  top:    TITLE_H,
  right:  20,
  bottom: XLBL_H + LEG_H + 16,
  left:   YLBL_W,
};
const W = n * cellSize + margin.left + margin.right;
const H = n * cellSize + margin.top  + margin.bottom;

// ── Colour helpers ─────────────────────────────────────────────────────────
function hexToRgb(h) {
  return [parseInt(h.slice(1,3),16)/255, parseInt(h.slice(3,5),16)/255, parseInt(h.slice(5,7),16)/255];
}
function blend(hex, a) {
  const [r,g,b] = hexToRgb(hex);
  return `rgb(${Math.round((1-a+r*a)*255)},${Math.round((1-a+g*a)*255)},${Math.round((1-a+b*a)*255)})`;
}

// ── Filter ─────────────────────────────────────────────────────────────────
// Collect all unique tags across items
const allTags = [...new Set(meta.flatMap(m => m.tags || []))].sort();
let activeFilter = null;

function itemVisible(i) {
  if (!activeFilter) return true;
  return (meta[i].tags || []).includes(activeFilter);
}

function applyFilter() {
  // Cells
  g.selectAll('.cell').attr('opacity', d => {
    if (d.i === d.j) return itemVisible(d.i) ? 1 : 0.08;
    return (itemVisible(d.i) && itemVisible(d.j)) ? 1 : 0.06;
  });
  // Value labels
  g.selectAll('.val').attr('opacity', d =>
    (itemVisible(d.i) && itemVisible(d.j)) ? 1 : 0);
  // Diagonal labels
  g.selectAll('.diag').attr('opacity', (d, i) => itemVisible(i) ? 1 : 0.1);
  // Axis labels
  g.selectAll('.xlabel').attr('opacity', (d, i) => itemVisible(i) ? 1 : 0.1);
  g.selectAll('.ylabel').attr('opacity', (d, i) => itemVisible(i) ? 1 : 0.1);
}

// Build filter buttons (only if there are tags)
if (allTags.length > 0) {
  const bar = document.getElementById('filter-bar');
  const allBtn = document.createElement('button');
  allBtn.className = 'fbtn active';
  allBtn.textContent = 'All';
  allBtn.onclick = () => {
    activeFilter = null;
    document.querySelectorAll('.fbtn').forEach(b => b.classList.remove('active'));
    allBtn.classList.add('active');
    applyFilter();
  };
  bar.appendChild(allBtn);

  allTags.forEach(tag => {
    const btn = document.createElement('button');
    btn.className = 'fbtn';
    btn.textContent = tag.replace(/-/g,' ').replace(/_/g,' ');
    btn.dataset.tag = tag;
    btn.onclick = () => {
      activeFilter = tag;
      document.querySelectorAll('.fbtn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      applyFilter();
    };
    bar.appendChild(btn);
  });
}

// ── SVG ────────────────────────────────────────────────────────────────────
const svg = d3.select('#chart').append('svg').attr('width', W).attr('height', H);
const defs = svg.append('defs');
[['leg-red', RED], ['leg-mustard', MUSTARD]].forEach(([id, col]) => {
  const gr = defs.append('linearGradient').attr('id', id).attr('x1','0%').attr('x2','100%');
  gr.append('stop').attr('offset','0%').attr('stop-color', WHITE);
  gr.append('stop').attr('offset','100%').attr('stop-color', col);
});

// Title
svg.append('text').attr('x', W/2).attr('y', 24)
  .attr('text-anchor','middle').attr('font-family', FONT)
  .attr('font-size', 17).attr('font-weight', 700).attr('fill', NAVY)
  .text('Similarity Matrix — ' + folder);
svg.append('text').attr('x', W/2).attr('y', 41)
  .attr('text-anchor','middle').attr('font-family', FONT)
  .attr('font-size', 9).attr('fill','#999')
  .text(n + ' items  ·  spectrally ordered  ·  ' + method);

const g   = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
const tip = d3.select('#tip');

// ── Cells ──────────────────────────────────────────────────────────────────
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
    const lbl_i = meta[d.i].label, lbl_j = meta[d.j].label;
    tip.style('opacity',1).html(
      `<div class="tip-head">${lbl_i} ↔ ${lbl_j}</div>` +
      `<span class="tip-link">▲ Link</span>&nbsp; ${(link[li][lj]*100).toFixed(1)}%<br>` +
      `<span class="tip-text">▼ Content</span>&nbsp; ${(text[lj][li]*100).toFixed(1)}%`
    );
    d3.select(this).attr('stroke',NAVY).attr('stroke-width',2);
    g.selectAll('.cell').filter(e => e.i!==d.i && e.j!==d.j).attr('opacity', e =>
      (itemVisible(e.i) && itemVisible(e.j)) ? 0.35 : 0.04);
  })
  .on('mousemove', ev => tip.style('left',(ev.clientX+14)+'px').style('top',(ev.clientY-10)+'px'))
  .on('mouseout', function() {
    tip.style('opacity',0);
    d3.select(this).attr('stroke','none');
    applyFilter();
  });

// ── Value labels ───────────────────────────────────────────────────────────
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

// ── Diagonal labels (sized to fit within cell, truncated if needed) ─────────
// monospace char width ≈ 0.58 * fontSize → max chars at size fs = inner / (0.58 * fs)
const maxDiagFs = Math.max(9, Math.round(cellSize * 0.18));

function diagText(label) {
  // Find the largest font size that fits, down to min 6px
  for (var fs = maxDiagFs; fs >= 6; fs--) {
    var maxChars = Math.floor(inner / (0.58 * fs));
    if (label.length <= maxChars) return { fs: fs, text: label };
  }
  // Even at 6px it's too long — truncate to fit
  var maxChars = Math.floor(inner / (0.58 * 6));
  return { fs: 6, text: label.slice(0, Math.max(1, maxChars - 1)) + '…' };
}

g.selectAll('.diag').data(meta).join('text')
  .attr('class','diag')
  .attr('x', (d,i) => i*cellSize + cellSize/2)
  .attr('y', (d,i) => i*cellSize + cellSize/2)
  .attr('dy','0.35em').attr('text-anchor','middle')
  .attr('font-family', FONT)
  .attr('font-size', d => diagText(d.label).fs)
  .attr('font-weight',700).attr('fill',WHITE).attr('pointer-events','none')
  .text(d => diagText(d.label).text);

// ── Axis labels ────────────────────────────────────────────────────────────
// X-axis: rotated -90°, truncated to 50 chars, reads bottom→top
const pivotY = n * cellSize + 4;   // just below the matrix

g.selectAll('.xlabel').data(meta).join('text')
  .attr('class','xlabel')
  .attr('transform', (d, i) =>
    `translate(${i*cellSize + cellSize/2},${pivotY}) rotate(-90)`)
  .attr('text-anchor','end')
  .attr('dy','0.35em')
  .attr('font-family', FONT)
  .attr('font-size', lblFs)
  .attr('font-weight', 600)
  .attr('fill', NAVY)
  .text(d => d.label.length > 50 ? d.label.slice(0, 50) + '…' : d.label);

// Y-axis: horizontal labels, truncated to 50 chars
g.selectAll('.ylabel').data(meta).join('text')
  .attr('class','ylabel')
  .attr('x', -8)   // 8px gap from left edge of matrix
  .attr('y', (d, i) => i*cellSize + cellSize/2)
  .attr('text-anchor','end').attr('dominant-baseline','middle')
  .attr('font-family', FONT)
  .attr('font-size', lblFs)
  .attr('font-weight', 600)
  .attr('fill', NAVY)
  .text(d => d.label.length > 50 ? d.label.slice(0, 50) + '…' : d.label);

// ── Diagonal divider ───────────────────────────────────────────────────────
g.append('line')
  .attr('x1',0).attr('y1',0).attr('x2',n*cellSize).attr('y2',n*cellSize)
  .attr('stroke',NAVY).attr('stroke-width',1.5)
  .attr('stroke-dasharray','5,4').attr('opacity',0.22);

// ── Legend bars ────────────────────────────────────────────────────────────
const legY  = n*cellSize + XLBL_H + 16;
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
  .attr('x', n*cellSize/2).attr('y', legY+barH+30)
  .attr('text-anchor','middle').attr('font-size', 9)
  .attr('font-family', FONT).attr('fill','#ccc')
  .text('hover any cell for details · click filter buttons to highlight groups');
</script>
</body></html>"""


# ---------------------------------------------------------------------------
# Dependency helper
# ---------------------------------------------------------------------------

def _pip_install(*packages: str, upgrade: bool = False) -> bool:
    """Attempt a silent pip install. Returns True on success."""
    import os
    if os.environ.get('CI'):
        return False   # CI must pre-install; don't attempt runtime pip
    cmd = [sys.executable, "-m", "pip", "install", "-q"] + list(packages)
    if upgrade:
        cmd.append("--upgrade")
    try:
        subprocess.check_call(cmd,
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _ensure_numpy():
    try:
        import numpy  # noqa: F401
    except ImportError:
        import os
        if os.environ.get('CI'):
            raise ImportError(
                "numpy is required for similarity charts. "
                "Add 'numpy>=1.24.0' to requirements.txt."
            )
        print("  Installing numpy…", flush=True)
        _pip_install("numpy")


def _ensure_sentence_transformers():
    """Import sentence_transformers, installing if missing."""
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
        return True
    except (ImportError, Exception):
        pass
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "sentence-transformers", "-q"])
    from sentence_transformers import SentenceTransformer  # noqa: F401
    return True


# ---------------------------------------------------------------------------
# FolderSimilarity
# ---------------------------------------------------------------------------

class FolderSimilarity:
    """
    Build a Similarity.html adjacency-matrix for one cmipld folder.

    Parameters
    ----------
    endpoint : str
        cmipld endpoint name, e.g. ``"horizontal_computational_grid"``.
    items : list[dict] | None
        Pre-fetched items.  When None, fetched via cmipld.expand().
    label : str | None
        Chart title label.
    filter_field : str | None
        Field name (last URL segment) to extract per-item filter tags from,
        e.g. ``"scientific_domains"``.  Tags become interactive filter buttons
        in the HTML.  When None, no filter buttons are rendered.
    use_embeddings : bool
        Try sentence-transformer embeddings; falls back to field-level.
    min_items : int
        Minimum items needed to render (default 2).
    """

    OUTPUT_FILENAME = "Similarity.html"

    def __init__(
        self,
        endpoint: str,
        items: Optional[List[Dict[str, Any]]] = None,
        label: Optional[str] = None,
        filter_field: Optional[str] = None,
        use_embeddings: bool = True,
        min_items: int = 2,
    ):
        self.endpoint      = endpoint
        self._items        = items
        self.label         = label or endpoint
        self.filter_field  = filter_field
        self.use_embeddings = use_embeddings
        self.min_items     = min_items
        self._html: Optional[str] = None

    # ------------------------------------------------------------------

    def build(self) -> str:
        _ensure_numpy()
        import numpy as np

        from cmipld.utils.similarity import (
            extract_links, strip_text_fields, compute_field_similarity,
        )
        from cmipld.utils.similarity.link_analyzer import _jaccard

        # 1. Items
        items = self._items if self._items is not None else self._fetch()
        n = len(items)
        if n < self.min_items:
            raise ValueError(
                f"Only {n} item(s) in '{self.endpoint}'; "
                f"need at least {self.min_items}."
            )

        # 2. Labels (full names) and short IDs (for matrix keys)
        labels = [_get_label(item) for item in items]
        ids    = [
            (item.get('@id', '') or '').split('/')[-1].split(':')[-1]
            or f"item{i}"
            for i, item in enumerate(items)
        ]

        # 3. Filter tags
        if self.filter_field:
            tags_list = [_get_tags(item, self.filter_field) for item in items]
        else:
            tags_list = [[] for _ in items]

        # 4. Link matrix
        all_links = [extract_links(item) for item in items]
        link_raw  = np.array([
            [_jaccard(all_links[i], all_links[j]) if i != j else 0.0
             for j in range(n)]
            for i in range(n)
        ])
        off = link_raw[~np.eye(n, dtype=bool)]
        link_degenerate = (
            off.size == 0
            or float(off.std()) < 1e-6
            or float(off.mean()) > 0.98
        )
        if link_degenerate:
            print(
                f"  ⚠ Link matrix degenerate (mean={float(off.mean()):.0%}) "
                f"— using text for upper triangle.", flush=True
            )

        # 5. Text matrix
        text_items  = [strip_text_fields(item) for item in items]
        text_method = "field-level"
        if self.use_embeddings:
            _ensure_sentence_transformers()
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

        # 6. Resolve link
        if link_degenerate:
            link_matrix = text_matrix.copy()
            link_label  = "text (links uninformative)"
        else:
            link_matrix = link_raw
            link_label  = "jaccard"

        # 7. Spectral ordering
        A       = (link_matrix + text_matrix) / 2
        D_mat   = np.diag(A.sum(axis=1))
        L       = D_mat - A
        _, evecs = np.linalg.eigh(L)
        fiedler  = evecs[:, 1] if n > 2 else evecs[:, 0]
        order    = np.argsort(fiedler)

        ordered_ids    = [ids[i]       for i in order]
        ordered_labels = [labels[i]    for i in order]
        ordered_tags   = [tags_list[i] for i in order]
        Lo             = link_matrix[np.ix_(order, order)]
        To             = text_matrix[np.ix_(order, order)]

        # 8. Metadata array for D3
        meta = [
            {"label": ordered_labels[i], "tags": ordered_tags[i]}
            for i in range(n)
        ]

        # 9. Render
        payload = json.dumps({
            "ids":    ordered_ids,
            "link":   Lo.tolist(),
            "text":   To.tolist(),
            "method": f"{text_method} | link: {link_label}",
            "folder": self.label,
            "meta":   meta,
        })
        self._html = _D3_TEMPLATE.replace("__DATA__", payload)
        return self._html

    def save(self, path: str) -> Path:
        if self._html is None:
            self.build()
        dest = Path(path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(self._html, encoding="utf-8")
        return dest

    def save_next_to(self, directory: str) -> Path:
        return self.save(str(Path(directory) / self.OUTPUT_FILENAME))

    # ------------------------------------------------------------------

    def _fetch(self) -> List[Dict[str, Any]]:
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
        return (f"FolderSimilarity({self.endpoint!r}, "
                f"{len(self._items or [])} items, "
                f"{'built' if self._html else 'not built'})")
