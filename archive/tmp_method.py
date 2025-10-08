    def extract_links_from_item_with_resolution(self, item: Dict[str, Any], item_id: str, folder_prefix: str) -> Tuple[Set[str], Dict[str, Set[str]]]:
        """Extract links from a single file (id) in graph.jsonld using RDF analysis."""
        links = set()
        property_links = defaultdict(set)
        
        try:
            from pyld import jsonld
            
            print(f"🔍 Extracting links from file: {item_id}")
            print(f"   Item keys: {list(item.keys())}")
            print(f"   Item sample: {dict(list(item.items())[:3])}")
            
            # Check if item has @context
            if '@context' not in item:
                print(f"   ⚠️  No @context in item - adding context for RDF conversion")
                print(f"   Available contexts: {list(cmipld.mapping.keys())}")
                
                # Add context based on folder prefix
                item_with_context = dict(item)
                if folder_prefix in cmipld.mapping:
                    item_with_context['@context'] = cmipld.mapping[folder_prefix]
                    print(f"   Added context: {cmipld.mapping[folder_prefix]}")
                else:
                    print(f"   No context available for prefix: {folder_prefix}")
                    return self.extract_links_from_item_fallback(item)
            else:
                item_with_context = item
                print(f"   Using existing context: {item.get('@context')}")
            
            # Convert this individual item to RDF triples
            print(f"   Converting to RDF...")
            rdf_dataset = jsonld.to_rdf(item_with_context)
            
            print(f"   RDF dataset keys: {list(rdf_dataset.keys())}")
            
            # Process ALL triples to find IRI objects (links)
            total_triples = 0
            iri_objects = 0
            
            for graph_name, triples in rdf_dataset.items():
                print(f"   Processing graph: {graph_name} with {len(triples)} triples")
                
                for triple in triples:
                    total_triples += 1
                    subject_uri = triple['subject']['value']
                    predicate_uri = triple['predicate']['value']
                    object_val = triple['object']['value']
                    object_type = triple['object']['type']
                    
                    if total_triples <= 5:  # Show first 5 triples for debugging
                        print(f"     Triple {total_triples}: {predicate_uri} -> {object_val} (type: {object_type})")
                    
                    # Process ALL IRI objects as potential links
                    if object_type == 'IRI':
                        iri_objects += 1
                        property_name = self._uri_to_property_name(predicate_uri)
                        
                        print(f"     Found IRI link: {property_name} -> {object_val}")
                        
                        # Test if the link is fetchable using cmipld.get(depth=0)
                        if self.is_link_fetchable(object_val):
                            links.add(object_val)
                            if property_name and property_name != 'type':  # Skip rdf:type
                                property_links[property_name].add(object_val)
                            print(f"       ✅ Link VALID and FETCHED")
                        else:
                            print(f"       💔 Link BROKEN - cmipld.get failed")
            
            print(f"   Total triples: {total_triples}, IRI objects: {iri_objects}")
            print(f"📋 Final results for {item_id}: {len(links)} valid links, {len(property_links)} property mappings")
            
            return links, dict(property_links)
            
        except Exception as e:
            print(f"❌ RDF analysis failed for {item_id}: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to direct parsing
            return self.extract_links_from_item_fallback(item)
