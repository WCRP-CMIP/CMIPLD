"""
cmipld.utils.similarity
=======================
Pipeline for analysing submitted JSON-LD items against a folder's graph.
"""

import os as _os

# Cache directory for the bundled fastembed ONNX model.
MODEL_PATH = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), 'models')

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
