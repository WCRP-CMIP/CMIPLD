// Enhanced JSON-LD processing with better context resolution and fallback
import { Utils } from './utils.js';
import { CONFIG } from './config.js';

export class JSONLDProcessor {
  constructor(documentLoader, resolvedContext) {
    this.documentLoader = documentLoader;
    this.resolvedContext = resolvedContext;
    this.entityIndex = new Map();
    this.expandedDocuments = new Map();
  }

  // Safe JSON-LD expansion with enhanced fallback mechanisms
  async safeExpand(doc) {
    console.log('🔄 Starting JSON-LD expansion process...');
    console.log('📋 Document @context type:', typeof doc['@context'], doc['@context']);
    
    // First attempt: Try with our custom document loader
    try {
      const options = {
        expandContext: null,
        keepFreeFloatingNodes: false,
        compactArrays: true,
        documentLoader: this.documentLoader.createDocumentLoader()
      };
      
      console.log('🔄 Attempt 1: Running jsonld.expand with custom document loader...');
      const expanded = await jsonld.expand(doc, options);
      console.log('✅ jsonld.expand successful with custom loader, result:', expanded.length, 'items');
      return expanded;
    } catch (error1) {
      console.warn('⚠️ Attempt 1 failed:', error1.message);
    }

    // Second attempt: Try without custom document loader
    try {
      console.log('🔄 Attempt 2: Running jsonld.expand without custom document loader...');
      const expanded = await jsonld.expand(doc);
      console.log('✅ jsonld.expand successful without loader, result:', expanded.length, 'items');
      return expanded;
    } catch (error2) {
      console.warn('⚠️ Attempt 2 failed:', error2.message);
    }

    // Third attempt: Pre-resolve context and try again
    try {
      console.log('🔄 Attempt 3: Pre-resolving context and retrying...');
      const docWithResolvedContext = await this.preResolveContext(doc);
      const expanded = await jsonld.expand(docWithResolvedContext);
      console.log('✅ jsonld.expand successful with pre-resolved context, result:', expanded.length, 'items');
      return expanded;
    } catch (error3) {
      console.warn('⚠️ Attempt 3 failed:', error3.message);
    }

    // Fourth attempt: Manual expansion as final fallback
    try {
      console.log('🔄 Attempt 4: Using manual expansion fallback...');
      const manuallyExpanded = this.createManualExpansion(doc);
      console.log('✅ Manual expansion successful, result:', manuallyExpanded.length, 'items');
      return manuallyExpanded;
    } catch (error4) {
      console.error('❌ All expansion attempts failed. Last error:', error4.message);
      throw new Error(`JSON-LD expansion failed: ${error4.message}`);
    }
  }

  // Pre-resolve context URLs before expansion
  async preResolveContext(doc) {
    if (!doc['@context']) {
      return doc;
    }

    const docCopy = Utils.deepClone(doc);
    
    try {
      // Use the document's URL as the base URL for context resolution
      const baseUrl = doc['@id'] || doc.id || null;
      const resolvedContext = await this.resolveContextRecursively(doc['@context'], new Set(), baseUrl);
      if (Object.keys(resolvedContext).length > 0) {
        docCopy['@context'] = resolvedContext;
        console.log('✅ Pre-resolved context with', Object.keys(resolvedContext).length, 'terms');
      } else {
        console.warn('⚠️ Context resolution returned empty object, removing @context');
        delete docCopy['@context'];
      }
    } catch (error) {
      console.warn('⚠️ Context pre-resolution failed, removing @context:', error.message);
      delete docCopy['@context'];
    }

    return docCopy;
  }

  // Recursively resolve context references
  async resolveContextRecursively(context, visited = new Set(), baseUrl = null) {
    if (typeof context === 'string') {
      // Resolve relative URLs to absolute URLs using the base URL
      let contextUrl = context;
      if (!context.startsWith('http')) {
        if (baseUrl) {
          // Create URL object to properly resolve relative paths
          try {
            const base = new URL(baseUrl);
            contextUrl = new URL(context, base.href).href;
            console.log(`🔄 Resolved relative context '${context}' to '${contextUrl}' using base '${baseUrl}'`);
          } catch (urlError) {
            console.warn('⚠️ Failed to resolve relative context URL:', context, 'with base', baseUrl);
            return {};
          }
        } else {
          console.warn('⚠️ Cannot resolve relative context without base URL:', context);
          return {};
        }
      }
      
      if (visited.has(contextUrl)) {
        console.warn('⚠️ Circular context reference detected:', contextUrl);
        return {};
      }
      visited.add(contextUrl);
      
      try {
        console.log('🔄 Resolving context URL:', contextUrl);
        const contextDoc = await this.documentLoader.fetchDocument(contextUrl);
        if (contextDoc && contextDoc['@context']) {
          return await this.resolveContextRecursively(contextDoc['@context'], visited, contextUrl);
        } else if (contextDoc && typeof contextDoc === 'object') {
          // The entire document might be the context
          return contextDoc;
        }
      } catch (error) {
        console.warn('⚠️ Failed to resolve context URL:', contextUrl, error.message);
      }
      return {};
    } else if (Array.isArray(context)) {
      const merged = {};
      for (const ctx of context) {
        const resolved = await this.resolveContextRecursively(ctx, visited, baseUrl);
        Object.assign(merged, resolved);
      }
      return merged;
    } else if (typeof context === 'object' && context !== null) {
      // Already resolved
      return context;
    }
    
    return {};
  }

  // Enhanced manual expansion with better context handling
  createManualExpansion(doc) {
    if (!doc) {
      console.error('⚠️ Cannot expand null/undefined document');
      return [];
    }
    
    console.log('🔄 Starting manual expansion...');
    console.log('📋 Input document:', doc);
    
    // Use resolved context if available, otherwise extract from document
    let expansionContext = this.resolvedContext;
    if (Object.keys(expansionContext).length === 0 && doc['@context']) {
      console.log('🔄 No resolved context available, using document context for expansion');
      expansionContext = this.extractInlineContext(doc['@context']);
    }
    
    console.log('📋 Expansion context has', Object.keys(expansionContext).length, 'terms');
    
    const expandedDoc = this.manuallyExpandObject(doc, expansionContext);
    
    // Ensure we always return an array for consistency with JSON-LD expand
    let result;
    if (Array.isArray(expandedDoc)) {
      result = expandedDoc;
    } else if (expandedDoc && typeof expandedDoc === 'object') {
      result = [expandedDoc];
    } else {
      console.warn('⚠️ Manual expansion produced unexpected result:', expandedDoc);
      result = [];
    }
    
    console.log('✅ Manual expansion completed, result:', result);
    return result;
  }

  // Extract inline context definitions (non-URL contexts)
  extractInlineContext(context) {
    if (typeof context === 'object' && context !== null && !Array.isArray(context)) {
      return context;
    } else if (Array.isArray(context)) {
      const merged = {};
      for (const ctx of context) {
        if (typeof ctx === 'object' && ctx !== null) {
          Object.assign(merged, ctx);
        }
      }
      return merged;
    }
    return {};
  }

  // Enhanced manual object expansion
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
      
      // Expand the key
      expandedKey = this.expandKey(key, context);
      
      // For @id and @type, ensure proper formatting
      if (expandedKey === '@id' && typeof value === 'string') {
        expandedValue = this.expandIri(value, context);
      } else if (expandedKey === '@type' && typeof value === 'string') {
        expandedValue = this.expandIri(value, context);
      } else if (this.isLinkProperty(key, context)) {
        // This is a link property - expand values to @id objects
        expandedValue = this.expandLinkedValue(value, context);
      } else {
        // Recursively expand other values
        expandedValue = this.manuallyExpandObject(value, context, visited);
      }
      
      expanded[expandedKey] = expandedValue;
    }
    
    visited.delete(obj);
    
    // Ensure we have at least an @id for the main entity
    if (!expanded['@id'] && obj.id && typeof obj.id === 'string') {
      expanded['@id'] = this.expandIri(obj.id, context);
    }
    
    return expanded;
  }

  // Expand a key using context
  expandKey(key, context) {
    // Handle JSON-LD keywords
    if (key.startsWith('@')) {
      return key;
    }
    
    // Handle common shortcuts
    if (key === 'id') return '@id';
    if (key === 'type') return '@type';
    
    // Check context definition
    const contextDef = context[key];
    if (contextDef) {
      if (typeof contextDef === 'string') {
        return contextDef;
      } else if (typeof contextDef === 'object' && contextDef['@id']) {
        return contextDef['@id'];
      }
    }
    
    // Handle prefixed terms
    if (key.includes(':')) {
      const [prefix, suffix] = key.split(':', 2);
      if (context[prefix]) {
        return context[prefix] + suffix;
      }
      // Check global prefix mappings
      if (CONFIG.prefixMapping && CONFIG.prefixMapping[prefix]) {
        return CONFIG.prefixMapping[prefix] + suffix;
      }
    }
    
    // Use vocab or base expansion
    const vocab = context['@vocab'];
    const base = context['@base'];
    
    if (vocab && !key.startsWith('http')) {
      return vocab + key;
    } else if (base && !key.startsWith('http')) {
      return base + key;
    }
    
    // For manual expansion in the absence of context, keep original key
    // This allows the compacted view to show the original property names
    return key;
  }

  // Check if a property is a link property
  isLinkProperty(key, context) {
    const contextDef = context[key];
    if (contextDef && typeof contextDef === 'object' && contextDef['@type'] === '@id') {
      return true;
    }
    return false;
  }

  // Expand linked values to @id objects
  expandLinkedValue(value, context) {
    if (typeof value === 'string') {
      const expandedIri = this.expandIri(value, context);
      return { '@id': expandedIri };
    } else if (Array.isArray(value)) {
      return value.map(item => {
        if (typeof item === 'string') {
          const expandedIri = this.expandIri(item, context);
          return { '@id': expandedIri };
        } else if (typeof item === 'object' && item !== null) {
          return this.manuallyExpandObject(item, context, new Set());
        }
        return item;
      });
    } else if (typeof value === 'object' && value !== null) {
      return this.manuallyExpandObject(value, context, new Set());
    }
    return value;
  }

  // Expand an IRI using context
  expandIri(value, context) {
    if (!value || typeof value !== 'string') return value;
    
    // Already a full URL
    if (value.startsWith('http://') || value.startsWith('https://')) return value;
    
    // Handle prefixed IRIs
    if (value.includes(':')) {
      const [prefix, suffix] = value.split(':', 2);
      if (context[prefix]) {
        return context[prefix] + suffix;
      }
      // Check global prefix mappings
      if (CONFIG.prefixMapping && CONFIG.prefixMapping[prefix]) {
        return CONFIG.prefixMapping[prefix] + suffix;
      }
    }
    
    // Use @base or @vocab for expansion
    const base = context['@base'];
    const vocab = context['@vocab'];
    
    if (base && !value.startsWith('/')) {
      return base + (base.endsWith('/') ? '' : '/') + value;
    } else if (vocab) {
      return vocab + value;
    }
    
    return value;
  }

  // Safe JSON-LD compaction with fallback
  async safeCompact(doc, context) {
    console.log('🔄 Starting JSON-LD compaction...');
    
    // First attempt: Try with custom document loader
    try {
      const options = {
        compactArrays: true,
        documentLoader: this.documentLoader.createDocumentLoader()
      };
      
      console.log('🔄 Running jsonld.compact with context:', typeof context === 'object' ? Object.keys(context).length + ' terms' : context);
      const compacted = await jsonld.compact(doc, context, options);
      console.log('✅ jsonld.compact successful');
      return compacted;
    } catch (error1) {
      console.warn('⚠️ Compaction with custom loader failed:', error1.message);
    }

    // Second attempt: Try without custom document loader
    try {
      console.log('🔄 Retrying jsonld.compact without custom document loader...');
      const compacted = await jsonld.compact(doc, context);
      console.log('✅ jsonld.compact successful (without loader)');
      return compacted;
    } catch (error2) {
      console.warn('⚠️ Compaction without loader failed:', error2.message);
    }

    // Fallback: Return the expanded document (at least it's valid JSON-LD)
    console.warn('⚠️ JSON-LD compaction failed completely, returning expanded form');
    return doc;
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