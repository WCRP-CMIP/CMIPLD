"""
Generate module for CMIP-LD

Contains utilities for generating various outputs including:
- JSON-LD graphs and RDF/Turtle files
- D3/Graphology visualization JSON
- GitHub issue templates
- Repository summaries and README files

Note: graphify module can be imported and used standalone without
the full cmipld package. It gracefully handles missing dependencies.
"""

# Import styling utilities from utils (shared across modules)
try:
    from cmipld.utils.styling import (
        get_colors_from_css,
        get_project_colors,
        shorten_uri,
        get_node_color,
        get_folder_from_uri,
        format_status,
        DEFAULT_COLORS,
        STATUS_ICONS,
        STATUS_EMOJI
    )
    _HAS_STYLING = True
except ImportError:
    _HAS_STYLING = False
    DEFAULT_COLORS = {
        'primary': '#2196f3',
        'primary_light': '#bbdefb',
        'primary_dark': '#1976d2',
        'grey': '#808080'
    }
    get_colors_from_css = None
    get_project_colors = None

# Import graphify functions (these work standalone)
from .graphify import (
    find_vocab_directories,
    generate_jsonld_graph,
    generate_rdf_turtle,
    generate_d3_graph,
    generate_d3_structure,
    extract_relationships,
    process_all as graphify_all,
)

# Try to import template utilities (require cmipld)
try:
    from .template_utils import (
        # Repository and branch utilities
        get_repo_info,
        get_folders_from_branch,
        get_json_files_from_branch,
        get_file_content_from_branch,
        DATA_BRANCH,
        # Template field utilities
        get_template_fields_and_options,
        find_matching_option,
        extract_value,
        normalize_value,
        # Configuration utilities
        load_template_config,
        resolve_prefill_sources,
        apply_field_mapping,
        # Prefill link generation
        generate_prefill_link,
        generate_prefill_links_for_folder,
        get_existing_entries_markdown,
        get_prefill_links_by_folder,
    )
    _HAS_TEMPLATE_UTILS = True
except ImportError:
    _HAS_TEMPLATE_UTILS = False
    # Create placeholder exports
    get_repo_info = None
    get_folders_from_branch = None
    get_json_files_from_branch = None
    get_file_content_from_branch = None
    get_template_fields_and_options = None
    find_matching_option = None
    extract_value = None
    normalize_value = None
    load_template_config = None
    resolve_prefill_sources = None
    apply_field_mapping = None
    generate_prefill_link = None
    generate_prefill_links_for_folder = None
    get_existing_entries_markdown = None
    get_prefill_links_by_folder = None
    DATA_BRANCH = 'src-data'

__all__ = [
    # Styling utilities
    'get_colors_from_css',
    'get_project_colors',
    'DEFAULT_COLORS',
    # Graph utilities (always available)
    'find_vocab_directories',
    'generate_jsonld_graph',
    'generate_rdf_turtle',
    'generate_d3_graph',
    'generate_d3_structure',
    'extract_relationships',
    'graphify_all',
    # Template utilities - Repository/branch
    'get_repo_info',
    'get_folders_from_branch', 
    'get_json_files_from_branch',
    'get_file_content_from_branch',
    'DATA_BRANCH',
    # Template utilities - Field handling
    'get_template_fields_and_options',
    'find_matching_option',
    'extract_value',
    'normalize_value',
    # Template utilities - Configuration
    'load_template_config',
    'resolve_prefill_sources',
    'apply_field_mapping',
    # Template utilities - Prefill links
    'generate_prefill_link',
    'generate_prefill_links_for_folder',
    'get_existing_entries_markdown',
    'get_prefill_links_by_folder',
]
