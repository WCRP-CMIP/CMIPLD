// Context expansion handling
export class ContextExpander {
  constructor(documentLoader, prefixMapping) {
    this.documentLoader = documentLoader;
    this.prefixMapping = prefixMapping;
  }

  // Expand context references (respects insertContext checkbox)
  expandContextReferences(obj, insertContext, visited = new Set()) {
    if (!insertContext) {
      console.log('📝 Context expansion disabled - not expanding context references in-place');
      return obj;
    }

    console.log('📝 Context expansion enabled - expanding context references in-place');
    
    if (typeof obj !== 'object' || obj === null || visited.has(obj)) {
      return obj;
    }
    visited.add(obj);

    if (Array.isArray(obj)) {
      const expanded = obj.map(item => this.expandContextReferences(item, insertContext, visited));
      visited.delete(obj);
      return expanded;
    }

    const expanded = {};
    
    for (const [key, value] of Object.entries(obj)) {
      if (key === '@context') {
        expanded[key] = this.expandContext(value, visited);
      } else {
        expanded[key] = this.expandContextReferences(value, insertContext, visited);
      }
    }
    
    visited.delete(obj);
    return expanded;
  }

  // Expand context by substituting URLs with actual content
  expandContext(context, visited = new Set()) {
    if (typeof context === 'string') {
      if (context.startsWith('http') || context.includes(':')) {
        const resolvedUrl = this.resolvePrefix(context);
        if (this.documentLoader.contextDocuments.has(resolvedUrl)) {
          const contextDoc = this.documentLoader.contextDocuments.get(resolvedUrl);
          if (contextDoc['@context']) {
            return this.expandContext(contextDoc['@context'], visited);
          }
        }
      }
      return context;
    } else if (Array.isArray(context)) {
      return context.map(ctx => this.expandContext(ctx, visited));
    } else if (typeof context === 'object' && context !== null) {
      // Don't recursively expand @context within context objects
      // Just return the context object as-is
      return context;
    }
    
    return context;
  }

  resolvePrefix(query) {
    if (typeof query !== 'string' || query.startsWith('http')) {
      return query;
    }

    const colonIndex = query.indexOf(':');
    if (colonIndex === -1) {
      return query;
    }

    const prefix = query.substring(0, colonIndex);
    const suffix = query.substring(colonIndex + 1);

    if (this.prefixMapping[prefix]) {
      if (suffix === '' || suffix === '/') {
        return `${this.prefixMapping[prefix]}graph.jsonld`;
      }
      return `${this.prefixMapping[prefix]}${suffix}`;
    }

    return query;
  }
}
