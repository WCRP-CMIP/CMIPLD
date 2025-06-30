// Document fetching and loading
import { Utils } from './utils.js';

export class DocumentLoader {
  constructor(corsProxies) {
    this.corsProxies = corsProxies;
    this.loadedDocuments = new Map();
    this.contextDocuments = new Map();
  }

  // Fetch JSON-LD document with CORS proxy fallback
  async fetchDocument(url) {
    if (this.loadedDocuments.has(url)) {
      return this.loadedDocuments.get(url);
    }

    // Skip invalid URLs
    if (!url.startsWith('http')) {
      console.warn(`Skipping invalid URL: ${url}`);
      throw new Error(`Invalid URL: ${url}`);
    }

    let lastError = null;
    
    // Try each CORS proxy in order
    for (let i = 0; i < this.corsProxies.length; i++) {
      const proxy = this.corsProxies[i];
      const fetchUrl = proxy + encodeURIComponent(url);
      
      try {
        const response = await fetch(fetchUrl, {
          method: 'GET',
          headers: {
            'Accept': 'application/ld+json, application/json, text/plain',
            'User-Agent': 'CMIP-LD-Viewer/1.0'
          },
          mode: 'cors'
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await this.parseResponse(response);
        this.loadedDocuments.set(url, data);
        
        // Log fetched data as warning
        console.warn(`📦 Fetched linked document from ${url}:`, data);
        
        return data;
        
      } catch (error) {
        // Only log CORS errors
        if (error.message.includes('CORS') || error.message.includes('Failed to fetch')) {
          console.error(`CORS error fetching ${url} ${proxy ? `via proxy ${proxy}` : 'directly'}:`, error.message);
        }
        lastError = error;
        continue;
      }
    }
    
    console.error(`Failed to fetch ${url} with all available methods:`, lastError);
    throw lastError;
  }

  async parseResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    
    if (contentType.includes('application/json') || contentType.includes('application/ld+json')) {
      return await response.json();
    } else {
      // Try to parse as JSON anyway
      const text = await response.text();
      try {
        return JSON.parse(text);
      } catch (parseError) {
        throw new Error(`Response is not valid JSON: ${text.substring(0, 100)}...`);
      }
    }
  }

  // Recursively collect and load all context URLs
  async collectAndLoadContexts(context, baseUrl, loaded = new Set()) {
    const contexts = {};
    
    if (typeof context === 'string') {
      const resolvedUrl = context.startsWith('http') ? context : Utils.resolveUrl(context, baseUrl);
      if (!loaded.has(resolvedUrl)) {
        loaded.add(resolvedUrl);
        try {
          const contextDoc = await this.fetchDocument(resolvedUrl);
          this.contextDocuments.set(resolvedUrl, contextDoc);
          
          if (contextDoc['@context']) {
            const nestedContexts = await this.collectAndLoadContexts(contextDoc['@context'], resolvedUrl, loaded);
            Object.assign(contexts, nestedContexts);
            this.mergeContext(contexts, contextDoc['@context']);
          }
        } catch (e) {
          console.warn(`Could not load context: ${resolvedUrl}`, e);
        }
      }
    } else if (Array.isArray(context)) {
      for (const ctx of context) {
        const nestedContexts = await this.collectAndLoadContexts(ctx, baseUrl, loaded);
        Object.assign(contexts, nestedContexts);
      }
    } else if (typeof context === 'object' && context !== null) {
      this.mergeContext(contexts, context);
      
      // Look for nested @context references
      for (const [key, value] of Object.entries(context)) {
        if (typeof value === 'object' && value !== null && value['@context']) {
          const nestedContexts = await this.collectAndLoadContexts(value['@context'], baseUrl, loaded);
          Object.assign(contexts, nestedContexts);
        }
      }
    }
    
    return contexts;
  }

  // Build comprehensive context from all loaded documents
  async buildResolvedContext(data, baseUrl) {
    const resolvedContext = {};

    // Collect contexts from the main document
    if (data['@context']) {
      const mainContexts = await this.collectAndLoadContexts(data['@context'], baseUrl);
      Object.assign(resolvedContext, mainContexts);
      
      // If the main context has @base, preserve it
      if (typeof data['@context'] === 'object' && data['@context']['@base']) {
        resolvedContext['@base'] = data['@context']['@base'];
      }
    }

    // Collect contexts from all loaded documents
    for (const [url, doc] of this.loadedDocuments) {
      if (doc['@context']) {
        const docContexts = await this.collectAndLoadContexts(doc['@context'], url);
        Object.assign(resolvedContext, docContexts);
      }
    }

    return resolvedContext;
  }

  // Merge context definitions
  mergeContext(target, source) {
    if (typeof source === 'object' && source !== null && !Array.isArray(source)) {
      // Special handling for @base - don't overwrite if already set
      if (source['@base'] && !target['@base']) {
        target['@base'] = source['@base'];
      }
      // Merge other properties
      Object.assign(target, source);
    } else if (Array.isArray(source)) {
      source.forEach(ctx => this.mergeContext(target, ctx));
    }
  }

  // Create document loader for JSON-LD operations
  createDocumentLoader() {
    return async (url) => {
      if (this.loadedDocuments.has(url)) {
        const doc = this.loadedDocuments.get(url);
        return { contextUrl: null, document: doc, documentUrl: url };
      }
      
      if (this.contextDocuments.has(url)) {
        const doc = this.contextDocuments.get(url);
        return { contextUrl: null, document: doc, documentUrl: url };
      }
      
      try {
        const doc = await this.fetchDocument(url);
        return { contextUrl: null, document: doc, documentUrl: url };
      } catch (error) {
        console.error(`Document loader failed for: ${url}`, error.message);
        throw new Error(`Failed to load document: ${url}`);
      }
    };
  }

  clear() {
    this.loadedDocuments.clear();
    this.contextDocuments.clear();
  }
}
