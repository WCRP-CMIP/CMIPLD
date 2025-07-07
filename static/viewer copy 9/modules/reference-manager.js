// Reference collection and linking
import { Utils } from './utils.js';

export class ReferenceManager {
  constructor(prefixMapping) {
    this.prefixMapping = prefixMapping;
    this.resolvedContext = {};
    this.linkProperties = new Set();
  }

  // Set the resolved context for link detection
  setResolvedContext(context) {
    this.resolvedContext = context;
    this.linkProperties = this.identifyLinkProperties(context);
    // Also create a reverse mapping from expanded URIs to compacted names
    this.expandedToCompactMap = this.createExpandedToCompactMap(context);
    // Reduced logging - only log summary
    if (this.linkProperties.size > 0) {
      console.warn(`🔗 Link properties identified: ${Array.from(this.linkProperties).join(', ')}`);
    }
  }

  // Identify properties that are defined as links in the context
  identifyLinkProperties(context) {
    const linkProps = new Set();
    
    for (const [key, value] of Object.entries(context)) {
      // Skip 'id' field - never treat it as a link property
      if (key === 'id') {
        continue;
      }
      
      if (value === '@id') {
        linkProps.add(key);
      } else if (typeof value === 'object' && value !== null) {
        if (value['@type'] === '@id') {
          linkProps.add(key);
        }
      }
    }
    
    return linkProps;
  }

  // Mark a property as a link property
  markAsLinkProperty(propertyName) {
    if (!this.linkProperties) {
      this.linkProperties = new Set();
    }
    this.linkProperties.add(propertyName);
    console.log(`🔗 Marked '${propertyName}' as a link property`);
  }

  // Create a mapping from expanded URIs to compacted names
  createExpandedToCompactMap(context) {
    const map = new Map();
    
    for (const [key, value] of Object.entries(context)) {
      if (typeof value === 'string') {
        map.set(value, key);
      } else if (typeof value === 'object' && value !== null && value['@id']) {
        map.set(value['@id'], key);
      }
    }
    
    return map;
  }

  // Check if a key (compacted or expanded) represents a linked property
  isLinkedProperty(key) {
    // Direct check for compacted names
    if (this.linkProperties && this.linkProperties.has(key)) {
      return true;
    }
    
    // Check if this is an expanded URI that maps to a linked property
    if (this.expandedToCompactMap && this.expandedToCompactMap.has(key)) {
      const compactedName = this.expandedToCompactMap.get(key);
      return this.linkProperties.has(compactedName);
    }
    
    return false;
  }

  // Expand a reference using context with proper priority and correct prefix resolution
  expandReference(value, key = null) {
    if (!value || typeof value !== 'string') return value;
    
    // Already a full URL
    if (value.startsWith('http')) return value;
    
    // PRIORITY 1: Handle prefixed values FIRST (before property-scoped contexts)
    // This ensures "universal:activity/cmip" is resolved correctly
    if (value.includes(':')) {
      const colonIndex = value.indexOf(':');
      const prefix = value.substring(0, colonIndex);
      const suffix = value.substring(colonIndex + 1);
      
      console.log(`🔗 Processing prefixed reference: prefix='${prefix}', suffix='${suffix}'`);
      
      // Check context for prefix mapping first
      if (this.resolvedContext && this.resolvedContext[prefix]) {
        const prefixMapping = this.resolvedContext[prefix];
        if (typeof prefixMapping === 'string') {
          const expanded = prefixMapping + suffix;
          console.log(`🔗 Expanding prefixed reference '${value}' using context prefix '${prefix}': ${expanded}`);
          return expanded;
        }
      }
      
      // Check global prefix mappings
      if (this.prefixMapping.hasOwnProperty(prefix)) {
        const expanded = Utils.resolvePrefix(value, this.prefixMapping);
        console.log(`🔗 Expanding prefixed reference '${value}' using global prefix '${prefix}': ${expanded}`);
        return expanded;
      }
      
      console.log(`⚠️ No prefix mapping found for '${prefix}' in reference '${value}'`);
    }
    
    // PRIORITY 2: Check if this property has its own resolved context (for non-prefixed values)
    if (key && this.resolvedContext && this.resolvedContext[key] && typeof this.resolvedContext[key] === 'object') {
      const propertyDef = this.resolvedContext[key];
      
      // Check if we have a resolved property-specific context
      if (propertyDef['@resolvedContext']) {
        const propContext = propertyDef['@resolvedContext'];
        console.log(`🔗 Using resolved property-specific context for '${key}' to expand '${value}'`);
        
        // Check for exact mapping in property context
        if (propContext[value]) {
          const mapping = propContext[value];
          if (typeof mapping === 'string') {
            console.log(`🔗 Expanding reference '${value}' using property-specific direct mapping: ${mapping}`);
            return mapping;
          } else if (typeof mapping === 'object' && mapping !== null && mapping['@id']) {
            console.log(`🔗 Expanding reference '${value}' using property-specific object mapping: ${mapping['@id']}`);
            return mapping['@id'];
          }
        }
        
        // Use property-specific base/vocab
        const propBase = propContext['@base'];
        const propVocab = propContext['@vocab'];
        
        if (propBase && !value.startsWith('/')) {
          const expanded = propBase + (propBase.endsWith('/') ? '' : '/') + value;
          console.log(`🔗 Expanding '${value}' using property-specific @base: ${expanded}`);
          return expanded;
        } else if (propVocab) {
          const expanded = propVocab + value;
          console.log(`🔗 Expanding '${value}' using property-specific @vocab: ${expanded}`);
          return expanded;
        }
      }
    }
    
    // PRIORITY 3: Check for exact context mapping in main context
    if (this.resolvedContext && this.resolvedContext[value]) {
      const mapping = this.resolvedContext[value];
      if (typeof mapping === 'string') {
        console.log(`🔗 Expanding reference '${value}' using direct context mapping: ${mapping}`);
        return mapping;
      } else if (typeof mapping === 'object' && mapping !== null && mapping['@id']) {
        console.log(`🔗 Expanding reference '${value}' using context object mapping: ${mapping['@id']}`);
        return mapping['@id'];
      }
    }
    
    // PRIORITY 4: Use main context @base or @vocab (only if no direct mapping found)
    if (this.resolvedContext) {
      const baseOrVocab = this.resolvedContext['@base'] || this.resolvedContext['@vocab'];
      if (baseOrVocab) {
        const expanded = baseOrVocab + value;
        console.log(`🔗 Expanding '${value}' using global base/vocab: ${expanded}`);
        return expanded;
      }
    }
    
    // Return original value if no expansion possible
    console.log(`⚠️ No expansion found for reference '${value}', keeping original`);
    return value;
  }

  // Find and collect all @id references that need resolution
  collectIdReferences(obj, refs = new Set(), visited = new Set()) {
    if (typeof obj !== 'object' || obj === null || visited.has(obj)) {
      return refs;
    }
    visited.add(obj);

    if (Array.isArray(obj)) {
      obj.forEach(item => this.collectIdReferences(item, refs, visited));
    } else {
      // Direct @id references in objects that only have @id
      if (obj['@id'] && typeof obj['@id'] === 'string' && Object.keys(obj).length <= 3) {
        if (this.isValidReference(obj['@id'])) {
          refs.add(obj['@id']);
        }
      }

      // String values in properties marked as links in the context
      Object.entries(obj).forEach(([key, value]) => {
        // Check if this key is marked as a link property
        if (this.isLinkedProperty(key)) {
          if (typeof value === 'string') {
            const expandedValue = this.expandReference(value, key);
            if (this.isValidReference(expandedValue, this.resolvedContext)) {
              console.log(`🔗 Collecting linked reference in '${key}': ${value} -> ${expandedValue}`);
              refs.add(expandedValue);
            }
          } else if (Array.isArray(value)) {
            value.forEach(item => {
              if (typeof item === 'string') {
                const expandedValue = this.expandReference(item, key);
                if (this.isValidReference(expandedValue, this.resolvedContext)) {
                  console.log(`🔗 Collecting linked reference in '${key}[]': ${item} -> ${expandedValue}`);
                  refs.add(expandedValue);
                }
              } else if (typeof item === 'object' && item !== null && item['@id'] && Object.keys(item).length <= 3) {
                if (this.isValidReference(item['@id'])) {
                  refs.add(item['@id']);
                }
              } else if (typeof item === 'object') {
                this.collectIdReferences(item, refs, visited);
              }
            });
          }
        } else if (typeof value === 'object' && value !== null) {
          this.collectIdReferences(value, refs, visited);
        }
      });
    }

    visited.delete(obj);
    return refs;
  }

  // Check if a reference is valid and resolvable with proper priority
  isValidReference(value, context = null) {
    if (!value || typeof value !== 'string') return false;
    
    // Already a full URL
    if (value.startsWith('http')) return true;
    
    // Check for explicit context mapping
    const checkContext = context || this.resolvedContext;
    if (checkContext && checkContext[value]) {
      const mapping = checkContext[value];
      if (typeof mapping === 'string' || (typeof mapping === 'object' && mapping !== null && mapping['@id'])) {
        return true;
      }
    }
    
    // Check for prefixed references
    if (value.includes(':')) {
      const prefix = value.split(':')[0];
      
      // Check context for prefix
      if (checkContext && checkContext[prefix]) {
        return true;
      }
      
      // Check global prefix mappings
      return this.prefixMapping.hasOwnProperty(prefix);
    }
    
    // If we have context with @base or @vocab, even simple strings can be references
    if (checkContext && (checkContext['@base'] || checkContext['@vocab'])) {
      return true;
    }
    
    return false;
  }

  // Collect all @id references from the data structure for iterative processing
  collectAllIdReferences(obj, refs = new Set(), visited = new Set()) {
    if (typeof obj !== 'object' || obj === null || visited.has(obj)) {
      return refs;
    }
    visited.add(obj);

    if (Array.isArray(obj)) {
      obj.forEach(item => this.collectAllIdReferences(item, refs, visited));
    } else {
      // Look for @id keys in objects that need expansion
      if (obj['@id'] && typeof obj['@id'] === 'string') {
        if (this.shouldExpandReference(obj)) {
          refs.add(obj['@id']);
        }
      }

      // Look for string values that are references
      Object.entries(obj).forEach(([key, value]) => {
        if (typeof value === 'string' && this.isExpandableReference(value, key)) {
          const expandedValue = this.expandReference(value, key);
          console.log(`🔗 Found expandable reference in '${key}': ${value} -> ${expandedValue}`);
          refs.add(expandedValue);
        } else if (Array.isArray(value)) {
          value.forEach((item, index) => {
            if (typeof item === 'string' && this.isExpandableReference(item, key)) {
              const expandedValue = this.expandReference(item, key);
              console.log(`🔗 Found expandable reference in '${key}[${index}]': ${item} -> ${expandedValue}`);
              refs.add(expandedValue);
            } else if (typeof item === 'object') {
              this.collectAllIdReferences(item, refs, visited);
            }
          });
        } else if (typeof value === 'object' && value !== null) {
          this.collectAllIdReferences(value, refs, visited);
        }
      });
    }

    visited.delete(obj);
    return refs;
  }

  // Check if a reference object should be expanded
  shouldExpandReference(obj) {
    if (!obj['@id']) return false;
    if (obj['@type']) return false; // Already expanded
    
    const keys = Object.keys(obj);
    if (keys.length > 3) return false; // Too many properties, likely expanded
    
    return this.isExpandableReference(obj['@id'], '@id');
  }

  // Check if a string value is an expandable reference with proper priority
  isExpandableReference(value, key) {
    if (typeof value !== 'string') return false;
    if (['@context', '@base', '@vocab', 'id', '@id'].includes(key)) return false;  // Never expand 'id' or '@id' fields
    
    // PRIORITY 1: Check for explicit context mapping
    if (this.resolvedContext && this.resolvedContext[value]) {
      const mapping = this.resolvedContext[value];
      if (typeof mapping === 'string' || (typeof mapping === 'object' && mapping !== null && mapping['@id'])) {
        console.log(`🔗 '${value}' is expandable via direct context mapping`);
        return true;
      }
    }
    
    // PRIORITY 2: Check if the key is defined as a link property in context
    if (this.linkProperties && this.linkProperties.has(key)) {
      // Expand the value to see if it's a valid reference
      const expandedValue = this.expandReference(value, key);
      const isValid = this.isValidReference(expandedValue, this.resolvedContext);
      if (isValid) {
        console.log(`🔗 '${value}' in '${key}' is expandable via link property definition`);
      }
      return isValid;
    }
    
    // PRIORITY 3: Check if the value looks like a reference
    if (value.startsWith('http')) {
      return true;
    }
    
    if (value.includes(':')) {
      const prefix = value.split(':')[0];
      
      // Check context for prefix
      if (this.resolvedContext && this.resolvedContext[prefix]) {
        console.log(`🔗 '${value}' is expandable via context prefix mapping`);
        return true;
      }
      
      // Check global prefix mappings
      if (this.prefixMapping.hasOwnProperty(prefix)) {
        console.log(`🔗 '${value}' is expandable via global prefix mapping`);
        return true;
      }
    }
    
    // PRIORITY 4: Check if we have base/vocab that could expand this
    if (this.resolvedContext && (this.resolvedContext['@base'] || this.resolvedContext['@vocab'])) {
      console.log(`🔗 '${value}' might be expandable via base/vocab`);
      return true;
    }
    
    return false;
  }
}
