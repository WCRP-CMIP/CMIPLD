"""
cmipld.utils.similarity
=======================
Pipeline for analysing submitted JSON-LD items against a folder's graph.

Quick start
-----------
    import cmipld
    from cmipld.utils.similarity import GraphLoader, LinkAnalyzer, PydanticValidator
    from cmipld.utils.similarity import TextSimilarityAnalyzer, ReportBuilder

    graph_data = cmipld.expand("emd:horizontal_grid_cells/_graph.json", depth=2)

    loader     = GraphLoader("emd:horizontal_grid_cells", graph_data=graph_data)
    link_res   = LinkAnalyzer(loader).analyze(item)
    val_res    = PydanticValidator("horizontal_grid_cell", item).validate()
    sim_res    = TextSimilarityAnalyzer(
                     loader,
                     exclude=link_res.link_fields | val_res.validated_fields
                 ).analyze(item)

    # Each result has .data (dict) and .md (Markdown string)
    print(link_res.md)
    print(val_res.data)

    # Or run everything at once:
    report = ReportBuilder(
        "emd:horizontal_grid_cells", "horizontal_grid_cell", item,
        graph_data=graph_data
    ).build()
"""

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

# Legacy / lower-level utilities
from .fingerprint import JSONSimilarityFingerprint, diff_jsons
from .analysis import (
    compute_field_similarity,
    hybrid_similarity,
    analyze_differences,
    detailed_diff,
    string_similarity,
)
from .rdf import RDFLinkAnalyzer

__all__ = [
    # Primary pipeline
    "GraphLoader",
    "LinkAnalyzer",     "LinkResult",
    "PydanticValidator","ValidationResult",
    "TextSimilarityAnalyzer", "SimilarityResult",
    "ReportBuilder",
    # Helpers
    "short", "is_default_skip", "strip_text_fields", "extract_links",
    "DEFAULT_SKIP_PREFIXES", "CMIPLD_KEY_TRANSLATION",
    # Legacy utilities
    "JSONSimilarityFingerprint", "diff_jsons",
    "compute_field_similarity", "hybrid_similarity",
    "analyze_differences", "detailed_diff", "string_similarity",
    "RDFLinkAnalyzer",
]
