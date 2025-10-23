// Fixed Document fetching and loading with better CORS error handling
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
      
      // Build fetch URL - handle empty proxy (direct fetch)
      let fetchUrl;
      if (proxy === '') {
        fetchUrl = url;
      } else {
        // Ensure proper proxy URL construction
        if (proxy.endsWith('=') || proxy.endsWith('?')) {
          fetchUrl = proxy + encodeURIComponent(url);
        } else {
          fetchUrl = proxy + url;
        }
      }
      
      try {
        console.log(`🔄 Attempting to fetch ${url} ${proxy ? `via proxy ${proxy}` : 'directly'}...`);
        
        const response = await fetch(fetchUrl, {
          method: 'GET',
          headers: {
            'Accept': 'application/ld+json, application/json, text/plain',
            'User-Agent': 'CMIP-LD-Viewer/1.0'
          },
          mode: 'cors',
          // Add timeout to prevent hanging
          signal: AbortSignal.timeout(10000) // 10 seconds
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await this.parseResponse(response);
        this.loadedDocuments.set(url, data);
        
        console.log(`✅ Successfully fetched ${url}:`, Object.keys(data));
        
        return data;
        
      } catch (error) {
        // Log specific error types for debugging
        if (error.name === 'AbortError') {
          console.warn(`⏰ Timeout fetching ${url} ${proxy ? `via proxy ${proxy}` : 'directly'}`);
        } else if (error.message.includes('CORS') || 
                   error.message.includes('Failed to fetch') ||
                   error.message.includes('blocked by CORS') ||
                   error.message.includes('No \'Access-Control-Allow-Origin\'')) {
          console.warn(`🚫 CORS error fetching ${url} ${proxy ? `via proxy ${proxy}` : 'directly'}: ${error.message}`);
        } else {
          console.warn(`❌ Error fetching ${url} ${proxy ? `via proxy ${proxy}` : 'directly'}: ${error.message}`);
        }
        
        lastError = error;
        continue;
      }
    }
    
    console.error(`❌ Failed to fetch ${url} with all available methods. Last error:`, lastError);
    throw lastError;
  }

  async parseResponse(response) {
    const contentType = response.headers.get('content-type') || '';
    
    if (contentType.includes('application/json') || 
        contentType.includes('application/ld+json') ||
        contentType.includes('text/plain')) {
      try {
        return await response.json();
      } catch (jsonError) {
        // If JSON parsing fails, try parsing as text and then JSON
        const text = await response.text();
        try {
          return JSON.parse(text);
        } catch (parseError) {
          // Check if it's an HTML error page
          if (text.trim().startsWith('<')) {
            throw new Error(`Server returned HTML instead of JSON. This usually indicates a CORS or server error.`);
          }
          throw new Error(`Response is not valid JSON: ${text.substring(0, 200)}${text.length > 200 ? '...' : ''}`);
        }
      }
    } else {
      // Try to parse as JSON anyway
      const text = await response.text();
      try {
        return JSON.parse(text);
      } catch (parseError) {
        // Check if it's an HTML error page
        if (text.trim().startsWith('<')) {
          throw new Error(`Server returned HTML (Content-Type: ${contentType}). This usually indicates a CORS or server error.`);
        }
        throw new Error(`Response is not valid JSON (Content-Type: ${contentType}): ${text.substring(0, 200)}${text.length > 200 ? '...' : ''}`);
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
          console.warn(`⚠️ Could not load context: ${resolvedUrl}`, e.message);
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



  // Collect property-specific contexts that need to be resolved
  async collectPropertySpecificContexts(context, baseUrl, propertyContexts) {
    if (typeof context === 'object' && context !== null && !Array.isArray(context)) {
      for (const [key, value] of Object.entries(context)) {
        if (typeof value === 'object' && value !== null && value['@context']) {
          console.log(`🔄 Found property-specific context for '${key}': ${value['@context']}`);
          
          // Resolve the property-specific context
          const resolvedPropContext = await this.collectAndLoadContexts(value['@context'], baseUrl);
          propertyContexts[key] = resolvedPropContext;
          
          console.log(`✅ Resolved property-specific context for '${key}' with`, Object.keys(resolvedPropContext).length, 'terms');
        }
      }
    } else if (Array.isArray(context)) {
      for (const ctx of context) {
        await this.collectPropertySpecificContexts(ctx, baseUrl, propertyContexts);
      }
    }
  }

  // Merge context definitions
  mergeContext(target, source) {
    if (typeof source === 'object' && source !== null && !Array.isArray(source)) {
      // Special handling for @base - don't overwrite if already set
      if (source['@base'] && !target['@base']) {
        target['@base'] = source['@base'];
      }
      // Special handling for @vocab - don't overwrite if already set
      if (source['@vocab'] && !target['@vocab']) {
        target['@vocab'] = source['@vocab'];
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
        console.error(`📋 Document loader failed for: ${url}`, error.message);
        throw new Error(`Failed to load document: ${url} - ${error.message}`);
      }
    };
  }

  clear() {
    this.loadedDocuments.clear();
    this.contextDocuments.clear();
  }
}