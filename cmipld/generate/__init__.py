"""
Generate module for CMIP-LD

Contains utilities for generating various outputs including:
- JSON-LD contexts
- GitHub issues  
- Repository summaries
- README files
- GitHub issue templates
"""

# Template utilities - can be imported in template .py files
from .template_utils import (
    get_repo_info,
    get_folders_from_branch,
    get_json_files_from_branch,
    get_file_content_from_branch,
    get_template_fields_and_options,
    find_matching_option,
    extract_value,
    generate_prefill_link,
    generate_prefill_links_for_folder,
    get_existing_entries_markdown,
    DATA_BRANCH
)

__all__ = [
    'get_repo_info',
    'get_folders_from_branch', 
    'get_json_files_from_branch',
    'get_file_content_from_branch',
    'get_template_fields_and_options',
    'find_matching_option',
    'extract_value',
    'generate_prefill_link',
    'generate_prefill_links_for_folder',
    'get_existing_entries_markdown',
    'DATA_BRANCH'
]
