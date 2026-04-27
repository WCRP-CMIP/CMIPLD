"""
cmipld.utils.similarity
=======================
Pipeline for analysing submitted JSON-LD items against a folder's graph.
"""

import os as _os

# Model cache lives in ~/.cache/cmipld/models — never inside the package.
# This keeps the installable package small and avoids committing model files to git.
MODEL_PATH = _os.path.join(
    _os.path.expanduser("~"), ".cache", "cmipld", "models"
)
_os.makedirs(MODEL_PATH, exist_ok=True)

from .graph_loader import GraphLoader
from .link_analyzer import LinkAnalyzer, LinkResult, extract_links
from .pydantic_validator import (
    PydanticValidator,
    ValidationResult,
    short,
    is_default_skip,
    DEFAULT_SKIP_PREFIXES,
    CMIPLD_KEY_TRANSLATION,
)
from .text_similarity import TextSimilarityAnalyzer, SimilarityResult, strip_text_fields
from .report_builder import ReportBuilder
from .folder_similarity import FolderSimilarity
from .fingerprint import JSONSimilarityFingerprint, diff_jsons, MODEL_NAME
from .analysis import (
    compute_field_similarity,
    hybrid_similarity,
    analyze_differences,
    detailed_diff,
    string_similarity,
)
from .rdf import RDFLinkAnalyzer

__all__ = [
    "MODEL_PATH", "MODEL_NAME",
    "GraphLoader",
    "LinkAnalyzer",      "LinkResult",
    "PydanticValidator", "ValidationResult",
    "TextSimilarityAnalyzer", "SimilarityResult",
    "ReportBuilder",
    "FolderSimilarity",
    "short", "is_default_skip", "strip_text_fields", "extract_links",
    "DEFAULT_SKIP_PREFIXES", "CMIPLD_KEY_TRANSLATION",
    "JSONSimilarityFingerprint", "diff_jsons",
    "compute_field_similarity", "hybrid_similarity",
    "analyze_differences", "detailed_diff", "string_similarity",
    "RDFLinkAnalyzer",
]
