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

  // Expand a reference using @base or @vocab from context
  expandReference(value, key = null) {
    if (!value || typeof value !== 'string') return value;
    
    // Already a full URL
    if (value.startsWith('http')) return value;
    
    // Has a prefix
    if (value.includes(':')) {
      const prefix = value.split(':')[0];
      if (this.prefixMapping.hasOwnProperty(prefix)) {
        return Utils.resolvePrefix(value, this.prefixMapping);
      }
      return value;
    }
    
    // Use @base or @vocab to expand
    if (this.resolvedContext) {
      // Check if the property has a specific @context with @base or @vocab
      if (key && this.resolvedContext[key] && typeof this.resolvedContext[key] === 'object') {
        const propContext = this.resolvedContext[key];
        if (propContext['@context']) {
          // This property has its own context - need to check it
          const propBase = propContext['@base'] || propContext['@vocab'];
          if (propBase) {
            console.log(`🔗 Using property-specific base for '${key}': ${propBase}`);
            return propBase + value;
          }
        }
      }
      
      // Use global @base or @vocab
      const baseOrVocab = this.resolvedContext['@base'] || this.resolvedContext['@vocab'];
      if (baseOrVocab) {
        console.log(`🔗 Expanding '${value}' using base/vocab: ${baseOrVocab}`);
        return baseOrVocab + value;
      }
    }
    
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

  // Check if a reference is valid and resolvable
  isValidReference(value, context = null) {
    if (value.startsWith('http')) return true;
    if (value.includes(':')) {
      const prefix = value.split(':')[0];
      return this.prefixMapping.hasOwnProperty(prefix);
    }
    // If we have context with @base or @vocab, even simple strings can be references
    if (context && (context['@base'] || context['@vocab'])) {
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

  // Check if a string value is an expandable reference
  isExpandableReference(value, key) {
    if (typeof value !== 'string') return false;
    if (['@context', '@base', '@vocab', 'id', '@id'].includes(key)) return false;  // Never expand 'id' or '@id' fields
    
    // Check if the key is defined as a link property in context
    if (this.linkProperties && this.linkProperties.has(key)) {
      // Expand the value to see if it's a valid reference
      const expandedValue = this.expandReference(value, key);
      return this.isValidReference(expandedValue, this.resolvedContext);
    }
    
    // Also check if the value looks like a reference even if not marked in context
    if (value.startsWith('http')) {
      return true;
    }
    
    if (value.includes(':')) {
      const prefix = value.split(':')[0];
      return this.prefixMapping.hasOwnProperty(prefix);
    }
    
    return false;
  }
}
