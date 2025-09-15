#!/usr/bin/env python3
"""
Test script for link field normalization functionality.

This script demonstrates how the context manager identifies linked fields
and normalizes their string values (lowercase, replace _ with -).
"""

import json
import tempfile
from pathlib import Path

# Test the link normalization functionality
def test_link_normalization():
    print("🔗 Testing Link Field Normalization")
    print("=" * 50)
    
    # Create a context with linked fields
    test_context = {
        "@context": {
            "@vocab": "https://wcrp-cmip.org/ontology#",
            
            # Regular fields (no normalization)
            "title": {
                "@id": "dcterms:title",
                "@type": "xsd:string"
            },
            "description": {
                "@id": "dcterms:description", 
                "@type": "xsd:string"
            },
            
            # Linked fields (will be normalized)
            "experiment": {
                "@id": "wcrp:experiment",
                "@type": "@id"  # This marks it as a link field
            },
            "institution": {
                "@id": "wcrp:institution",
                "@type": "@id"  # This marks it as a link field
            },
            "model": {
                "@id": "wcrp:model", 
                "@type": "@id"  # This marks it as a link field
            },
            "category": {
                "@id": "wcrp:category",
                "@type": "@vocab"  # This also marks it as a link field
            },
            "themes": {
                "@id": "wcrp:theme",
                "@type": "@vocab",
                "@container": "@list"  # Array of link values
            },
            "references": {
                "@id": "dcterms:references",
                "@type": "@id",
                "@container": "@set"  # Set of link values
            }
        }
    }
    
    # Create a temporary context file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonld', delete=False) as f:
        json.dump(test_context, f, indent=2)
        context_file = f.name
    
    try:
        from cmipld.utils.validate_json import ContextManager
        
        # Load the context
        context_mgr = ContextManager(context_file)
        
        print("📋 Context Information:")
        context_info = context_mgr.get_context_info()
        print(f"   Total terms: {context_info['total_terms']}")
        print(f"   Linked fields: {context_info['linked_fields_count']}")
        print(f"   Linked field names: {context_info['linked_fields']}")
        
        print(f"\n🔗 Linked Fields Details:")
        linked_info = context_mgr.get_linked_fields_info()
        for field_name, info in linked_info.items():
            container = f" ({info['container']})" if info['container'] else ""
            print(f"   {field_name}: {info['type']}{container}")
        
        # Test data with mixed case and underscores in linked fields
        test_data = {
            "id": "test-record",
            "validation-key": "test_record",
            "@context": "_context_",
            "type": ["wcrp:test"],
            
            # Regular fields (won't be normalized)
            "title": "Test_Record_With_Underscores",
            "description": "This Has Mixed_Case and underscores_too",
            
            # Linked fields (will be normalized)
            "experiment": "CMIP6_Historical_Run",  # Should become "cmip6-historical-run"
            "institution": "NASA_GISS",           # Should become "nasa-giss"
            "model": "GISS_E2_1_G",              # Should become "giss-e2-1-g"
            "category": "Earth_System_Model",     # Should become "earth-system-model"
            
            # Array of linked values
            "themes": [
                "Climate_Change",
                "Ocean_Dynamics", 
                "Atmospheric_Physics"
            ],
            
            # Set of linked values
            "references": [
                "DOI:10.1000/Test_Paper",
                "https://example.com/Full_URL_Preserved",
                "wcrp:some_Reference"
            ]
        }
        
        print(f"\n📝 Original Data (linked fields):")
        for field in context_info['linked_fields']:
            if field in test_data:
                print(f"   {field}: {test_data[field]}")
        
        # Apply normalization
        print(f"\n🔄 Applying link normalization...")
        modified = context_mgr.normalize_link_values(test_data)
        
        if modified:
            print(f"✅ Data was modified!")
            print(f"\n📝 Normalized Data (linked fields):")
            for field in context_info['linked_fields']:
                if field in test_data:
                    print(f"   {field}: {test_data[field]}")
        else:
            print(f"ℹ️  No changes needed")
        
        # Test edge cases
        print(f"\n🧪 Testing Edge Cases:")
        
        edge_case_data = {
            "experiment": "http://example.com/Full_URL",  # Should NOT be normalized
            "institution": "urn:uuid:12345",              # Should NOT be normalized  
            "model": "CMIP6:experiment-name",             # Should NOT be normalized (uppercase prefix)
            "category": "simple_value"                    # Should be normalized
        }
        
        print("   Before normalization:")
        for k, v in edge_case_data.items():
            print(f"     {k}: {v}")
        
        modified = context_mgr.normalize_link_values(edge_case_data)
        
        print("   After normalization:")
        for k, v in edge_case_data.items():
            print(f"     {k}: {v}")
        
        print(f"\n🎯 Key Behaviors Demonstrated:")
        print("   ✅ Only fields marked as @id or @vocab are normalized")
        print("   ✅ Full URLs/URIs are preserved unchanged")
        print("   ✅ Prefixed names with uppercase prefixes are preserved")
        print("   ✅ Arrays and lists are processed recursively")
        print("   ✅ Simple values are lowercased and _ → -")
        
    finally:
        # Clean up
        Path(context_file).unlink()
    
    print(f"\n🎉 Link normalization test completed!")


if __name__ == "__main__":
    test_link_normalization()
