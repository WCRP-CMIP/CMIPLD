// JSON-LD processing (expansion, compaction, resolution)
import { Utils } from './utils.js';
import { CONFIG } from './config.js';

export class JSONLDProcessor {
  constructor(documentLoader, resolvedContext) {
    this.documentLoader = documentLoader;
    this.resolvedContext = resolvedContext;
    this.entityIndex = new Map();
    this.expandedDocuments = new Map();
  }

  // Safe JSON-LD expansion with full context
  async safeExpand(doc) {
    try {
      const options = {
        expandContext: null,
        keepFreeFloatingNodes: false,
        compactArrays: true,
        documentLoader: this.documentLoader.createDocumentLoader()
      };
      
      // Use jsonld.expand directly - no preprocessing
      console.log('🔄 Running jsonld.expand with document loader...');
      const expanded = await jsonld.expand(doc, options);
      console.log('✅ jsonld.expand successful, result:', expanded.length, 'items');
      return expanded;
    } catch (error) {
      console.error('⚠️ JSON-LD expansion failed:', error.message);
      console.error('⚠️ Full error:', error);
      // Try without custom document loader as fallback
      try {
        console.log('🔄 Retrying jsonld.expand without custom document loader...');
        const expanded = await jsonld.expand(doc);
        console.log('✅ jsonld.expand successful (without loader), result:', expanded.length, 'items');
        return expanded;
      } catch (error2) {
        console.error('⚠️ JSON-LD expansion failed again:', error2.message);
        throw error2;
      }
    }
  }

  // Prepare document for expansion by cleaning problematic contexts
  prepareDocumentForExpansion(doc) {
    const cleanDoc = Utils.deepClone(doc);
    
    if (cleanDoc['@context']) {
      const context = cleanDoc['@context'];
      
      // Handle string contexts (URLs)
      if (typeof context === 'string' && context.startsWith('http')) {
        if (Object.keys(this.resolvedContext).length > 0) {
          cleanDoc['@context'] = this.resolvedContext;
        } else {
          delete cleanDoc['@context'];
        }
      } else if (Array.isArray(context)) {
        // Filter and clean array contexts
        const cleanedContexts = [];
        
        for (const ctx of context) {
          if (typeof ctx === 'string' && ctx.startsWith('http')) {
            // Skip URL contexts
          } else if (typeof ctx === 'object' && ctx !== null) {
            // Keep object contexts
            cleanedContexts.push(ctx);
          } else if (typeof ctx === 'string') {
            // Keep non-URL string contexts
            cleanedContexts.push(ctx);
          }
        }
        
        // Add resolved context if available
        if (Object.keys(this.resolvedContext).length > 0) {
          cleanedContexts.push(this.resolvedContext);
        }
        
        if (cleanedContexts.length > 0) {
          cleanDoc['@context'] = cleanedContexts.length === 1 ? cleanedContexts[0] : cleanedContexts;
        } else {
          delete cleanDoc['@context'];
        }
      } else if (typeof context !== 'object' || context === null) {
        // Invalid context type - remove it
        delete cleanDoc['@context'];
      }
    }
    
    return cleanDoc;
  }

  // Create manual expansion when jsonld.expand fails
  createManualExpansion(doc) {
    if (!doc) {
      console.error('⚠️ Cannot expand null/undefined document');
      return [];
    }
    
    const expandedDoc = this.manuallyExpandObject(doc, this.resolvedContext);
    const result = Array.isArray(expandedDoc) ? expandedDoc : [expandedDoc];
    
    return result;
  }

  // Manually expand an object using available context
  manuallyExpandObject(obj, context = {}, visited = new Set()) {
    if (typeof obj !== 'object' || obj === null || visited.has(obj)) {
      return obj;
    }
    visited.add(obj);
    
    if (Array.isArray(obj)) {
      const result = obj.map(item => this.manuallyExpandObject(item, context, visited));
      visited.delete(obj);
      return result;
    }
    
    const expanded = {};
    
    for (const [key, value] of Object.entries(obj)) {
      let expandedKey = key;
      let expandedValue = value;
      
      // Skip @context in the output
      if (key === '@context') continue;
      
      // Get context definition for this key
      const contextDef = context[key];
      
      // Expand the key using context
      if (contextDef) {
        if (typeof contextDef === 'string') {
          expandedKey = contextDef;
        } else if (typeof contextDef === 'object' && contextDef['@id']) {
          expandedKey = contextDef['@id'];
          
          // Check if this property is marked as @type: @id
          if (contextDef['@type'] === '@id') {
            // This is a linked property - expand values to @id objects
            expandedValue = this.expandLinkedValue(value, context);
          }
        }
      } else if (key === 'id' && !key.startsWith('@')) {
        expandedKey = '@id';
      } else if (key === 'type' && !key.startsWith('@')) {
        expandedKey = '@type';
      } else if (!key.startsWith('@') && !key.includes(':') && !key.startsWith('http')) {
        // Use vocab or base from context if available
        const vocab = context['@vocab'] || context['@base'];
        if (vocab) {
          expandedKey = vocab + key;
        } else {
          // Default expansion
          expandedKey = 'http://example.org/' + key;
        }
      }
      
      // Recursively expand the value (unless already expanded above)
      if (expandedValue === value) {
        expandedValue = this.manuallyExpandObject(value, context, visited);
      }
      
      expanded[expandedKey] = expandedValue;
    }
    
    visited.delete(obj);
    return expanded;
  }

  // Expand linked values to @id objects
  expandLinkedValue(value, context) {
    if (typeof value === 'string') {
      // Expand the string to a full IRI
      const expandedIri = this.expandIri(value, context);
      console.log(`🔗 Expanding linked value: "${value}" -> {"@id": "${expandedIri}"}`);
      return { '@id': expandedIri };
    } else if (Array.isArray(value)) {
      // Expand each item in the array
      console.log(`🔗 Expanding linked array with ${value.length} items`);
      return value.map(item => {
        if (typeof item === 'string') {
          const expandedIri = this.expandIri(item, context);
          console.log(`🔗 Expanding array item: "${item}" -> {"@id": "${expandedIri}"}`);
          return { '@id': expandedIri };
        } else if (typeof item === 'object' && item !== null) {
          // Already an object, expand it normally
          return this.manuallyExpandObject(item, context, new Set());
        }
        return item;
      });
    } else if (typeof value === 'object' && value !== null) {
      // Already an object, expand it normally
      return this.manuallyExpandObject(value, context, new Set());
    }
    return value;
  }

  // Expand an IRI using context
  expandIri(value, context) {
    if (!value || typeof value !== 'string') return value;
    
    // Already a full URL
    if (value.startsWith('http')) return value;
    
    // Has a prefix
    if (value.includes(':')) {
      const [prefix, suffix] = value.split(':', 2);
      if (context[prefix]) {
        return context[prefix] + suffix;
      }
      return value;
    }
    
    // Use @base or @vocab
    const baseOrVocab = context['@base'] || context['@vocab'];
    if (baseOrVocab) {
      return baseOrVocab + value;
    }
    
    return value;
  }

  // Safe JSON-LD compaction
  async safeCompact(doc, context) {
    try {
      const options = {
        compactArrays: true,
        documentLoader: this.documentLoader.createDocumentLoader()
      };
      
      console.log('🔄 Running jsonld.compact with context:', typeof context === 'object' ? Object.keys(context).length + ' terms' : context);
      const compacted = await jsonld.compact(doc, context, options);
      console.log('✅ jsonld.compact successful');
      return compacted;
    } catch (error) {
      console.error('⚠️ Failed to compact with jsonld.compact():', error.message);
      console.error('⚠️ Full error:', error);
      // Try without custom document loader as fallback
      try {
        console.log('🔄 Retrying jsonld.compact without custom document loader...');
        const compacted = await jsonld.compact(doc, context);
        console.log('✅ jsonld.compact successful (without loader)');
        return compacted;
      } catch (error2) {
        console.error('⚠️ JSON-LD compaction failed again:', error2.message);
        throw error2;
      }
    }
  }

  // Index entities from expanded documents
  async indexAllEntities(loadedDocuments) {
    this.entityIndex.clear();

    for (const [url, doc] of loadedDocuments) {
      try {
        const expanded = await this.safeExpand(doc);
        this.expandedDocuments.set(url, expanded);
        this.indexEntitiesFromExpanded(expanded, url);
      } catch (error) {
        console.error(`Failed to expand document ${url}:`, error.message);
        this.indexEntitiesFromOriginal(doc, url);
      }
    }
    
    // Log summary as warning
    if (this.entityIndex.size > 0) {
      console.warn(`📦 Indexed ${this.entityIndex.size} entities from ${loadedDocuments.size} documents`);
    }
  }

  // Index entities from expanded JSON-LD
  indexEntitiesFromExpanded(expanded, baseUrl) {
    if (!Array.isArray(expanded)) {
      expanded = [expanded];
    }

    const indexEntity = (entity, depth = 0) => {
      if (!entity || typeof entity !== 'object' || depth > 10) {
        return;
      }
      
      if (entity['@id']) {
        const id = entity['@id'];
        this.entityIndex.set(id, entity);
        
        // Also index with resolved URL
        try {
          const resolvedId = Utils.resolveUrl(id, baseUrl);
          if (resolvedId !== id) {
            this.entityIndex.set(resolvedId, entity);
          }
        } catch (e) {
          // URL resolution failed, that's ok
        }
        
        // Also index with prefix form if it's a full URL
        if (id.startsWith('http')) {
          for (const [prefix, uri] of Object.entries(CONFIG.prefixMapping || {})) {
            if (id.startsWith(uri)) {
              const prefixedId = id.replace(uri, prefix + ':');
              this.entityIndex.set(prefixedId, entity);
              break;
            }
          }
        }
      }
      
      // Recursively index nested entities
      for (const value of Object.values(entity)) {
        if (Array.isArray(value)) {
          value.forEach(item => {
            if (typeof item === 'object' && item !== null) {
              indexEntity(item, depth + 1);
            }
          });
        } else if (typeof value === 'object' && value !== null) {
          indexEntity(value, depth + 1);
        }
      }
    };

    expanded.forEach(entity => indexEntity(entity));
  }

  // Fallback indexing from original document
  indexEntitiesFromOriginal(doc, baseUrl) {
    const indexEntity = (obj) => {
      if (typeof obj === 'object' && obj !== null) {
        if (obj['@id']) {
          this.entityIndex.set(obj['@id'], obj);
        }
        
        if (Array.isArray(obj)) {
          obj.forEach(indexEntity);
        } else {
          Object.values(obj).forEach(indexEntity);
        }
      }
    };
    
    indexEntity(doc);
  }

  // Get entity from index
  getEntityFromIndex(idRef, prefixMapping) {
    // Direct lookup
    if (this.entityIndex.has(idRef)) {
      return this.entityIndex.get(idRef);
    }
    
    // Try with resolved prefix
    const resolvedRef = Utils.resolvePrefix(idRef, prefixMapping);
    if (this.entityIndex.has(resolvedRef)) {
      return this.entityIndex.get(resolvedRef);
    }
    
    // Try as prefixed form if it's a full URL
    if (idRef.startsWith('http')) {
      for (const [prefix, uri] of Object.entries(prefixMapping || {})) {
        if (idRef.startsWith(uri)) {
          const prefixedForm = idRef.replace(uri, prefix + ':');
          if (this.entityIndex.has(prefixedForm)) {
            return this.entityIndex.get(prefixedForm);
          }
        }
      }
    }
    
    // Try from loaded documents
    if (this.documentLoader.loadedDocuments.has(resolvedRef)) {
      const doc = this.documentLoader.loadedDocuments.get(resolvedRef);
      // If the document itself is the entity we're looking for
      if (doc['@id'] === idRef || doc['@id'] === resolvedRef || doc['id'] === idRef || doc['id'] === resolvedRef) {
        return doc;
      }
      // Look for the entity within the document
      if (doc['@graph']) {
        for (const entity of doc['@graph']) {
          if (entity['@id'] === idRef || entity['@id'] === resolvedRef) {
            return entity;
          }
        }
      }
    }
    
    return null;
  }

  clear() {
    this.entityIndex.clear();
    this.expandedDocuments.clear();
  }
}
