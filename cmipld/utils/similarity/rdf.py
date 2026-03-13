"""
RDF Link Analysis

Compare JSON-LD items by their URI/link structure (not values).
Shows which items reference the same external entities.

Usage:
    import cmipld
    from cmipld.utils.similarity.rdf import RDFLinkAnalyzer
    
    # Expand data
    data = cmipld.expand('emd:horizontal_grid_cells/_graph.json', depth=2)
    
    # Analyze
    analyzer = RDFLinkAnalyzer(data)
    
    # Get results
    pairs = analyzer.get_pairs(threshold=80.0)      # [[id1, id2, percentage], ...]
    links = analyzer.get_links(id1)                # {id1: [links]}
    diff = analyzer.compare_pair(id1, id2)        # Link differences
"""

from typing import Dict, List, Set, Tuple, Optional
import json
from pathlib import Path


class RDFLinkAnalyzer:
    """
    Analyze JSON-LD data by comparing URI/link structure.
    
    Ignores values - only looks at @id references.
    """
    
    def __init__(self, data: dict):
        """
        Initialize with expanded JSON-LD data.
        
        Args:
            data: JSON-LD collection (dict with 'contents' or similar key)
        """
        self.raw_data = data
        self.items = {}
        self.links = {}
        self.ids = []
        
        self._extract_items()
        self._extract_links()
    
    def _extract_items(self):
        """Extract items from collection."""
        contents_key = None
        for key in self.raw_data.keys():
            if 'contents' in key.lower():
                contents_key = key
                break
        
        if not contents_key:
            raise ValueError("No 'contents' key found in data")
        
        items_list = self.raw_data[contents_key]
        
        if not isinstance(items_list, list):
            raise ValueError("Contents must be a list")
        
        for i, item in enumerate(items_list):
            item_id = item.get('@id', f'item_{i}')
            short_id = item_id.split('/')[-1] if '/' in item_id else item_id
            
            self.items[short_id] = item
            self.ids.append(short_id)
    
    def _extract_links(self):
        """Extract @id references from each item."""
        for item_id, item in self.items.items():
            links = self._get_item_links(item)
            self.links[item_id] = links
    
    def _get_item_links(self, item: dict) -> Set[str]:
        """
        Extract all @id references from an item.
        
        Returns set of URI strings.
        """
        links = set()
        
        def traverse(obj, exclude_keys={'@value', 'ui_label'}):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if k in exclude_keys:
                        continue
                    
                    if k == '@id' and isinstance(v, str):
                        links.add(v)
                    
                    elif isinstance(v, (dict, list)):
                        traverse(v, exclude_keys)
            
            elif isinstance(obj, list):
                for elem in obj:
                    traverse(elem, exclude_keys)
        
        traverse(item)
        return links
    
    def _link_similarity_percentage(self, links1: Set[str], links2: Set[str]) -> float:
        """
        Calculate link similarity as percentage of common links.
        
        Returns:
            0.0 to 100.0 percentage
        """
        if not links1 and not links2:
            return 100.0
        
        if not links1 or not links2:
            return 0.0
        
        intersection = len(links1 & links2)
        union = len(links1 | links2)
        
        return (intersection / union) * 100.0 if union > 0 else 0.0
    
    def get_pairs(self, threshold: float = 80.0) -> List[List]:
        """
        Get all item pairs with link similarity above threshold.
        
        Args:
            threshold: Minimum percentage (0-100, default 80%)
        
        Returns:
            [[id1, id2, percentage], ...] sorted by percentage descending
        """
        pairs = []
        
        for i in range(len(self.ids)):
            for j in range(i + 1, len(self.ids)):
                id1 = self.ids[i]
                id2 = self.ids[j]
                
                sim = self._link_similarity_percentage(
                    self.links[id1],
                    self.links[id2]
                )
                
                if sim >= threshold:
                    pairs.append([id1, id2, round(sim, 1)])
        
        pairs.sort(key=lambda x: x[2], reverse=True)
        return pairs
    
    def get_links(self, item_id: str) -> Dict[str, list]:
        """
        Get links for an item.
        
        Args:
            item_id: Item identifier
        
        Returns:
            {item_id: [link1, link2, ...]}
        """
        if item_id not in self.links:
            raise ValueError(f"Item '{item_id}' not found")
        
        return {item_id: sorted(self.links[item_id])}
    
    def compare_pair(self, id1: str, id2: str) -> Dict:
        """
        Compare links between two items in detail.
        
        Args:
            id1: First item ID
            id2: Second item ID
        
        Returns:
            {
                'id1': str,
                'id2': str,
                'similarity_percent': float,
                'common_links': [links],
                'only_in_id1': [links],
                'only_in_id2': [links],
                'total_links_id1': int,
                'total_links_id2': int,
            }
        """
        if id1 not in self.links or id2 not in self.links:
            raise ValueError(f"Item not found")
        
        links1 = self.links[id1]
        links2 = self.links[id2]
        
        common = links1 & links2
        only1 = links1 - links2
        only2 = links2 - links1
        
        sim = self._link_similarity_percentage(links1, links2)
        
        return {
            'id1': id1,
            'id2': id2,
            'similarity_percent': round(sim, 1),
            'common_links': sorted(common),
            'only_in_id1': sorted(only1),
            'only_in_id2': sorted(only2),
            'total_links_id1': len(links1),
            'total_links_id2': len(links2),
            'common_count': len(common),
        }
    
    def get_summary(self) -> Dict:
        """
        Get summary of all items and their link counts.
        
        Returns:
            {
                'total_items': int,
                'items': {id: link_count, ...},
                'total_unique_links': int,
            }
        """
        all_links = set()
        for links in self.links.values():
            all_links.update(links)
        
        return {
            'total_items': len(self.items),
            'items': {item_id: len(self.links[item_id]) for item_id in self.ids},
            'total_unique_links': len(all_links),
        }
    
    def get_groups(self, threshold: float = 80.0) -> Dict[int, List[str]]:
        """
        Group items by link similarity (transitive closure).
        
        Args:
            threshold: Minimum percentage (0-100)
        
        Returns:
            {group_id: [item_ids], ...}
        """
        pairs = self.get_pairs(threshold=threshold)
        
        parent = {}
        
        def find(x):
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        for id1, id2, _ in pairs:
            union(id1, id2)
        
        groups_dict = {}
        for item_id in self.ids:
            root = find(item_id)
            if root not in groups_dict:
                groups_dict[root] = []
            groups_dict[root].append(item_id)
        
        groups = {}
        gid = 0
        for root in sorted(groups_dict.keys()):
            members = groups_dict[root]
            if len(members) > 1:
                groups[gid] = sorted(members)
                gid += 1
        
        return groups
    
    def to_json(self) -> Dict:
        """
        Export analysis results as JSON-serializable dict.
        
        Returns:
            {
                'summary': {...},
                'pairs': [[id1, id2, percentage], ...],
                'groups': {group_id: [items], ...},
                'links_by_item': {id: [links], ...},
            }
        """
        return {
            'summary': self.get_summary(),
            'pairs': self.get_pairs(threshold=0.0),
            'groups': self.get_groups(threshold=80.0),
            'links_by_item': {
                item_id: sorted(self.links[item_id])
                for item_id in self.ids
            },
        }
    
    def print_summary(self):
        """Print human-readable summary."""
        summary = self.get_summary()
        
        print("\n" + "="*70)
        print("RDF LINK ANALYSIS SUMMARY")
        print("="*70)
        
        print(f"\nTotal items: {summary['total_items']}")
        print(f"Total unique links: {summary['total_unique_links']}\n")
        
        print("Links per item:")
        for item_id in sorted(self.ids):
            count = summary['items'][item_id]
            print(f"  {item_id:20} {count:3} links")
        
        pairs = self.get_pairs(threshold=80.0)
        if pairs:
            print(f"\nSimilar pairs (>80%): {len(pairs)}")
            for id1, id2, sim in pairs[:10]:
                print(f"  {id1:15} ↔ {id2:15} {sim:5.1f}%")
            if len(pairs) > 10:
                print(f"  ... and {len(pairs) - 10} more")
        
        groups = self.get_groups(threshold=80.0)
        if groups:
            print(f"\nGroups (transitive similar): {len(groups)}")
            for gid, members in groups.items():
                print(f"  Group {gid}: {members}")
        
        print("\n" + "="*70)
