"""
JSON similarity fingerprinting using fastembed (ONNX, no torch required).
Works with dict input: {file_path: data_dict, ...}
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Union

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_fastembed_model = None


def _get_model(model_name: str = None, cache_dir: str = None):
    """Load fastembed model, using cmipld bundled cache by default."""
    global _fastembed_model
    name = model_name or MODEL_NAME
    if _fastembed_model is None or getattr(_fastembed_model, 'model_name', None) != name:
        try:
            from fastembed import TextEmbedding
        except ImportError:
            import subprocess, sys
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "fastembed"],
                timeout=180, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            from fastembed import TextEmbedding
        if cache_dir is None:
            from cmipld.utils.similarity import MODEL_PATH
            cache_dir = MODEL_PATH
        _fastembed_model = TextEmbedding(name, cache_dir=cache_dir)
    return _fastembed_model



class JSONSimilarityFingerprint:
    """Analyze JSON similarity using fastembed ONNX embeddings. No torch required."""

    def __init__(self, model_name: str = None, include_keys: bool = False):
        self.model_name   = model_name or MODEL_NAME
        self.include_keys = include_keys
        self.file_paths   = []
        self.data_dict    = {}
        self.embeddings   = None
        self.similarity_matrix = None
        self.texts        = []

    def load_from_dict(self, data_dict: Dict[str, dict]) -> int:
        self.data_dict  = data_dict
        self.file_paths = list(data_dict.keys())
        return len(self.file_paths)

    def load_jsons_from_glob(self, pattern: str) -> int:
        import glob
        self.file_paths = sorted(glob.glob(pattern))
        self.data_dict  = {}
        for fp in self.file_paths:
            with open(fp) as f:
                self.data_dict[fp] = json.load(f)
        return len(self.file_paths)

    def json_to_text(self, data: dict) -> str:
        parts = []
        def flatten(obj, prefix=''):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if not k.startswith('_'):
                        flatten(v, prefix=f"{prefix}{k} " if self.include_keys else prefix)
            elif isinstance(obj, (list, tuple)):
                for item in obj:
                    flatten(item, prefix=prefix)
            else:
                parts.append(f"{prefix}{obj}")
        flatten(data)
        return ' '.join(parts)

    def embed(self, batch_size: int = 32, show_progress: bool = False):
        if not self.file_paths:
            raise ValueError("No files loaded.")
        self.texts = [self.json_to_text(self.data_dict[fp]) for fp in self.file_paths]
        model = _get_model(self.model_name)
        self.embeddings = np.array(list(model.embed(self.texts)))
        return self.embeddings

    def compute_similarity(self):
        if self.embeddings is None:
            raise ValueError("Must call embed() first.")
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = self.embeddings / norms
        self.similarity_matrix = normalized @ normalized.T
        return self.similarity_matrix

    def export_similar_pairs(self, threshold: float = 0.85, group: bool = False) -> Union[List[str], Dict[int, List[str]]]:
        if self.similarity_matrix is None:
            raise ValueError("Must call compute_similarity() first.")
        if not group:
            pairs = []
            for i in range(len(self.similarity_matrix)):
                for j in range(i + 1, len(self.similarity_matrix)):
                    sim = self.similarity_matrix[i][j]
                    if sim > threshold:
                        pairs.append(f"{Path(self.file_paths[i]).name} ↔ {Path(self.file_paths[j]).name} ({sim:.1%})")
            return sorted(pairs, reverse=True)
        else:
            parent = {}
            def find(x):
                parent.setdefault(x, x)
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]
            def union(x, y):
                parent[find(x)] = find(y)
            for i in range(len(self.similarity_matrix)):
                for j in range(i + 1, len(self.similarity_matrix)):
                    if self.similarity_matrix[i][j] > threshold:
                        union(i, j)
            groups: Dict[int, List[str]] = {}
            seen: Dict[int, int] = {}
            gid = 0
            for i in range(len(self.file_paths)):
                root = find(i)
                if root not in seen:
                    seen[root] = gid
                    gid += 1
                groups.setdefault(seen[root], []).append(Path(self.file_paths[i]).name)
            return {k: v for k, v in groups.items() if len(v) > 1}


def diff_jsons(data1: dict, data2: dict, name1: str = "File 1", name2: str = "File 2", max_depth: int = 10) -> str:
    differences = []
    def compare(o1, o2, path="", depth=0):
        if depth > max_depth:
            return
        if type(o1) != type(o2):
            differences.append((path, f"**Type mismatch**: {type(o1).__name__} vs {type(o2).__name__}"))
            return
        if isinstance(o1, dict) and isinstance(o2, dict):
            for key in sorted(set(o1) | set(o2)):
                p = f"{path}.{key}" if path else key
                if key not in o1:
                    differences.append((p, f"**Only in {name2}**: {json.dumps(o2[key])}"))
                elif key not in o2:
                    differences.append((p, f"**Only in {name1}**: {json.dumps(o1[key])}"))
                else:
                    compare(o1[key], o2[key], p, depth + 1)
        elif isinstance(o1, list) and isinstance(o2, list):
            if len(o1) != len(o2):
                differences.append((path, f"**List length**: {len(o1)} vs {len(o2)}"))
            else:
                for i, (a, b) in enumerate(zip(o1, o2)):
                    compare(a, b, f"{path}[{i}]", depth + 1)
        elif o1 != o2:
            differences.append((path, f"`{json.dumps(o1)}` → `{json.dumps(o2)}`"))
    compare(data1, data2)
    lines = [f"## Differences between {name1} and {name2}\n"]
    if not differences:
        lines.append("✅ **No differences found!**\n")
    else:
        lines += [f"Found **{len(differences)}** differences:\n", "```"]
        for path, diff in differences:
            lines += [path, f"  {diff}\n"]
        lines.append("```\n")
    return "\n".join(lines)
