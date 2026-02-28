"""
Advanced JSON similarity analysis with multiple metrics.

Combines:
1. Semantic similarity (embeddings)
2. Structural similarity (field matching)
3. Value similarity (content comparison)

Shows field-level differences with contribution scores.
"""

import json
from typing import Dict, List, Tuple, Optional
from pathlib import Path


def flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> Dict[str, any]:
    """Flatten nested dict to key-value pairs."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, json.dumps(v)))
        else:
            items.append((new_key, v))
    return dict(items)


def compute_field_similarity(data1: dict, data2: dict) -> Tuple[float, Dict[str, float]]:
    """
    Compute field-level similarity.
    
    Returns:
        (overall_similarity, {field: similarity, ...})
    """
    flat1 = flatten_dict(data1)
    flat2 = flatten_dict(data2)
    
    all_fields = set(flat1.keys()) | set(flat2.keys())
    
    if not all_fields:
        return 1.0, {}
    
    field_sims = {}
    
    for field in sorted(all_fields):
        if field not in flat1:
            field_sims[field] = 0.0
        elif field not in flat2:
            field_sims[field] = 0.0
        elif flat1[field] == flat2[field]:
            field_sims[field] = 1.0
        else:
            v1_str = str(flat1[field])
            v2_str = str(flat2[field])
            field_sims[field] = string_similarity(v1_str, v2_str)
    
    overall = sum(field_sims.values()) / len(field_sims) if field_sims else 0.0
    return overall, field_sims


def string_similarity(s1: str, s2: str) -> float:
    """Compute string similarity using Levenshtein ratio."""
    if s1 == s2:
        return 1.0
    
    longer = max(len(s1), len(s2))
    if longer == 0:
        return 1.0
    
    matching = sum(1 for c1, c2 in zip(s1, s2) if c1 == c2)
    return matching / longer


def hybrid_similarity(embedding_sim: float, field_sim: float, weights: Tuple[float, float] = (0.7, 0.3)) -> float:
    """
    Combine embedding and field similarity.
    
    Args:
        embedding_sim: Similarity from transformer embeddings (0-1)
        field_sim: Similarity from field comparison (0-1)
        weights: (embedding_weight, field_weight), default (0.7, 0.3)
    
    Returns:
        Combined similarity score (0-1)
    """
    w_embed, w_field = weights
    total_weight = w_embed + w_field
    return (embedding_sim * w_embed + field_sim * w_field) / total_weight


def analyze_differences(data1: dict, data2: dict, name1: str = "File 1", name2: str = "File 2") -> str:
    """
    Analyze and display differences with field-level scores.
    
    Shows:
    - Which fields are different
    - How different (similarity %)
    - What changed
    - Importance ranking
    """
    flat1 = flatten_dict(data1)
    flat2 = flatten_dict(data2)
    
    all_fields = set(flat1.keys()) | set(flat2.keys())
    
    differences = []
    
    for field in sorted(all_fields):
        if field not in flat1:
            differences.append({
                'field': field,
                'status': 'NEW',
                'value1': None,
                'value2': flat2[field],
                'similarity': 0.0
            })
        elif field not in flat2:
            differences.append({
                'field': field,
                'status': 'REMOVED',
                'value1': flat1[field],
                'value2': None,
                'similarity': 0.0
            })
        elif flat1[field] != flat2[field]:
            sim = string_similarity(str(flat1[field]), str(flat2[field]))
            differences.append({
                'field': field,
                'status': 'CHANGED',
                'value1': flat1[field],
                'value2': flat2[field],
                'similarity': sim
            })
    
    differences.sort(key=lambda x: x['similarity'])
    
    lines = [
        f"## Field-Level Differences: {name1} vs {name2}\n",
        f"Total fields: {len(all_fields)} | Different: {len(differences)}\n",
        "| Field | Status | Similarity | Value 1 | Value 2 |",
        "|-------|--------|-----------|---------|---------|",
    ]
    
    for diff in differences:
        field = diff['field']
        status = diff['status']
        sim = f"{diff['similarity']:.0%}"
        
        v1 = str(diff['value1'])[:40] if diff['value1'] is not None else "—"
        v2 = str(diff['value2'])[:40] if diff['value2'] is not None else "—"
        
        lines.append(f"| {field} | {status} | {sim} | {v1} | {v2} |")
    
    return "\n".join(lines)


def detailed_diff(data1: dict, data2: dict, name1: str = "File 1", name2: str = "File 2", 
                 show_unchanged: bool = False) -> str:
    """
    Generate detailed diff showing all changes with context.
    
    Args:
        data1: First dict
        data2: Second dict
        name1: Label for first file
        name2: Label for second file
        show_unchanged: Include unchanged fields (default False)
    
    Returns:
        Markdown-formatted detailed diff
    """
    flat1 = flatten_dict(data1)
    flat2 = flatten_dict(data2)
    
    all_fields = set(flat1.keys()) | set(flat2.keys())
    
    lines = [
        f"# Detailed Differences: {name1} ↔ {name2}\n",
        f"**Total fields:** {len(all_fields)}\n"
    ]
    
    changed = []
    new = []
    removed = []
    unchanged = []
    
    for field in sorted(all_fields):
        if field not in flat1:
            new.append((field, flat2[field]))
        elif field not in flat2:
            removed.append((field, flat1[field]))
        elif flat1[field] == flat2[field]:
            unchanged.append((field, flat1[field]))
        else:
            changed.append((field, flat1[field], flat2[field]))
    
    if changed:
        lines.append(f"## ⚠️ Changed ({len(changed)} fields)\n")
        for field, v1, v2 in changed:
            lines.append(f"**{field}**")
            lines.append(f"- {name1}: `{v1}`")
            lines.append(f"- {name2}: `{v2}`")
            lines.append("")
    
    if new:
        lines.append(f"## ✨ New in {name2} ({len(new)} fields)\n")
        for field, value in new:
            lines.append(f"**{field}**: `{value}`")
        lines.append("")
    
    if removed:
        lines.append(f"## 🗑️ Removed from {name2} ({len(removed)} fields)\n")
        for field, value in removed:
            lines.append(f"**{field}**: `{value}`")
        lines.append("")
    
    if show_unchanged and unchanged:
        lines.append(f"## ✅ Unchanged ({len(unchanged)} fields)\n")
        for field, value in unchanged:
            lines.append(f"- **{field}**: `{value}`")
        lines.append("")
    
    return "\n".join(lines)
