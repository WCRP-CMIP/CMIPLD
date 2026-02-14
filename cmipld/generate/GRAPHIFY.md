# Graphify - CMIP-LD Graph Generation Tool

**Location:** `cmipld/generate/graphify.py`

Graphify is a command-line tool and Python module for generating semantic web artifacts and visualization data from CMIP-LD vocabulary directories.

## Overview

Graphify processes vocabulary directories (those containing `_context.json` or `_context` files) and generates:

1. **JSON-LD Graph Files** (`_graph.jsonld`) - Collection documents listing all entities
2. **RDF/Turtle Files** (`_graph.ttl`) - Semantic web format for SPARQL queries
3. **D3/Graphology Visualization JSON** - For interactive graph visualizations

## Generated Files

### Per-Directory Files

| File | Description |
|------|-------------|
| `_graph.jsonld` | JSON-LD Collection containing references to all entities in the directory |
| `_graph.ttl` | RDF/Turtle serialization of the expanded JSON-LD graph |

### Repository-Level Files

| File | Description |
|------|-------------|
| `_d3graph.json` | Entity-level graph for D3.js/Graphology/Sigma.js visualization |
| `_d3structure.json` | Folder-level structure graph showing relationships between entity types |

## Usage

### Command Line

```bash
# Process all vocabulary directories
graphify --all

# Process specific directory
graphify --dir model_family

# Process multiple directories
graphify model_family model_component model

# Skip RDF generation (faster, JSON-LD only)
graphify --all --no-rdf

# Skip visualization generation
graphify --all --no-viz

# Quiet mode (minimal output)
graphify --all --quiet

# GitHub Actions with summary output
graphify --all --output-summary
```

### Python API

```python
from cmipld.generate.graphify import (
    find_vocab_directories,
    generate_jsonld_graph,
    generate_rdf_turtle,
    generate_d3_graph,
    generate_d3_structure,
    process_all
)

# Process everything
results = process_all()

# Process specific directory
from pathlib import Path
result = generate_jsonld_graph(Path("model_family"))

# Generate visualization only
from cmipld.generate.graphify import extract_relationships
relationships = extract_relationships(rdf_graphs, prefix)
generate_d3_graph(relationships, prefix, colors, Path("_d3graph.json"))
```

## Processing Steps

### 1. JSON-LD Graph Generation

For each vocabulary directory:

1. Load the `_context.json` file
2. Scan all `.json` files (excluding those starting with `_`)
3. Extract `@id` from each entity
4. Create a Collection document with references to all entities
5. Write `_graph.jsonld`

**Output Format:**
```json
{
  "@context": { ... },
  "@type": ["Collection"],
  "contents": [
    {"@id": "https://emd.mipcvs.dev/model/CESM2"},
    {"@id": "https://emd.mipcvs.dev/model/HadGEM3-GC31-LL"}
  ]
}
```

### 2. RDF/Turtle Generation

For each vocabulary directory with a JSON-LD graph:

1. Expand the JSON-LD using `cmipld.expand()` with depth=3
2. Add vocabulary namespace bindings
3. Parse into an RDF graph using rdflib
4. Serialize to Turtle format
5. Write `_graph.ttl`

**Requirements:**
- `cmipld` package with LDR client
- `rdflib` package

### 3. Relationship Extraction

From all RDF graphs:

1. Iterate over all triples (subject, predicate, object)
2. Filter out W3C predicates (`www.w3.org`)
3. Keep only relationships between internal entities (`mipcvs.dev`)
4. Shorten URIs to prefixed form (e.g., `emd:model/CESM2`)

### 4. D3 Graph Generation (`_d3graph.json`)

Entity-level visualization graph:

1. Create a node for each unique subject and object
2. Create an edge for each relationship
3. Color internal nodes with project primary color
4. Color external nodes grey

**Output Format (D3/Graphology compatible):**
```json
{
  "nodes": [
    {"id": "emd:model/CESM2", "label": "CESM2", "color": "#2196f3"}
  ],
  "links": [
    {"source": "emd:model/CESM2", "target": "emd:model_family/CESM", "label": "emd:family", "color": "#bbdefb"}
  ]
}
```

### 5. D3 Structure Generation (`_d3structure.json`)

Folder-level structure visualization:

1. Create a root node for the project
2. Create nodes for each folder/entity type
3. Connect folders to root with "contains" edges
4. Count inter-folder relationships
5. Create weighted edges between folders

**Output Format:**
```json
{
  "nodes": [
    {"id": "root", "label": "EMD", "color": "#1976d2", "size": 30},
    {"id": "emd:model", "label": "model", "color": "#bbdefb", "size": 15}
  ],
  "links": [
    {"source": "root", "target": "emd:model", "label": "contains"},
    {"source": "emd:model", "target": "emd:model_family", "label": "15 links", "weight": 15}
  ],
  "directed": true,
  "multigraph": true
}
```

## Color Configuration

Colors are extracted from the project's CSS file at `docs/stylesheets/custom.css`:

```css
:root {
  --emd-primary: #2196f3;
  --emd-primary-light: #bbdefb;
  --emd-primary-dark: #1976d2;
}
```

If no CSS is found, Material Design Blue defaults are used.

## GitHub Actions Integration

Add to your workflow:

```yaml
- name: Generate graphs
  run: |
    pip install cmipld rdflib
    graphify --all --output-summary
```

The `--output-summary` flag writes a formatted report to `$GITHUB_STEP_SUMMARY`.

## Visualization

The generated JSON files are compatible with:

- **D3.js** force-directed graphs
- **Graphology** graph library
- **Sigma.js** WebGL graph renderer
- **NetworkX** (Python) via `nx.node_link_graph()`
- **ipysigma** (Jupyter) for interactive exploration

### Example: Jupyter Preview

```python
import json
import networkx as nx
from ipysigma import Sigma

data = json.load(open('_d3structure.json'))
G = nx.node_link_graph(data)
Sigma(G, node_color='color', edge_color='color', height=700)
```

## Dependencies

**Required:**
- Python 3.8+
- `cmipld` package

**Optional (for full functionality):**
- `rdflib` - RDF/Turtle generation
- `networkx` - Graph analysis
- `ipysigma` - Jupyter visualization

## Related Utilities

- `cmipld.utils.styling` - Color extraction and URI shortening utilities
- `cmipld.generate.template_generator` - Issue template generation
- `cmipld.generate.template_prefill` - Prefill link generation
