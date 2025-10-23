// Auto-substitution Document Manager - automatically fetches and substitutes linked content
export class AutoSubstitutionManager {
  constructor(documentLoader, contextResolutionManager, jsonldProcessor, referenceManager) {
    this.documentLoader = documentLoader;
    this.contextResolutionManager = contextResolutionManager;
    this.jsonldProcessor = jsonldProcessor;
    this.referenceManager = referenceManager;
    this.substitutionCache = new Map();
    this.maxDepth = 2;
    this.currentDepth = 0;
  }

  // Set maximum depth for auto-substitution
  setMaxDepth(depth) {
    this.maxDepth = depth;
  }

  // Auto-substitute linked entries in the data structure
  async autoSubstituteLinkedEntries(data, baseUrl, depth = 0, visited = new Set()) {
    if (depth >= this.maxDepth || !data || visited.has(data)) {
      return data;
    }

    this.currentDepth = depth;
    console.log(`🔄 Auto-substituting at depth ${depth}, max depth ${this.maxDepth}`);

    if (typeof data === 'object' && data !== null) {
      visited.add(data);

      if (Array.isArray(data)) {
        // Process array items
        const processedArray = [];
        for (const item of data) {
          const processedItem = await this.autoSubstituteLinkedEntries(item, baseUrl, depth, visited);
          processedArray.push(processedItem);
        }
        visited.delete(data);
        return processedArray;
      } else {
        // Process object
        const result = {};
        
        for (const [key, value] of Object.entries(data)) {
          if (await this.shouldSubstituteValue(key, value, depth)) {
            // This is a linked reference that should be substituted
            const substituted = await this.fetchAndSubstituteReference(value, key, baseUrl, depth + 1);
            result[key] = substituted;
          } else if (typeof value === 'object' && value !== null) {
            // Recursively process nested objects/arrays
            result[key] = await this.autoSubstituteLinkedEntries(value, baseUrl, depth, visited);
          } else {
            // Keep primitive values as-is
            result[key] = value;
          }
        }
        
        visited.delete(data);
        return result;
      }
    }

    return data;
  }

  // Check if a value should be substituted
  async shouldSubstituteValue(key, value, currentDepth) {
    // Don't substitute if we're at max depth
    if (currentDepth >= this.maxDepth) {
      return false;
    }

    // Check for simple @id-only objects
    if (typeof value === 'object' && value !== null && !Array.isArray(value) &&
        Object.keys(value).length === 1 && value['@id']) {
      const idValue = value['@id'];
      const resolvedUrl = this.referenceManager.expandReference(idValue, '@id');
      return resolvedUrl && resolvedUrl.startsWith('http') && resolvedUrl !== idValue;
    }

    // Check for string values in linked properties
    if (typeof value === 'string' && this.referenceManager.isLinkedProperty(key)) {
      const resolvedUrl = this.referenceManager.expandReference(value, key);
      return resolvedUrl && resolvedUrl.startsWith('http') && resolvedUrl !== value;
    }

    // Check for arrays of linked references
    if (Array.isArray(value)) {
      return value.some(item => {
        if (typeof item === 'object' && item !== null && Object.keys(item).length === 1 && item['@id']) {
          const resolvedUrl = this.referenceManager.expandReference(item['@id'], '@id');
          return resolvedUrl && resolvedUrl.startsWith('http');
        }
        if (typeof item === 'string' && this.referenceManager.isLinkedProperty(key)) {
          const resolvedUrl = this.referenceManager.expandReference(item, key);
          return resolvedUrl && resolvedUrl.startsWith('http');
        }
        return false;
      });
    }

    return false;
  }

  // Fetch and substitute a reference
  async fetchAndSubstituteReference(value, key, baseUrl, depth) {
    try {
      let urlToFetch;
      let isArraySubstitution = false;
      let itemsToProcess = [];

      // Determine what to fetch
      if (Array.isArray(value)) {
        isArraySubstitution = true;
        // Collect all URLs to fetch from the array
        for (const item of value) {
          if (typeof item === 'object' && item !== null && item['@id']) {
            const resolvedUrl = this.referenceManager.expandReference(item['@id'], '@id');
            if (resolvedUrl && resolvedUrl.startsWith('http')) {
              itemsToProcess.push({ original: item, url: resolvedUrl, type: 'object' });
            } else {
              itemsToProcess.push({ original: item, url: null, type: 'object' });
            }
          } else if (typeof item === 'string' && this.referenceManager.isLinkedProperty(key)) {
            const resolvedUrl = this.referenceManager.expandReference(item, key);
            if (resolvedUrl && resolvedUrl.startsWith('http')) {
              itemsToProcess.push({ original: item, url: resolvedUrl, type: 'string' });
            } else {
              itemsToProcess.push({ original: item, url: null, type: 'string' });
            }
          } else {
            itemsToProcess.push({ original: item, url: null, type: 'other' });
          }
        }
      } else if (typeof value === 'object' && value !== null && value['@id']) {
        urlToFetch = this.referenceManager.expandReference(value['@id'], '@id');
      } else if (typeof value === 'string') {
        urlToFetch = this.referenceManager.expandReference(value, key);
      }

      // Process array substitution
      if (isArraySubstitution) {
        const processedArray = [];
        
        for (const item of itemsToProcess) {
          if (item.url) {
            try {
              const substituted = await this.fetchSingleReference(item.url, depth);
              processedArray.push(substituted);
            } catch (error) {
              console.warn(`⚠️ Failed to fetch array item ${item.url}:`, error.message);
              processedArray.push(item.original); // Keep original on error
            }
          } else {
            processedArray.push(item.original);
          }
        }
        
        return processedArray;
      }

      // Process single substitution
      if (urlToFetch && urlToFetch.startsWith('http')) {
        return await this.fetchSingleReference(urlToFetch, depth);
      }

      return value; // Return original if no substitution needed

    } catch (error) {
      console.warn(`⚠️ Failed to substitute reference:`, error.message);
      return value; // Return original value on error
    }
  }

  // Fetch a single reference and return its processed content
  async fetchSingleReference(url, depth) {
    // Check cache first
    if (this.substitutionCache.has(url)) {
      console.log(`📋 Using cached substitution: ${url}`);
      const cached = this.substitutionCache.get(url);
      // Still need to process recursively if within depth limit
      if (depth < this.maxDepth) {
        return await this.autoSubstituteLinkedEntries(cached, url, depth);
      }
      return cached;
    }

    console.log(`📥 Fetching for substitution: ${url} at depth ${depth}`);

    try {
      // Fetch the document
      const rawData = await this.documentLoader.fetchDocument(url);
      console.log(`✅ Fetched document for substitution: ${url}`);

      // Try to resolve context and expand, but handle failures gracefully
      let mainEntity = null;
      
      try {
        // Resolve context
        const resolvedContext = await this.contextResolutionManager.buildResolvedContext(rawData, url);
        
        // Expand the document
        const originalContext = this.jsonldProcessor.resolvedContext;
        this.jsonldProcessor.resolvedContext = resolvedContext;
        
        let expandedData;
        try {
          expandedData = await this.jsonldProcessor.safeExpand(rawData);
        } catch (expandError) {
          console.warn(`⚠️ JSON-LD expansion failed for ${url}, using manual expansion:`, expandError.message);
          expandedData = this.jsonldProcessor.createManualExpansion(rawData, url);
        }
        
        // Restore context
        this.jsonldProcessor.resolvedContext = originalContext;

        // Find the main entity in the expanded data
        if (expandedData && expandedData.length > 0) {
          // Look for entity with matching @id
          mainEntity = expandedData.find(item => item['@id'] === url) || expandedData[0];
        }
      } catch (contextError) {
        console.warn(`⚠️ Context resolution failed for ${url}:`, contextError.message);
      }

      // If expansion failed, use the raw data as fallback
      if (!mainEntity) {
        console.log(`⚠️ No expanded entity found, using raw data for ${url}`);
        
        // Create a clean version of the raw data with proper @id
        mainEntity = { ...rawData };
        
        // Ensure it has the correct @id
        if (!mainEntity['@id']) {
          mainEntity['@id'] = url;
        }
        
        // Remove context if it's a relative reference (causes problems)
        if (mainEntity['@context'] && typeof mainEntity['@context'] === 'string' && 
            !mainEntity['@context'].startsWith('http')) {
          delete mainEntity['@context'];
        }
        
        console.log(`📋 Using raw data for ${url}:`, Object.keys(mainEntity));
      }

      // Cache the result
      this.substitutionCache.set(url, mainEntity);

      // Set up temporary reference manager context for recursive processing
      const originalResolvedContext = this.referenceManager.resolvedContext;
      this.referenceManager.setResolvedContext(resolvedContext);

      try {
        // Recursively process the substituted content if within depth limit
        if (depth < this.maxDepth) {
          const processedEntity = await this.autoSubstituteLinkedEntries(mainEntity, url, depth);
          return processedEntity;
        }
        return mainEntity;
      } finally {
        // Restore original context
        this.referenceManager.setResolvedContext(originalResolvedContext);
      }

    } catch (error) {
      console.error(`❌ Failed to fetch reference ${url}:`, error);
      // Return a reference object on error
      return { '@id': url, '_error': `Failed to load: ${error.message}` };
    }
  }

  // Clear the substitution cache
  clearCache() {
    this.substitutionCache.clear();
  }

  // Get cache statistics
  getCacheStats() {
    return {
      size: this.substitutionCache.size,
      urls: Array.from(this.substitutionCache.keys())
    };
  }
}
