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

  // Enhanced context resolution with property-scoped context support
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
      // Process object context and resolve nested @context references
      const resolved = {};
      
      for (const [key, value] of Object.entries(context)) {
        if (typeof value === 'object' && value !== null && value['@context']) {
          // This property has its own context - resolve it
          console.log(`🔄 Found property-scoped context for '${key}':`, value['@context']);
          const propContext = await this.resolveContextRecursively(value['@context'], visited, baseUrl);
          
          // Store the resolved property-scoped context
          resolved[key] = {
            ...value,
            '@resolvedContext': propContext  // Store resolved context for later use
          };
          
          console.log(`✅ Resolved property-scoped context for '${key}' with`, Object.keys(propContext).length, 'terms');
        } else {
          // Regular context entry
          resolved[key] = value;
        }
      }
      
      return resolved;
    }
    
    return {};
  }

  // Enhanced manual expansion with better context handling
  createManualExpansion(doc, docUrl = null) {
    if (!doc) {
      console.error('⚠️ Cannot expand null/undefined document');
      return [];
    }
    
    console.log('🔄 Starting manual expansion...');
    console.log('📋 Input document:', doc);
    console.log('📋 Document URL:', docUrl);
    
    // Use resolved context if available, otherwise extract from document
    let expansionContext = this.resolvedContext;
    if (Object.keys(expansionContext).length === 0 && doc['@context']) {
      console.log('🔄 No resolved context available, using document context for expansion');
      expansionContext = this.extractInlineContext(doc['@context']);
    }
    
    // If we have a document URL, ensure property-scoped contexts are resolved
    if (docUrl && doc['@context']) {
      expansionContext = this.resolveContextWithBase(doc['@context'], docUrl, expansionContext);
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

  // Resolve context using the document's base URL for property-scoped contexts
  resolveContextWithBase(context, baseUrl, fallbackContext = {}) {
    if (typeof context === 'string') {
      // Context is a URL - it should have been resolved already by the document loader
      return fallbackContext;
    } else if (Array.isArray(context)) {
      // Multiple contexts - merge them
      let merged = { ...fallbackContext };
      for (const ctx of context) {
        if (typeof ctx === 'object' && ctx !== null) {
          // Check for property-scoped contexts in this context object
          for (const [key, value] of Object.entries(ctx)) {
            if (typeof value === 'object' && value !== null && value['@context']) {
              // This is a property with its own context - mark it as needing resolution
              console.log(`🔄 Found property-scoped context for '${key}' that needs async resolution`);
              merged[key] = {
                ...value,
                '_needsContextResolution': true,
                '_contextUrl': value['@context'],
                '_baseUrl': baseUrl
              };
            } else {
              merged[key] = value;
            }
          }
        }
      }
      return merged;
    } else if (typeof context === 'object' && context !== null) {
      // Inline context - merge with fallback and check for property-scoped contexts
      let merged = { ...fallbackContext };
      for (const [key, value] of Object.entries(context)) {
        if (typeof value === 'object' && value !== null && value['@context']) {
          console.log(`🔄 Found property-scoped context for '${key}' that needs async resolution`);
          merged[key] = {
            ...value,
            '_needsContextResolution': true,
            '_contextUrl': value['@context'],
            '_baseUrl': baseUrl
          };
        } else {
          merged[key] = value;
        }
      }
      return merged;
    }
    
    return fallbackContext;
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
        expandedValue = this.expandLinkedValue(value, context, key);
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

  // Expand the key using context with proper priority
  expandKey(key, context) {
    // Handle JSON-LD keywords
    if (key.startsWith('@')) {
      return key;
    }
    
    // Handle common shortcuts
    if (key === 'id') return '@id';
    if (key === 'type') return '@type';
    
    // PRIORITY 1: Check direct context mapping first
    const contextDef = context[key];
    if (contextDef) {
      if (typeof contextDef === 'string') {
        console.log(`🔄 Expanding key '${key}' using direct context mapping: ${contextDef}`);
        return contextDef;
      } else if (typeof contextDef === 'object' && contextDef['@id']) {
        console.log(`🔄 Expanding key '${key}' using context object mapping: ${contextDef['@id']}`);
        return contextDef['@id'];
      }
    }
    
    // PRIORITY 2: Handle prefixed terms
    if (key.includes(':')) {
      const [prefix, suffix] = key.split(':', 2);
      if (context[prefix]) {
        const expanded = context[prefix] + suffix;
        console.log(`🔄 Expanding prefixed key '${key}' using context: ${expanded}`);
        return expanded;
      }
      // Check global prefix mappings
      if (CONFIG.prefixMapping && CONFIG.prefixMapping[prefix]) {
        const expanded = CONFIG.prefixMapping[prefix] + suffix;
        console.log(`🔄 Expanding prefixed key '${key}' using global mapping: ${expanded}`);
        return expanded;
      }
    }
    
    // PRIORITY 3: Use vocab or base expansion (only if no direct mapping)
    const vocab = context['@vocab'];
    const base = context['@base'];
    
    if (vocab && !key.startsWith('http')) {
      const expanded = vocab + key;
      console.log(`🔄 Expanding key '${key}' using @vocab: ${expanded}`);
      return expanded;
    } else if (base && !key.startsWith('http')) {
      const expanded = base + key;
      console.log(`🔄 Expanding key '${key}' using @base: ${expanded}`);
      return expanded;
    }
    
    // For manual expansion in the absence of context, keep original key
    // This allows the compacted view to show the original property names
    console.log(`⚠️ No expansion found for key '${key}', keeping original`);
    return key;
  }

  // Check if a property is a link property
  isLinkProperty(key, context) {
    const contextDef = context[key];
    if (contextDef && typeof contextDef === 'object') {
      // Check for @type: @id (indicates this property contains links)
      if (contextDef['@type'] === '@id') {
        return true;
      }
    }
    return false;
  }

  // Expand linked values to @id objects with proper context resolution
  expandLinkedValue(value, context, propertyKey = null) {
    if (typeof value === 'string') {
      // Check if this property has its own context for resolution
      let expansionContext = context;
      if (propertyKey && context[propertyKey] && typeof context[propertyKey] === 'object' && context[propertyKey]['@context']) {
        console.log(`🔄 Property '${propertyKey}' has its own context, will need to resolve it for value expansion`);
        // Note: The property-specific context should be resolved and used
        // This will be handled by the expandIri method when it checks for property-specific contexts
      }
      
      const expandedIri = this.expandIri(value, expansionContext, propertyKey);
      return { '@id': expandedIri };
    } else if (Array.isArray(value)) {
      return value.map(item => {
        if (typeof item === 'string') {
          const expandedIri = this.expandIri(item, context, propertyKey);
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

  // Expand an IRI using context with proper priority and correct prefix resolution
  expandIri(value, context, propertyKey = null) {
    if (!value || typeof value !== 'string') return value;
    
    // Already a full URL
    if (value.startsWith('http://') || value.startsWith('https://')) return value;
    
    // PRIORITY 1: Handle prefixed IRIs FIRST (before property-scoped contexts)
    // This ensures "universal:activity/cmip" is resolved correctly
    if (value.includes(':')) {
      const colonIndex = value.indexOf(':');
      const prefix = value.substring(0, colonIndex);
      const suffix = value.substring(colonIndex + 1);
      
      console.log(`🔄 Processing prefixed IRI: prefix='${prefix}', suffix='${suffix}'`);
      
      // Check main context for prefix mapping first
      if (context[prefix]) {
        const prefixMapping = context[prefix];
        if (typeof prefixMapping === 'string') {
          const expanded = prefixMapping + suffix;
          console.log(`🔄 Expanding prefixed '${value}' using context prefix '${prefix}': ${expanded}`);
          return expanded;
        }
      }
      
      // Check global prefix mappings
      if (CONFIG.prefixMapping && CONFIG.prefixMapping[prefix]) {
        const expanded = CONFIG.prefixMapping[prefix] + suffix;
        console.log(`🔄 Expanding prefixed '${value}' using global prefix '${prefix}': ${expanded}`);
        return expanded;
      }
      
      console.log(`⚠️ No prefix mapping found for '${prefix}' in value '${value}'`);
    }
    
    // PRIORITY 2: Check if this property has its own resolved context (for non-prefixed values)
    if (propertyKey && context[propertyKey] && typeof context[propertyKey] === 'object') {
      const propertyDef = context[propertyKey];
      
      // Check if we have a resolved property-specific context
      if (propertyDef['@resolvedContext']) {
        const propContext = propertyDef['@resolvedContext'];
        console.log(`🔄 Using resolved property-specific context for '${propertyKey}' to expand '${value}'`);
        
        // First check the property-specific context for direct mappings
        if (propContext[value]) {
          const mapping = propContext[value];
          if (typeof mapping === 'string') {
            console.log(`🔄 Expanding '${value}' using property-specific direct mapping: ${mapping}`);
            return mapping;
          } else if (typeof mapping === 'object' && mapping['@id']) {
            console.log(`🔄 Expanding '${value}' using property-specific object mapping: ${mapping['@id']}`);
            return mapping['@id'];
          }
        }
        
        // Check for prefixed terms in property context (shouldn't happen since we handled prefixes above)
        // Use property-specific base/vocab
        const propBase = propContext['@base'];
        const propVocab = propContext['@vocab'];
        
        if (propBase && !value.startsWith('/')) {
          const expanded = propBase + (propBase.endsWith('/') ? '' : '/') + value;
          console.log(`🔄 Expanding '${value}' using property-specific @base: ${expanded}`);
          return expanded;
        } else if (propVocab) {
          const expanded = propVocab + value;
          console.log(`🔄 Expanding '${value}' using property-specific @vocab: ${expanded}`);
          return expanded;
        }
      } else if (propertyDef['@context']) {
        console.log(`🔄 Property '${propertyKey}' has unresolved context: ${propertyDef['@context']} - this should have been resolved during document loading`);
      }
    }
    
    // PRIORITY 3: Check for exact context mapping in main context
    if (context[value]) {
      const mapping = context[value];
      if (typeof mapping === 'string') {
        console.log(`🔄 Expanding '${value}' using direct context mapping: ${mapping}`);
        return mapping;
      } else if (typeof mapping === 'object' && mapping['@id']) {
        console.log(`🔄 Expanding '${value}' using context object mapping: ${mapping['@id']}`);
        return mapping['@id'];
      }
    }
    
    // PRIORITY 4: Use main context @base or @vocab for expansion (only if no direct mapping found)
    const base = context['@base'];
    const vocab = context['@vocab'];
    
    if (base && !value.startsWith('/')) {
      const expanded = base + (base.endsWith('/') ? '' : '/') + value;
      console.log(`🔄 Expanding '${value}' using main context @base: ${expanded}`);
      return expanded;
    } else if (vocab) {
      const expanded = vocab + value;
      console.log(`🔄 Expanding '${value}' using main context @vocab: ${expanded}`);
      return expanded;
    }
    
    // Return original value if no expansion possible
    console.log(`⚠️ No expansion found for '${value}', keeping original`);
    return value;
  }

  // Safe JSON-LD compaction with property-scoped context support
  async safeCompact(doc, context) {
    console.log('🔄 Starting JSON-LD compaction...');
    console.log('📋 Compaction context type:', typeof context);
    
    // Pre-process the context to handle property-scoped contexts for JSON-LD library
    const processedContext = this.preprocessCompactionContext(context);
    
    // First attempt: Try with custom document loader
    try {
      const options = {
        compactArrays: true,
        documentLoader: this.documentLoader.createDocumentLoader()
      };
      
      console.log('🔄 Running jsonld.compact with processed context:', typeof processedContext === 'object' ? Object.keys(processedContext).length + ' terms' : processedContext);
      const compacted = await jsonld.compact(doc, processedContext, options);
      console.log('✅ jsonld.compact successful');
      return compacted;
    } catch (error1) {
      console.warn('⚠️ Compaction with custom loader failed:', error1.message);
    }

    // Second attempt: Try without custom document loader
    try {
      console.log('🔄 Retrying jsonld.compact without custom document loader...');
      const compacted = await jsonld.compact(doc, processedContext);
      console.log('✅ jsonld.compact successful (without loader)');
      return compacted;
    } catch (error2) {
      console.warn('⚠️ Compaction without loader failed:', error2.message);
    }

    // Fallback: Manual compaction using property-scoped contexts
    try {
      console.log('🔄 Attempting manual compaction with property-scoped contexts...');
      const manuallyCompacted = this.manualCompactWithPropertyScopes(doc, context);
      console.log('✅ Manual compaction with property-scoped contexts successful');
      return manuallyCompacted;
    } catch (error3) {
      console.warn('⚠️ Manual compaction failed:', error3.message);
    }

    // Final fallback: Return the expanded document (at least it's valid JSON-LD)
    console.warn('⚠️ JSON-LD compaction failed completely, returning expanded form');
    return doc;
  }

  // Preprocess compaction context to flatten property-scoped contexts for JSON-LD library
  preprocessCompactionContext(context) {
    if (typeof context !== 'object' || context === null) {
      return context;
    }
    
    const processed = {};
    
    for (const [key, value] of Object.entries(context)) {
      if (typeof value === 'object' && value !== null && value['@context']) {
        // This is a property with scoped context - flatten it for JSON-LD library
        console.log(`🔄 Flattening property-scoped context for '${key}' in compaction`);
        
        // Add the property itself
        processed[key] = {
          '@type': value['@type'] || '@id'
          // Note: Don't include @context here as JSON-LD library handles it differently
        };
        
        // Add all terms from the property-scoped context to the main context
        if (typeof value['@context'] === 'object') {
          for (const [propKey, propValue] of Object.entries(value['@context'])) {
            if (!propKey.startsWith('@') && !processed[propKey]) {
              processed[propKey] = propValue;
            }
          }
        }
      } else {
        // Regular context term
        processed[key] = value;
      }
    }
    
    return processed;
  }

  // Manual compaction with property-scoped context support
  manualCompactWithPropertyScopes(doc, context) {
    console.log('🔄 Starting manual compaction with property-scoped contexts');
    
    if (Array.isArray(doc)) {
      // Handle array of expanded objects
      if (doc.length === 1) {
        return this.compactObject(doc[0], context);
      } else {
        // Multiple objects - wrap in @graph
        const compactedObjects = doc.map(item => this.compactObject(item, context));
        return {
          '@context': context,
          '@graph': compactedObjects
        };
      }
    } else if (typeof doc === 'object' && doc !== null) {
      return this.compactObject(doc, context);
    }
    
    return doc;
  }

  // Compact a single object using property-scoped contexts
  compactObject(obj, context, visited = new Set()) {
    if (typeof obj !== 'object' || obj === null || visited.has(obj)) {
      return obj;
    }
    visited.add(obj);
    
    const compacted = {};
    
    for (const [expandedKey, value] of Object.entries(obj)) {
      // Skip @context in expanded data
      if (expandedKey === '@context') continue;
      
      // Find the compact form of the key
      const compactKey = this.findCompactKey(expandedKey, context);
      
      // Check if this property has a scoped context for value compaction
      const propertyContext = this.getPropertyScopedContext(compactKey, context);
      
      if (expandedKey === '@id' || expandedKey === '@type') {
        // Handle JSON-LD keywords
        compacted[expandedKey] = this.compactValue(value, context, compactKey, propertyContext);
      } else {
        // Handle regular properties
        const compactedValue = this.compactValue(value, context, compactKey, propertyContext);
        compacted[compactKey] = compactedValue;
      }
    }
    
    visited.delete(obj);
    return compacted;
  }

  // Find the compact form of an expanded key
  findCompactKey(expandedKey, context) {
    // Check if any context term maps to this expanded key
    for (const [key, value] of Object.entries(context)) {
      if (typeof value === 'string' && value === expandedKey) {
        return key;
      } else if (typeof value === 'object' && value !== null && value['@id'] === expandedKey) {
        return key;
      }
    }
    
    // If no mapping found, return the expanded key
    return expandedKey;
  }

  // Get property-scoped context if available
  getPropertyScopedContext(propertyKey, context) {
    const propertyDef = context[propertyKey];
    if (typeof propertyDef === 'object' && propertyDef !== null && propertyDef['@context']) {
      return propertyDef['@context'];
    }
    return null;
  }

  // Compact a value using appropriate context
  compactValue(value, mainContext, propertyKey, propertyContext = null) {
    if (Array.isArray(value)) {
      return value.map(item => this.compactValue(item, mainContext, propertyKey, propertyContext));
    }
    
    if (typeof value === 'object' && value !== null) {
      if (value['@id']) {
        // This is a reference object - compact the @id value
        const compactedId = this.compactIri(value['@id'], propertyContext || mainContext);
        
        // If the property context indicates this should be a string reference, return just the string
        const propertyDef = mainContext[propertyKey];
        if (propertyDef && propertyDef['@type'] === '@id') {
          return compactedId;
        }
        
        return { '@id': compactedId };
      } else {
        // This is a nested object - compact it recursively
        return this.compactObject(value, mainContext);
      }
    }
    
    if (typeof value === 'string') {
      // Compact IRI values
      return this.compactIri(value, propertyContext || mainContext);
    }
    
    return value;
  }

  // Compact an IRI using the appropriate context with correct prefix handling
  compactIri(iri, context) {
    if (!iri || typeof iri !== 'string' || !iri.startsWith('http')) {
      return iri;
    }
    
    // Check for exact reverse mappings in context
    for (const [key, value] of Object.entries(context)) {
      if (key.startsWith('@')) continue;
      
      if (typeof value === 'string' && iri === value) {
        console.log(`🔄 Compacting IRI '${iri}' to '${key}' using direct mapping`);
        return key;
      } else if (typeof value === 'object' && value !== null && value['@id'] === iri) {
        console.log(`🔄 Compacting IRI '${iri}' to '${key}' using object mapping`);
        return key;
      }
    }
    
    // Check for prefix-based compaction (corrected logic)
    for (const [prefix, baseUri] of Object.entries(context)) {
      if (prefix.startsWith('@')) continue;
      
      if (typeof baseUri === 'string' && iri.startsWith(baseUri)) {
        const suffix = iri.substring(baseUri.length);
        if (suffix) {  // Any suffix is valid, including paths with slashes
          const compacted = prefix + ':' + suffix;
          console.log(`🔄 Compacting IRI '${iri}' to '${compacted}' using prefix '${prefix}'`);
          return compacted;
        }
      }
    }
    
    // Check for base/vocab compaction
    const base = context['@base'];
    const vocab = context['@vocab'];
    
    if (base && iri.startsWith(base)) {
      const relative = iri.substring(base.length);
      if (relative) {
        console.log(`🔄 Compacting IRI '${iri}' to '${relative}' using @base`);
        return relative;
      }
    }
    
    if (vocab && iri.startsWith(vocab)) {
      const term = iri.substring(vocab.length);
      if (term) {
        console.log(`🔄 Compacting IRI '${iri}' to '${term}' using @vocab`);
        return term;
      }
    }
    
    // Return original IRI if no compaction possible
    return iri;
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