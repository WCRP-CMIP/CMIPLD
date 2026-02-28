"""
JSON similarity fingerprinting using sentence-transformers.
Works with dict input: {file_path: data_dict, ...}

Uses transformer embeddings (sentence-transformers) for semantic similarity.
Converts JSON to text (values + optional keys if semantic).
"""

import json
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Optional, Union

SentenceTransformer = None


def _ensure_sentence_transformers():
    """Load sentence-transformers model. Auto-installs if missing."""
    global SentenceTransformer
    if SentenceTransformer is None:
        try:
            from sentence_transformers import SentenceTransformer as ST
            SentenceTransformer = ST
            return SentenceTransformer
        except ImportError:
            print("⚠ sentence-transformers not found. Installing...")
            import subprocess
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "sentence-transformers"], timeout=180)
                from sentence_transformers import SentenceTransformer as ST
                SentenceTransformer = ST
                print("✓ sentence-transformers installed")
                return SentenceTransformer
            except Exception as install_err:
                print(f"ERROR: Could not install sentence-transformers")
                print(f"  {install_err}")
                print("\nManual install: pip install sentence-transformers")
                raise
        except Exception as e:
            error_msg = str(e)
            print(f"ERROR: Could not load sentence-transformers")
            print(f"  {type(e).__name__}: {error_msg}")
            print("\nManual install: pip install sentence-transformers")
            raise
    return SentenceTransformer


class JSONSimilarityFingerprint:
    """
    Analyze JSON file similarity using transformer embeddings.
    
    Features:
    - Converts JSON to semantic text
    - Uses sentence-transformers (all-MiniLM-L6-v2 by default)
    - Computes cosine similarity between embeddings
    - Finds clusters, representatives, outliers
    - Option to skip noisy/variable-length keys
    
    Works with:
    - Dict: {file_path: data_dict, ...}
    - Glob: load JSON files from disk
    """
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', include_keys: bool = False):
        """
        Initialize with transformer model.
        
        Args:
            model_name: HuggingFace model ID (default: all-MiniLM-L6-v2)
            include_keys: Include JSON keys in text (default False)
        """
        self.model_name = model_name
        self.include_keys = include_keys
        self.model = None
        self.file_paths = []
        self.data_dict = {}
        self.embeddings = None
        self.similarity_matrix = None
        self.texts = []
        
    def load_from_dict(self, data_dict: Dict[str, dict]) -> int:
        """Load JSON data from dictionary."""
        self.data_dict = data_dict
        self.file_paths = list(data_dict.keys())
        print(f"✓ Loaded {len(self.file_paths)} files from dict")
        return len(self.file_paths)
    
    def load_jsons_from_glob(self, pattern: str) -> int:
        """Load JSON files matching glob pattern."""
        import glob
        file_paths = sorted(glob.glob(pattern))
        self.file_paths = file_paths
        self.data_dict = {}
        
        for fp in file_paths:
            with open(fp) as f:
                self.data_dict[fp] = json.load(f)
        
        print(f"✓ Loaded {len(self.file_paths)} files from glob")
        return len(self.file_paths)
    
    def json_to_text(self, data: dict) -> str:
        """Convert JSON to semantic text."""
        text_parts = []
        
        def flatten(obj, prefix=''):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if not k.startswith('_'):
                        if self.include_keys:
                            new_prefix = f"{prefix}{k} " if prefix else f"{k} "
                        else:
                            new_prefix = prefix
                        flatten(v, prefix=new_prefix)
            elif isinstance(obj, (list, tuple)):
                for item in obj:
                    flatten(item, prefix=prefix)
            else:
                text_parts.append(f"{prefix}{str(obj)}")
        
        flatten(data)
        return ' '.join(text_parts)
    
    def embed(self, batch_size: int = 32, show_progress: bool = True):
        """Embed all files using transformer."""
        if not self.file_paths:
            raise ValueError("No files loaded. Call load_from_dict() or load_jsons_from_glob() first")
        
        print("Converting JSONs to semantic text...")
        self.texts = []
        for fp in self.file_paths:
            data = self.data_dict[fp]
            text = self.json_to_text(data)
            self.texts.append(text)
        
        st = _ensure_sentence_transformers()
        print(f"Loading transformer model: {self.model_name}")
        self.model = st(self.model_name)
        
        print(f"Encoding {len(self.texts)} texts to embeddings...")
        self.embeddings = self.model.encode(
            self.texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        print(f"✓ Embeddings: {self.embeddings.shape} (files × dimensions)")
        return self.embeddings
    
    def compute_similarity(self):
        """Compute cosine similarity between embeddings."""
        if self.embeddings is None:
            raise ValueError("Must call embed() first")
        
        try:
            import numpy as np
        except ImportError:
            raise ImportError("numpy required for similarity computation")
        
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        normalized = self.embeddings / norms
        
        self.similarity_matrix = normalized @ normalized.T
        
        print(f"✓ Similarity matrix: {self.similarity_matrix.shape}")
        return self.similarity_matrix
    
    def find_clusters(self, n_clusters: int = 5) -> Dict[int, List[int]]:
        """Find clusters of similar files using K-means."""
        try:
            import numpy as np
        except ImportError:
            raise ImportError("numpy required for clustering")
        
        if self.embeddings is None:
            raise ValueError("Must call embed() first")
        
        X = self.embeddings
        n_samples = X.shape[0]
        
        indices = np.random.choice(n_samples, n_clusters, replace=False)
        centers = X[indices].copy()
        
        for iteration in range(100):
            distances = np.sqrt(((X - centers[:, np.newaxis]) ** 2).sum(axis=2))
            labels = np.argmin(distances, axis=0)
            
            old_centers = centers.copy()
            for k in range(n_clusters):
                if np.sum(labels == k) > 0:
                    centers[k] = X[labels == k].mean(axis=0)
            
            if np.allclose(old_centers, centers):
                break
        
        clusters = {}
        for cluster_id in range(n_clusters):
            clusters[cluster_id] = np.where(labels == cluster_id)[0].tolist()
        
        return clusters
    
    def find_representatives(self, clusters: Dict[int, List[int]]) -> Dict[int, str]:
        """Find most representative file in each cluster."""
        try:
            import numpy as np
        except ImportError:
            raise ImportError("numpy required for representatives")
        
        X = self.embeddings
        n_clusters = len(clusters)
        
        indices = np.random.choice(X.shape[0], n_clusters, replace=False)
        centers = X[indices].copy()
        
        for _ in range(100):
            distances = np.sqrt(((X - centers[:, np.newaxis]) ** 2).sum(axis=2))
            labels = np.argmin(distances, axis=0)
            
            old_centers = centers.copy()
            for k in range(n_clusters):
                if np.sum(labels == k) > 0:
                    centers[k] = X[labels == k].mean(axis=0)
            
            if np.allclose(old_centers, centers):
                break
        
        representatives = {}
        for cluster_id, member_indices in clusters.items():
            if not member_indices:
                continue
            
            dists = [np.linalg.norm(X[i] - centers[cluster_id]) for i in member_indices]
            closest = member_indices[np.argmin(dists)]
            representatives[cluster_id] = self.file_paths[closest]
        
        return representatives
    
    def find_outliers(self, threshold: float = 0.5) -> List[str]:
        """Find outliers with low average similarity."""
        try:
            import numpy as np
        except ImportError:
            raise ImportError("numpy required for outlier detection")
        
        if self.similarity_matrix is None:
            raise ValueError("Must call compute_similarity() first")
        
        avg_sims = []
        for i in range(len(self.similarity_matrix)):
            sim = np.mean([self.similarity_matrix[i][j] for j in range(len(self.similarity_matrix)) if i != j])
            avg_sims.append(sim)
        
        outliers = [
            self.file_paths[i]
            for i, sim in enumerate(avg_sims)
            if sim < threshold
        ]
        
        return outliers
    
    def export_similar_pairs(self, threshold: float = 0.85, group: bool = False) -> Union[List[str], Dict[int, List[str]]]:
        """Export similar pairs as strings or grouped."""
        if self.similarity_matrix is None:
            raise ValueError("Must call compute_similarity() first")
        
        if not group:
            pairs_str = []
            for i in range(len(self.similarity_matrix)):
                for j in range(i + 1, len(self.similarity_matrix)):
                    sim = self.similarity_matrix[i][j]
                    if sim > threshold:
                        fp1 = Path(self.file_paths[i]).name
                        fp2 = Path(self.file_paths[j]).name
                        pairs_str.append(f"{fp1} ↔ {fp2} ({sim:.1%})")
            
            pairs_str.sort(reverse=True)
            return pairs_str
        
        else:
            similar_pairs = []
            for i in range(len(self.similarity_matrix)):
                for j in range(i + 1, len(self.similarity_matrix)):
                    sim = self.similarity_matrix[i][j]
                    if sim > threshold:
                        similar_pairs.append((i, j))
            
            parent = {}
            
            def find(x):
                if x not in parent:
                    parent[x] = x
                if parent[x] != x:
                    parent[x] = find(parent[x])
                return parent[x]
            
            def union(x, y):
                px, py = find(x), find(y)
                if px != py:
                    parent[px] = py
            
            for i, j in similar_pairs:
                union(i, j)
            
            groups_dict = {}
            for i in range(len(self.file_paths)):
                root = find(i)
                if root not in groups_dict:
                    groups_dict[root] = []
                groups_dict[root].append(Path(self.file_paths[i]).name)
            
            result = {}
            group_id = 0
            for root in sorted(groups_dict.keys()):
                files = sorted(groups_dict[root])
                if len(files) > 1:
                    result[group_id] = files
                    group_id += 1
            
            return result
    
    def export_clusters(self, n_clusters: int = 5) -> Dict[int, List[str]]:
        """Export clusters as strings (file names)."""
        clusters_idx = self.find_clusters(n_clusters=n_clusters)
        
        clusters_str = {}
        for cluster_id, member_indices in clusters_idx.items():
            clusters_str[cluster_id] = [Path(self.file_paths[i]).name for i in member_indices]
        
        return clusters_str
    
    def export_outliers(self, threshold: float = 0.5) -> List[str]:
        """Export outliers as strings (file names)."""
        outliers_idx = self.find_outliers(threshold=threshold)
        return [Path(fp).name for fp in outliers_idx]
    
    def to_json(self, threshold_pairs: float = 0.85, n_clusters: int = 5, threshold_outliers: float = 0.5, 
                output_file: Optional[str] = None) -> Dict:
        """Export all analysis results (pairs, clusters, outliers) as JSON."""
        pairs_list = self.export_similar_pairs(threshold=threshold_pairs, group=False)
        pairs_grouped = self.export_similar_pairs(threshold=threshold_pairs, group=True)
        clusters = self.export_clusters(n_clusters=n_clusters)
        outliers = self.export_outliers(threshold=threshold_outliers)
        
        result = {
            "metadata": {
                "model": self.model_name,
                "n_files": len(self.file_paths),
                "embedding_dim": int(self.embeddings.shape[1]) if self.embeddings is not None else None,
                "include_keys": self.include_keys
            },
            "similar_pairs": {
                "string_format": pairs_list,
                "grouped": pairs_grouped
            },
            "clusters": {str(k): v for k, v in clusters.items()},
            "outliers": outliers
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"✓ Results saved to: {output_file}")
            return result
        else:
            return result


def diff_jsons(data1: dict, data2: dict, name1: str = "File 1", name2: str = "File 2", max_depth: int = 10) -> str:
    """Generate a pretty diff between two JSON objects for GitHub issues."""
    lines = []
    lines.append(f"## Differences between {name1} and {name2}\n")
    
    differences = []
    
    def compare(obj1, obj2, path="", depth=0):
        """Recursively compare two objects"""
        if depth > max_depth:
            return
        
        if type(obj1) != type(obj2):
            differences.append((path, f"**Type mismatch**: {type(obj1).__name__} vs {type(obj2).__name__}"))
            return
        
        if isinstance(obj1, dict) and isinstance(obj2, dict):
            all_k = set(obj1.keys()) | set(obj2.keys())
            for key in sorted(all_k):
                new_path = f"{path}.{key}" if path else key
                
                if key not in obj1:
                    differences.append((new_path, f"**Only in {name2}**: {json.dumps(obj2[key])}"))
                elif key not in obj2:
                    differences.append((new_path, f"**Only in {name1}**: {json.dumps(obj1[key])}"))
                else:
                    compare(obj1[key], obj2[key], new_path, depth + 1)
        
        elif isinstance(obj1, list) and isinstance(obj2, list):
            if len(obj1) != len(obj2):
                differences.append((path, f"**List length**: {len(obj1)} vs {len(obj2)}"))
            else:
                for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                    compare(item1, item2, f"{path}[{i}]", depth + 1)
        
        elif obj1 != obj2:
            differences.append((path, f"`{json.dumps(obj1)}` → `{json.dumps(obj2)}`"))
    
    compare(data1, data2)
    
    if not differences:
        lines.append("✅ **No differences found!**\n")
    else:
        lines.append(f"Found **{len(differences)}** differences:\n")
        lines.append("```")
        for path, diff in differences:
            lines.append(f"{path}")
            lines.append(f"  {diff}\n")
        lines.append("```\n")
    
    return "\n".join(lines)


def export_diff_markdown(fp: JSONSimilarityFingerprint, file1_name: str, file2_name: str) -> str:
    """Export a GitHub-friendly diff between two loaded files."""
    if file1_name not in fp.file_paths or file2_name not in fp.file_paths:
        return f"Error: Files not found in loaded data"
    
    data1 = fp.data_dict[file1_name]
    data2 = fp.data_dict[file2_name]
    
    return diff_jsons(data1, data2, name1=Path(file1_name).name, name2=Path(file2_name).name)


def main():
    """Example usage."""
    data_dict = {
        'grid_1.json': {'a': 'Regular Grid', 'xyz': 1.25},
        'grid_2.json': {'k': 'Regular Grid', 'x_res': 1.25},
        'grid_3.json': {'type_name': 'Gaussian Grid', 'res': 2.5},
    }
    
    fp = JSONSimilarityFingerprint(include_keys=False)
    fp.load_from_dict(data_dict)
    fp.embed()
    fp.compute_similarity()
    
    pairs = fp.export_similar_pairs(threshold=0.8)
    for pair in pairs:
        print(pair)


if __name__ == '__main__':
    main()
