// Context Resolution Manager - handles all context resolution logic
export class ContextResolutionManager {
  constructor(documentLoader) {
    this.documentLoader = documentLoader;
  }

  // Build resolved context with property-specific contexts
  async buildResolvedContext(document, baseUrl) {
    if (!document['@context']) {
      return {};
    }

    try {
      const resolvedContext = await this.resolveContext(document['@context'], baseUrl);
      console.log(`✅ Resolved context for ${baseUrl} with`, Object.keys(resolvedContext).length, 'terms');
      
      // Log property-specific contexts if any
      const propSpecificContexts = Object.keys(resolvedContext).filter(key => 
        resolvedContext[key] && 
        typeof resolvedContext[key] === 'object' && 
        resolvedContext[key]['@resolvedContext']
      );
      if (propSpecificContexts.length > 0) {
        console.log(`✅ Found property-specific contexts in ${baseUrl} for:`, propSpecificContexts.join(', '));
      }
      
      return resolvedContext;
    } catch (contextError) {
      console.warn(`⚠️ Context resolution failed for ${baseUrl}:`, contextError.message);
      return {};
    }
  }

  // Build merged context from multiple documents
  async buildMergedContext(documents) {
    const mergedContext = {};
    
    // Merge resolved contexts from all documents
    for (const [url, doc] of documents) {
      if (doc.resolvedContext && Object.keys(doc.resolvedContext).length > 0) {
        console.log(`🔄 Merging context from ${url}:`, Object.keys(doc.resolvedContext).length, 'terms');
        Object.assign(mergedContext, doc.resolvedContext);
      } else if (doc.context) {
        // Fallback to resolving context if not already resolved
        try {
          const resolvedContext = await this.resolveContext(doc.context, url);
          if (Object.keys(resolvedContext).length > 0) {
            console.log(`🔄 Late-resolving context from ${url}:`, Object.keys(resolvedContext).length, 'terms');
            Object.assign(mergedContext, resolvedContext);
            // Store the resolved context
            doc.resolvedContext = resolvedContext;
          }
        } catch (error) {
          console.warn(`⚠️ Failed to resolve context from ${url}:`, error.message);
        }
      }
    }
    
    console.log('📝 Built merged context with', Object.keys(mergedContext).length, 'terms');
    return mergedContext;
  }

  // Build comprehensive compaction context that includes property-scoped contexts
  buildCompactionContextWithPropertyScopes(mainContext, mergedContext = null) {
    const compactionContext = {};
    
    // Start with merged context if available, otherwise main context
    const baseContext = mergedContext || mainContext || {};
    
    // Add all terms from the base context
    for (const [key, value] of Object.entries(baseContext)) {
      if (typeof value === 'object' && value !== null && value['@resolvedContext']) {
        // This is a property with resolved scoped context
        console.log(`🔄 Processing property-scoped context for '${key}' in compaction context`);
        
        // Add the property definition itself (preserving @type: @id, etc.)
        compactionContext[key] = {
          '@type': value['@type'] || '@id',  // Ensure it's marked as an ID property
          '@context': value['@resolvedContext']  // Use resolved context for compaction
        };
        
        // Also flatten property-scoped terms into the main context with prefixes
        const propContext = value['@resolvedContext'];
        for (const [propKey, propValue] of Object.entries(propContext)) {
          if (!propKey.startsWith('@') && !compactionContext[propKey]) {
            // Add property-scoped terms, but don't override existing terms
            compactionContext[propKey] = propValue;
          }
        }
        
        console.log(`✅ Added property-scoped terms for '${key}':`, Object.keys(propContext).filter(k => !k.startsWith('@')));
      } else if (typeof value === 'string' || (typeof value === 'object' && value !== null && !value['@resolvedContext'])) {
        // Regular context term
        compactionContext[key] = value;
      }
    }
    
    console.log(`📋 Built comprehensive compaction context with ${Object.keys(compactionContext).length} terms`);
    return compactionContext;
  }

  // Resolve context (internal implementation)
  async resolveContext(context, baseUrl) {
    const result = {};
    
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
            console.warn(`⚠️ Failed to resolve relative context URL: ${context} with base ${baseUrl}`);
            return result;
          }
        } else {
          console.warn(`⚠️ Cannot resolve relative context '${context}' without base URL`);
          return result;
        }
      }
      
      try {
        const contextDoc = await this.documentLoader.fetchDocument(contextUrl);
        if (contextDoc && contextDoc['@context']) {
          return this.resolveContext(contextDoc['@context'], contextUrl);
        } else if (contextDoc && typeof contextDoc === 'object') {
          // The entire document might be the context
          return contextDoc;
        }
      } catch (e) {
        console.warn(`Could not resolve context: ${contextUrl}`, e.message);
      }
    } else if (Array.isArray(context)) {
      for (const ctx of context) {
        const resolved = await this.resolveContext(ctx, baseUrl);
        Object.assign(result, resolved);
      }
    } else if (typeof context === 'object' && context !== null) {
      // Process object context and resolve property-scoped contexts
      for (const [key, value] of Object.entries(context)) {
        if (typeof value === 'object' && value !== null && value['@context']) {
          // This property has its own context - resolve it
          console.log(`🔄 Found property-scoped context for '${key}':`, value['@context']);
          try {
            const propContext = await this.resolveContext(value['@context'], baseUrl);
            
            // Store the resolved property-scoped context
            result[key] = {
              ...value,
              '@resolvedContext': propContext  // Store resolved context for later use
            };
            
            console.log(`✅ Resolved property-scoped context for '${key}' with`, Object.keys(propContext).length, 'terms');
          } catch (propError) {
            console.warn(`⚠️ Failed to resolve property-scoped context for '${key}':`, propError.message);
            // Store the original definition even if resolution failed
            result[key] = value;
          }
        } else {
          // Regular context entry
          result[key] = value;
        }
      }
    }
    
    return result;
  }
}
