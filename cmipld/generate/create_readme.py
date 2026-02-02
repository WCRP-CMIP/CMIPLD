#!/usr/bin/env python3
"""
Create README files for WCRP universe data directories.

This module generates clean, structured markdown documentation for CMIP-LD
vocabulary directories, integrating with cmipld and esgvoc libraries.
"""

import os
import re
import json
import sys
import argparse
import inspect
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Any, get_type_hints, get_origin, get_args, Union
from collections import defaultdict
from datetime import datetime
import urllib.parse

# =============================================================================
# Configuration
# =============================================================================

@dataclass
class Config:
    """Configuration for README generation."""
    priority_keys: tuple = ('validation-key', 'ui-label', 'description', 'name')
    end_keys: tuple = ('@context', 'type')
    skip_keys: tuple = ('id', '@id', 'type', '@type', '@context', 'drs_name')
    skip_directories: tuple = ('project',)
    github_org: str = 'WCRP-CMIP'
    esgvoc_repo_url: str = 'https://github.com/ESGF/esgf-vocab/blob/main/src/esgvoc/api/data_descriptors'


CONFIG = Config()

# =============================================================================
# Library Imports (with graceful fallbacks)
# =============================================================================

try:
    import cmipld
    from cmipld.utils.git import get_path_url, get_repo_url, get_relative_path
    from cmipld import prefix_url
    CMIPLD_AVAILABLE = True
except ImportError:
    print("Warning: cmipld not available. Some features will be limited.")
    CMIPLD_AVAILABLE = False
    cmipld = None

try:
    import esgvoc
    from esgvoc.api.data_descriptors import DATA_DESCRIPTOR_CLASS_MAPPING
    ESGVOC_AVAILABLE = True
except ImportError:
    print("Warning: esgvoc not available. Pydantic models will not be used.")
    DATA_DESCRIPTOR_CLASS_MAPPING = {}
    ESGVOC_AVAILABLE = False


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FieldInfo:
    """Detailed information about a schema field."""
    name: str
    type_str: str
    description: str
    required: bool = True
    default: Any = None
    constraints: dict = field(default_factory=dict)
    references: list = field(default_factory=list)  # Links to other vocabularies


@dataclass
class VocabInfo:
    """Information about a vocabulary directory."""
    name: str
    path: Path
    prefix: str
    json_files: list = field(default_factory=list)
    keys: list = field(default_factory=list)
    pydantic_model: Optional[str] = None
    pydantic_class: Optional[type] = None
    pydantic_file_path: Optional[str] = None
    model_docstring: Optional[str] = None
    module_docstring: Optional[str] = None
    fields: list = field(default_factory=list)  # List of FieldInfo
    validators: list = field(default_factory=list)  # List of validator info
    
    @property
    def display_name(self) -> str:
        """Human-readable name."""
        return self.name.replace('-', ' ').replace('_', ' ').title()
    
    @property 
    def type_uri(self) -> str:
        """Full type URI."""
        return f"{self.prefix}:{self.name}"
    
    @property
    def example_file(self) -> str:
        """First JSON file (alphabetically, excluding graph files) for examples."""
        if self.json_files:
            non_graph = [f for f in self.json_files if not f.startswith('graph')]
            files = non_graph if non_graph else self.json_files
            return sorted(files, key=str.lower)[0].replace('.json', '')
        return 'example'
    
    @property
    def description(self) -> str:
        """Get best available description from model or module docstring."""
        if self.model_docstring:
            # Clean up the docstring
            lines = self.model_docstring.strip().split('\n')
            # Skip the first line if it's just a title repeat
            cleaned = []
            for line in lines:
                stripped = line.strip()
                if stripped:
                    cleaned.append(stripped)
            return ' '.join(cleaned)
        if self.module_docstring:
            return self.module_docstring.strip().split('\n')[0]
        return ""


@dataclass  
class ExternalDependency:
    """An external vocabulary dependency."""
    prefix: str
    path: str
    url: str
    
    @property
    def full_ref(self) -> str:
        return f"{self.prefix}:{self.path}"


# =============================================================================
# Utility Functions
# =============================================================================

def sort_keys(keys: list) -> list:
    """Sort keys with priority ordering."""
    priority = list(CONFIG.priority_keys)
    end = list(CONFIG.end_keys)
    
    result = [k for k in priority if k in keys]
    result += sorted(k for k in keys if k not in priority and k not in end)
    result += [k for k in end if k in keys]
    
    return result


def extract_json_keys(directory: Path) -> list:
    """Extract all unique keys from JSON files in a directory."""
    keys = set()
    for json_file in directory.glob('*.json'):
        if json_file.name.startswith('_') or json_file.name.startswith('graph'):
            continue
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, dict):
                keys.update(data.keys())
        except (json.JSONDecodeError, IOError):
            continue
    return list(keys)


def format_type_annotation(annotation) -> str:
    """Convert a type annotation to a readable string."""
    if annotation is None:
        return "Any"
    
    origin = get_origin(annotation)
    args = get_args(annotation)
    
    # Handle Union types (including Optional)
    if origin is Union:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1 and type(None) in args:
            return f"Optional[{format_type_annotation(non_none[0])}]"
        return " | ".join(format_type_annotation(a) for a in args)
    
    # Handle List, Dict, etc.
    if origin is list:
        if args:
            return f"List[{format_type_annotation(args[0])}]"
        return "List"
    
    if origin is dict:
        if args and len(args) == 2:
            return f"Dict[{format_type_annotation(args[0])}, {format_type_annotation(args[1])}]"
        return "Dict"
    
    # Get the name
    if hasattr(annotation, '__name__'):
        return annotation.__name__
    
    return str(annotation).replace('typing.', '')


def extract_field_info(cls: type) -> list:
    """Extract detailed field information from a Pydantic model."""
    fields = []
    
    if not hasattr(cls, '__pydantic_fields__'):
        return fields
    
    pydantic_fields = cls.__pydantic_fields__
    
    for name, field_info in pydantic_fields.items():
        if name in CONFIG.skip_keys:
            continue
        
        # Get type string
        type_str = format_type_annotation(field_info.annotation)
        
        # Get description
        description = field_info.description or ""
        
        # Check if required
        required = field_info.is_required()
        
        # Get default
        default = field_info.default if field_info.default is not None else None
        
        # Extract constraints
        constraints = {}
        if hasattr(field_info, 'metadata'):
            for meta in field_info.metadata:
                if hasattr(meta, 'min_length'):
                    constraints['min_length'] = meta.min_length
                if hasattr(meta, 'max_length'):
                    constraints['max_length'] = meta.max_length
                if hasattr(meta, 'ge'):
                    constraints['min'] = meta.ge
                if hasattr(meta, 'le'):
                    constraints['max'] = meta.le
                if hasattr(meta, 'pattern'):
                    constraints['pattern'] = meta.pattern
        
        # Check for references to other vocabularies in description
        references = []
        if description:
            # Look for patterns like "Taken from X.X name CV"
            cv_matches = re.findall(r'Taken from [\d.]+ (\w+) CV', description)
            references.extend(cv_matches)
            # Look for patterns referencing other types
            type_refs = re.findall(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', type_str)
            references.extend(type_refs)
        
        fields.append(FieldInfo(
            name=name,
            type_str=type_str,
            description=description,
            required=required,
            default=default,
            constraints=constraints,
            references=list(set(references))
        ))
    
    return fields


def extract_validators(cls: type) -> list:
    """Extract validator functions from a Pydantic model by reading source file."""
    validators = []
    
    if not cls:
        return validators
    
    # Try to get the source file path
    try:
        source_file = inspect.getfile(cls)
    except (TypeError, OSError):
        return validators
    
    # Read the entire source file
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            full_source = f.read()
    except (IOError, OSError):
        return validators
    
    # Simple approach: find all functions with @field_validator or @model_validator decorators
    # Split by 'def ' to get function blocks
    lines = full_source.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this line has a validator decorator
        if '@field_validator' in line or '@model_validator' in line:
            # Extract fields from decorator
            fields_validated = []
            if '@field_validator' in line:
                field_matches = re.findall(r'["\']([^"\']+)["\']', line)
                fields_validated = [f for f in field_matches if f not in ('before', 'after', 'mode')]
            
            # Find the def line (skip @classmethod if present)
            j = i + 1
            while j < len(lines) and not lines[j].strip().startswith('def '):
                j += 1
            
            if j < len(lines):
                # Extract function name
                def_line = lines[j]
                name_match = re.search(r'def\s+(\w+)', def_line)
                if name_match:
                    func_name = name_match.group(1)
                    
                    # Collect function body until we hit another def or decorator at same indent
                    func_lines = [def_line]
                    k = j + 1
                    base_indent = len(def_line) - len(def_line.lstrip())
                    
                    while k < len(lines):
                        curr_line = lines[k]
                        if curr_line.strip() == '':
                            func_lines.append(curr_line)
                            k += 1
                            continue
                        curr_indent = len(curr_line) - len(curr_line.lstrip())
                        # Stop if we're back at base indent with a new def or decorator
                        if curr_indent <= base_indent and (curr_line.strip().startswith('def ') or curr_line.strip().startswith('@')):
                            break
                        func_lines.append(curr_line)
                        k += 1
                    
                    func_source = '\n'.join(func_lines)
                    
                    # Extract docstring
                    docstring = ""
                    doc_match = re.search(r'"""(.*?)"""', func_source, re.DOTALL)
                    if doc_match:
                        docstring = doc_match.group(1).strip()
                    
                    validators.append({
                        'name': func_name,
                        'docstring': docstring,
                        'fields': fields_validated,
                        'source': func_source.strip(),
                    })
                    print(f"      Found validator: {func_name} -> fields: {fields_validated}")
                    
                    i = k
                    continue
        
        i += 1
    
    return validators


def find_pydantic_model(name: str) -> tuple:
    """Find matching Pydantic model for a vocabulary name.
    
    Returns:
        tuple: (model_name, model_class, relative_file_path, model_docstring, module_docstring)
    """
    if not DATA_DESCRIPTOR_CLASS_MAPPING:
        return None, None, None, None, None
    
    # Try different name variations
    variations = [
        name,
        name.replace('-', '_'),
        name.replace('_', '-'),
        f"{name.replace('-', '_')}_new",
    ]
    
    for variant in variations:
        if variant in DATA_DESCRIPTOR_CLASS_MAPPING:
            cls = DATA_DESCRIPTOR_CLASS_MAPPING[variant]
            
            # Get the file path using inspect
            file_path = None
            module_doc = None
            try:
                full_path = inspect.getfile(cls)
                # Extract relative path after data_descriptors/
                if 'data_descriptors/' in full_path:
                    idx = full_path.index('data_descriptors/') + len('data_descriptors/')
                    file_path = full_path[idx:]
                elif 'data_descriptors\\' in full_path:  # Windows
                    idx = full_path.index('data_descriptors\\') + len('data_descriptors\\')
                    file_path = full_path[idx:].replace('\\', '/')
                
                # Get module docstring
                module = inspect.getmodule(cls)
                if module and module.__doc__:
                    module_doc = module.__doc__
            except (TypeError, ValueError):
                pass
            
            # Get class docstring
            class_doc = cls.__doc__ if cls.__doc__ else None
            
            return variant, cls, file_path, class_doc, module_doc
    
    return None, None, None, None, None


def extract_description_from_readme(readme_path: Path) -> Optional[str]:
    """Extract existing description from README if present."""
    if not readme_path.exists():
        return None
    
    try:
        content = readme_path.read_text(encoding='utf-8')
        pattern = r'<section id="description">(.*?)</section>'
        match = re.search(pattern, content, re.DOTALL)
        
        if match:
            section = match.group(1).strip()
            desc_match = re.search(r'## Description\s*(.*?)(?=\n\n|\Z)', section, re.DOTALL)
            if desc_match:
                return desc_match.group(1).strip()
    except IOError:
        pass
    
    return None


# =============================================================================
# Markdown Generators
# =============================================================================

class MarkdownGenerator:
    """Generate markdown sections for vocabulary documentation."""
    
    def __init__(self, vocab: VocabInfo, urls: dict):
        self.vocab = vocab
        self.urls = urls
    
    def generate_header(self, existing_description: str = "") -> str:
        """Generate the header/description section."""
        # Use pydantic docstring if available, otherwise existing or placeholder
        description = existing_description or self.vocab.description or "_No description provided yet._"
        
        # Generation date for badge (use underscores, shields.io friendly)
        gen_date = datetime.utcnow().strftime("%Y_%m_%d")
        
        # Badges - all on one line with no line breaks
        pydantic_badge = "![Pydantic](https://img.shields.io/badge/Pydantic-✓-green)" if self.vocab.pydantic_class else "![Pydantic](https://img.shields.io/badge/Pydantic-✗-red)"
        type_encoded = urllib.parse.quote(self.vocab.type_uri, safe='')
        
        badge_line = f"![Generated](https://img.shields.io/badge/Generated-{gen_date}-708090) ![Type](https://img.shields.io/badge/Type-{type_encoded}-blue) {pydantic_badge} ![Files](https://img.shields.io/badge/Files-{len(self.vocab.json_files)}-lightgrey)"
        
        return f'''# {self.vocab.display_name}

{badge_line}

{description}
'''

    def generate_info_table(self) -> str:
        """Generate the information reference table."""
        pydantic_info = self._format_pydantic_info()
        content_url = self.urls.get('content', '#')
        repo_url = self.urls.get('repo', '#')
        io_url = self.urls.get('io', '#')
        short = self.urls.get('short', 'N/A')
        # Build contributing URL (main branch)
        contrib_url = repo_url.rstrip('/') + '/tree/main?tab=readme-ov-file#contributing'
        
        return f'''## Quick Reference

| Property | Value |
|----------|-------|
| **Type URI** | `{self.vocab.type_uri}` |
| **Prefix** | `{self.vocab.prefix}` |
| **Pydantic Model** | {pydantic_info} |
| **JSON-LD** | [`{short}`]({io_url}) |
| **Repository** | [![View Source](https://img.shields.io/badge/GitHub-View_Source-blue?logo=github)]({content_url}) |
| **Contribute** | [![Submit New / Edit Existing](https://img.shields.io/badge/Submit_New-Edit_Existing-grey?labelColor=orange&logo=github)]({contrib_url}) |
'''

    def _format_pydantic_info(self) -> str:
        """Format Pydantic model information."""
        if self.vocab.pydantic_model and self.vocab.pydantic_class:
            class_name = self.vocab.pydantic_class.__name__
            pydantic_url = self._get_pydantic_url()
            return f"[`{class_name}`]({pydantic_url})"
        return "_Not yet implemented_"
    
    def _get_pydantic_url(self) -> str:
        """Get the URL to the Pydantic model file."""
        if self.vocab.pydantic_file_path:
            return f"{CONFIG.esgvoc_repo_url}/{self.vocab.pydantic_file_path}"
        elif self.vocab.pydantic_model:
            return f"{CONFIG.esgvoc_repo_url}/{self.vocab.pydantic_model}.py"
        return "#"

    def generate_schema(self) -> str:
        """Generate the content schema section."""
        if not self.vocab.fields and not self.vocab.keys:
            return '''## Schema

_No schema information available._
'''
        
        if self.vocab.fields:
            return self._schema_from_fields()
        else:
            return self._schema_from_keys()

    def _schema_from_fields(self) -> str:
        """Generate detailed schema from Pydantic fields."""
        lines = ["## Schema\n"]
        
        # Explanation paragraph
        if self.vocab.pydantic_class:
            class_name = self.vocab.pydantic_class.__name__
            pydantic_url = self._get_pydantic_url()
            lines.append(f"The JSON structure and validation for this vocabulary is defined using the [`{class_name}`]({pydantic_url}) Pydantic model in [esgvoc](https://github.com/ESGF/esgf-vocab). This ensures data consistency and provides automatic validation of all entries. *Click field name for description.*\n")
        else:
            lines.append("_No Pydantic model available for validation. Click field name for description._\n")
        
        # Separate required and optional fields
        required = [f for f in self.vocab.fields if f.required]
        optional = [f for f in self.vocab.fields if not f.required]
        
        # Required Fields Table
        if required:
            lines.append("### Required Fields\n")
            lines.append("| Field | Type | Constraints | References |")
            lines.append("|-------|------|-------------|------------|")
            for f in sort_fields(required):
                type_short = self._shorten_type(f.type_str)
                constraints = ", ".join(f"{k}={v}" for k, v in f.constraints.items()) if f.constraints else "-"
                refs = self._format_references(f.references) if f.references else "-"
                lines.append(f"| [{f.name}](#{f.name}) | `{type_short}` | {constraints} | {refs} |")
            lines.append("")
        
        # Optional Fields Table
        if optional:
            lines.append("### Optional Fields\n")
            lines.append("| Field | Type | Constraints | References |")
            lines.append("|-------|------|-------------|------------|")
            for f in sort_fields(optional):
                type_short = self._shorten_type(f.type_str)
                constraints = ", ".join(f"{k}={v}" for k, v in f.constraints.items()) if f.constraints else "-"
                refs = self._format_references(f.references) if f.references else "-"
                lines.append(f"| [{f.name}](#{f.name}) | `{type_short}` | {constraints} | {refs} |")
            lines.append("")
        
        # Field Descriptions Section
        lines.append("### Field Descriptions\n")
        
        # Build validator lookup by field
        validators_by_field = {}
        unassigned_validators = []
        for v in self.vocab.validators:
            if v['fields'] and v['fields'][0] != '_model_':
                for field_name in v['fields']:
                    if field_name not in validators_by_field:
                        validators_by_field[field_name] = []
                    validators_by_field[field_name].append(v)
            else:
                unassigned_validators.append(v)
        
        # Get pydantic file URL for linking
        pydantic_url = self._get_pydantic_url() if self.vocab.pydantic_class else None
        
        for f in sort_fields(self.vocab.fields):
            lines.append(f'<a id="{f.name}"></a>')
            lines.append(f"#### {f.name.replace('_', ' ').title()}\n")
            if f.description:
                lines.append(f"{f.description}\n")
            else:
                lines.append("_No description available._\n")
            
            # Add validators for this field
            if f.name in validators_by_field:
                for v in validators_by_field[f.name]:
                    validator_id = f"{f.name}-{v['name']}"
                    lines.append(f'<details id="{validator_id}" open>')
                    source_link = f" <a href=\"{pydantic_url}\">[source]</a>" if pydantic_url else ""
                    lines.append(f"<summary><strong>Validation:</strong> {v['name']}{source_link}</summary>")
                    lines.append("")
                    if v['docstring']:
                        lines.append(f"{v['docstring']}")
                        lines.append("")
                    if v['source']:
                        lines.append(f"```python\n{v['source']}\n```")
                        lines.append("")
                    lines.append("</details>")
                    lines.append("")
        
        # Other Validations Section - for unassigned validators
        if unassigned_validators:
            lines.append("### Other Validations\n")
            for v in unassigned_validators:
                validator_id = f"other-{v['name']}"
                lines.append(f'<details id="{validator_id}" open>')
                source_link = f" <a href=\"{pydantic_url}\">[source]</a>" if pydantic_url else ""
                lines.append(f"<summary><strong>{v['name']}</strong>{source_link}</summary>")
                lines.append("")
                if v['docstring']:
                    lines.append(f"{v['docstring']}")
                    lines.append("")
                if v['source']:
                    lines.append(f"```python\n{v['source']}\n```")
                    lines.append("")
                lines.append("</details>")
                lines.append("")
        
        return '\n'.join(lines)
    
    def _format_references(self, references: list) -> str:
        """Format references as links to EMD items."""
        if not references:
            return "-"
        
        formatted = []
        for ref in references:
            # Convert to lowercase and link to EMD vocabulary
            ref_lower = ref.lower().replace(' ', '_')
            formatted.append(f"[`{ref}`](../{ref_lower}/)")
        
        return ", ".join(formatted)
    
    def _format_field(self, f: FieldInfo) -> list:
        """Format a single field entry with title, description, then properties table."""
        lines = []
        type_short = self._shorten_type(f.type_str)
        
        # Anchor and field header (title)
        lines.append(f'<a id="{f.name}"></a>')
        lines.append(f"#### `{f.name}`\n")
        
        # Description first
        if f.description:
            lines.append(f"{f.description}\n")
        
        # Build transposed table - headers are property names, values in second row
        headers = ["Type", "Required"]
        values = [f"`{type_short}`"]
        
        if f.required:
            values.append("![Yes](https://img.shields.io/badge/-Yes-blue)")
        else:
            values.append("![No](https://img.shields.io/badge/-No-grey)")
        
        if f.constraints:
            for k, v in f.constraints.items():
                headers.append(k)
                values.append(f"`{v}`")
        
        if f.references:
            refs_str = ", ".join(f"[`{r}`](#{r.lower()})" for r in f.references)
            headers.append("See also")
            values.append(refs_str)
        
        # Build table
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        lines.append("| " + " | ".join(values) + " |")
        
        lines.append("")
        return lines
    
    def _shorten_type(self, type_str: str) -> str:
        """Shorten long type strings by removing module paths."""
        # Remove full module paths like esgvoc.api.data_descriptors.EMD_models.arrangement.
        shortened = re.sub(r'esgvoc\.api\.data_descriptors\.[A-Za-z_\.]+\.([A-Za-z_]+)', r'\1', type_str)
        return shortened

    def _schema_from_keys(self) -> str:
        """Generate schema from JSON keys when no Pydantic model available."""
        filtered_keys = [k for k in self.vocab.keys if k not in CONFIG.skip_keys]
        sorted_keys = sort_keys(filtered_keys)
        
        lines = ["## Schema\n"]
        lines.append("*No Pydantic model available. Fields extracted from JSON files.*\n")
        lines.append("| Field | Type |")
        lines.append("|-------|------|")
        for key in sorted_keys:
            lines.append(f"| `{key}` | _unknown_ |")
        
        return '\n'.join(lines) + '\n'

    def generate_usage(self) -> str:
        """Generate the usage examples section."""
        example = self.vocab.example_file
        short = self.urls.get('short', f'{self.vocab.prefix}:{self.vocab.name}')
        io_url = self.urls.get('io', '')
        content_url = self.urls.get('content', '')
        
        return f'''## Usage

<details open>
<summary><strong>Online</strong></summary>

| Resource | Link |
|----------|------|
| **Direct JSON** | [{example}.json]({content_url}/{example}.json) |
| **Interactive Viewer** | [Open Viewer](https://wcrp-cmip.github.io/CMIPLD/viewer/index.html?uri={urllib.parse.quote(short, safe='')}/{example}) |
| **Full URL** | [{io_url}/{example}.json]({io_url}/{example}.json) |

</details>

<details>
<summary><strong>cmipld</strong></summary>

```python
import cmipld

# Fetch and resolve a single record
data = cmipld.get("{short}/{example}")
print(data)
```

</details>

<details>
<summary><strong>esgvoc</strong></summary>

```python
from esgvoc.api import search

# Search for terms in this vocabulary
results = search.find("{self.vocab.name}", term="{example}")
print(results)
```

</details>

<details>
<summary><strong>HTTP</strong></summary>

```python
import requests

url = "{io_url}/{example}.json"
response = requests.get(url)
data = response.json()
print(data)
```

</details>

<details>
<summary><strong>CLI / Node / Web</strong></summary>

```bash
# Install
npm install -g jsonld-recursive

# Compact a JSON-LD document
ldr compact {io_url}/{example}.json
```

</details>
'''

    def generate_dependencies(self, dependencies: list) -> str:
        """Generate the dependencies section."""
        if not dependencies:
            return ""
        
        # Group by prefix
        by_prefix = defaultdict(list)
        for dep in dependencies:
            by_prefix[dep.prefix].append(dep)
        
        lines = ["## Dependencies\n"]
        lines.append(f"This vocabulary references **{len(dependencies)} external vocabularies**:\n")
        
        for prefix in sorted(by_prefix.keys()):
            deps = by_prefix[prefix]
            lines.append(f"\n### `{prefix}:`\n")
            for dep in sorted(deps, key=lambda d: d.path):
                lines.append(f"- [`{dep.path}`]({dep.url})")
        
        return '\n'.join(lines) + '\n'

    def generate_full_readme(self, existing_description: str = "", dependencies: list = None) -> str:
        """Generate the complete README content."""
        sections = [
            self.generate_header(existing_description),
            self.generate_info_table(),
            self.generate_schema(),
            self.generate_usage(),
        ]
        
        if dependencies:
            sections.insert(4, self.generate_dependencies(dependencies))
        
        return '\n---\n\n'.join(filter(None, sections))


def sort_fields(fields: list) -> list:
    """Sort fields with priority ordering."""
    priority = list(CONFIG.priority_keys)
    
    def key_func(f):
        if f.name in priority:
            return (0, priority.index(f.name))
        return (1, f.name)
    
    return sorted(fields, key=key_func)


# =============================================================================
# Main Processing
# =============================================================================

def process_directory(vocab_dir: Path, prefix: str, base_urls: dict) -> Optional[str]:
    """Process a single vocabulary directory and generate README."""
    name = vocab_dir.name
    
    # Skip configured directories
    if name in CONFIG.skip_directories:
        print(f"  Skipping '{name}' (in skip list)")
        return None
    
    # Only process directories with _context file
    context_file = vocab_dir / '_context'
    if not context_file.exists():
        print(f"  Skipping '{name}' (no _context file)")
        return None
    
    # Find JSON files (exclude files starting with _)
    json_files = [f.name for f in vocab_dir.glob('*.json') if not f.name.startswith('_')]
    if not json_files:
        print(f"  Skipping '{name}' (no JSON files)")
        return None
    
    # Build vocab info
    vocab = VocabInfo(
        name=name,
        path=vocab_dir,
        prefix=prefix,
        json_files=json_files,
        keys=extract_json_keys(vocab_dir),
    )
    
    # Find Pydantic model
    model_name, model_class, file_path, class_doc, module_doc = find_pydantic_model(name)
    vocab.pydantic_model = model_name
    vocab.pydantic_class = model_class
    vocab.pydantic_file_path = file_path
    vocab.model_docstring = class_doc
    vocab.module_docstring = module_doc
    
    # Extract detailed field info and validators if we have a pydantic model
    if model_class:
        vocab.fields = extract_field_info(model_class)
        vocab.validators = extract_validators(model_class)
        if vocab.validators:
            print(f"    Found {len(vocab.validators)} validators")
        else:
            print(f"    No validators found")
    
    # Build URLs
    urls = build_urls(vocab_dir, prefix, name, base_urls)
    
    # Get existing description (only if no pydantic docstring)
    readme_path = vocab_dir / 'README.md'
    existing_description = ""
    if not vocab.description:
        existing_description = extract_description_from_readme(readme_path) or ""
    
    # Analyze dependencies (if cmipld available)
    dependencies = []
    if CMIPLD_AVAILABLE:
        dependencies = analyze_dependencies(vocab.type_uri, prefix)
    
    # Generate README
    generator = MarkdownGenerator(vocab, urls)
    readme_content = generator.generate_full_readme(existing_description, dependencies)
    
    # Write README
    readme_path.write_text(readme_content, encoding='utf-8')
    print(f"  ✓ Created README for '{name}'")
    
    return name


def build_urls(vocab_dir: Path, prefix: str, name: str, base_urls: dict) -> dict:
    """Build URL dictionary for a vocabulary."""
    urls = {}
    
    if CMIPLD_AVAILABLE:
        try:
            content_url = get_path_url(str(vocab_dir)).replace('wolfiex', CONFIG.github_org.lower())
            # Ensure we use src-data branch for direct GitHub links
            if '/tree/main/' in content_url:
                content_url = content_url.replace('/tree/main/', '/tree/src-data/')
            elif '/blob/main/' in content_url:
                content_url = content_url.replace('/blob/main/', '/blob/src-data/')
            
            repo_url = get_repo_url().replace('wolfiex', CONFIG.github_org.lower())
            rel_path = get_relative_path(str(vocab_dir))
            
            # Build mipcvs.dev URL
            io_url = f"https://{prefix}.mipcvs.dev/{name}"
            short = f"{prefix}:{name}"
            
            urls = {
                'content': content_url,
                'repo': repo_url,
                'io': io_url,
                'short': short,
            }
        except Exception as e:
            print(f"  Warning: Could not build URLs: {e}")
    
    # Fallbacks
    if not urls:
        base = base_urls.get('base', f'https://{CONFIG.github_org.lower()}.github.io')
        urls = {
            'content': f'{base}/{name}',
            'io': f'{base}/{name}',
            'short': f'{prefix}:{name}',
        }
    
    return urls


def analyze_dependencies(type_uri: str, self_prefix: str) -> list:
    """Analyze external dependencies for a vocabulary."""
    dependencies = []
    
    if not CMIPLD_AVAILABLE:
        return dependencies
    
    # Check if depends function exists
    if not hasattr(cmipld, 'depends'):
        print("  ⚠ Dependency analysis unavailable: cmipld.depends() not found.")
        print("    TODO: Update jsonld-recursive to load local files from the calling directory.")
        return dependencies
    
    try:
        graph_url = f'{type_uri}/graph.jsonld'
        all_deps = cmipld.depends(graph_url, prefix=True)
        
        # Filter to external only
        last_segment = re.compile(r'/[^/]+$')
        for dep in all_deps:
            if not dep.startswith(self_prefix):
                clean_dep = last_segment.sub('', dep)
                if ':' in clean_dep:
                    prefix, path = clean_dep.split(':', 1)
                    base_url = cmipld.mapping.get(prefix, '')
                    dependencies.append(ExternalDependency(
                        prefix=prefix,
                        path=path,
                        url=f"{base_url}{path}/"
                    ))
    except Exception:
        pass
    
    # Deduplicate
    seen = set()
    unique = []
    for dep in dependencies:
        key = dep.full_ref
        if key not in seen:
            seen.add(key)
            unique.append(dep)
    
    return unique


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate README files for WCRP vocabulary directories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s                          # Run in current directory
  %(prog)s /path/to/src-data        # Run in specified directory
  %(prog)s --prefix universal       # Override prefix
  %(prog)s --dry-run                # Preview without writing
        '''
    )
    parser.add_argument('directory', nargs='?', default='.', help='Directory containing vocabulary subdirectories (default: current directory)')
    parser.add_argument('--prefix', help='Override the prefix (auto-detected via cmipld.prefix() if not specified)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without writing files')
    
    args = parser.parse_args()
    
    directory = Path(args.directory).resolve()
    if not directory.exists():
        print(f"Error: Directory '{directory}' does not exist")
        sys.exit(1)
    
    # Change to the target directory
    original_dir = Path.cwd()
    os.chdir(directory)
    
    # Detect prefix using cmipld.prefix()
    prefix = args.prefix
    if not prefix and CMIPLD_AVAILABLE:
        try:
            prefix = cmipld.prefix()
            print(f"Auto-detected prefix: {prefix}")
        except Exception as e:
            print(f"Warning: Could not auto-detect prefix: {e}")
            prefix = 'unknown'
    prefix = prefix or 'unknown'
    
    print(f"Processing vocabularies in: {directory}")
    print(f"Using prefix: {prefix}")
    print(f"Libraries: cmipld={'✓' if CMIPLD_AVAILABLE else '✗'}, esgvoc={'✓' if ESGVOC_AVAILABLE else '✗'}")
    print("-" * 50)
    
    # Process each subdirectory in the current level
    base_urls = {'base': cmipld.mapping.get(prefix, '') if CMIPLD_AVAILABLE else ''}
    
    processed = []
    missing_pydantic = []
    
    for vocab_dir in sorted(directory.iterdir()):
        if not vocab_dir.is_dir() or vocab_dir.name.startswith('.'):
            continue
        
        print(f"\nProcessing: {vocab_dir.name}")
        
        if args.dry_run:
            context_exists = (vocab_dir / '_context').exists()
            status = "✓ has _context" if context_exists else "✗ no _context"
            print(f"  [DRY RUN] {status}")
            continue
        
        result = process_directory(vocab_dir, prefix, base_urls)
        if result:
            processed.append(result)
            # Track missing pydantic models
            model_name, _, _, _, _ = find_pydantic_model(vocab_dir.name)
            if not model_name:
                missing_pydantic.append(vocab_dir.name)
    
    # Return to original directory
    os.chdir(original_dir)
    
    # Summary
    print("\n" + "=" * 50)
    print(f"Processed: {len(processed)} vocabularies")
    
    if missing_pydantic:
        print(f"\nMissing Pydantic models ({len(missing_pydantic)}):")
        for name in missing_pydantic:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
