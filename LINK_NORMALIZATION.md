## Link Field Normalization Feature

### Overview

The enhanced JSON-LD validator now includes **automatic link field normalization** based on context definitions. This feature identifies fields that contain links or references (marked with `@type: "@id"` or `@type: "@vocab"` in the context) and automatically normalizes their string values.

### What Gets Normalized

**Fields marked as linked in context:**
- `@type: "@id"` - Fields containing IRIs/URLs/references  
- `@type: "@vocab"` - Fields containing vocabulary terms

**Normalization rules:**
- Convert to lowercase
- Replace underscores (`_`) with hyphens (`-`)
- Process strings, arrays of strings, and nested structures

**What is NOT normalized:**
- Full URLs/URIs (http://, https://, urn:, mailto:)
- Prefixed names with uppercase prefixes (e.g., "CMIP6:experiment")
- Fields not marked as linked in the context
- Non-string values

### Example

**Context definition:**
```json
{
  "@context": {
    "experiment": {
      "@id": "wcrp:experiment",
      "@type": "@id"
    },
    "title": {
      "@id": "dcterms:title", 
      "@type": "xsd:string"
    }
  }
}
```

**Before normalization:**
```json
{
  "experiment": "CMIP6_Historical_Run",
  "title": "My_Test_Title"
}
```

**After normalization:**
```json
{
  "experiment": "cmip6-historical-run",  ← normalized (linked field)
  "title": "My_Test_Title"              ← unchanged (not linked)
}
```

### Usage

**Automatic (when using context file):**
```bash
python -m cmipld.utils.validate_json . --context context.jsonld
```

**Programmatic:**
```python
from cmipld.utils.validate_json import ContextManager

context_mgr = ContextManager('context.jsonld')
linked_fields = context_mgr.get_linked_fields()
modified = context_mgr.normalize_link_values(data)
```

### Test Script

Run the test script to see link normalization in action:
```bash
python test_links.py
```

This feature ensures consistent formatting of linked field values across CMIP-LD files while preserving the integrity of full URIs and intentionally formatted identifiers.
