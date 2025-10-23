// Link Content Resolver - resolves linked entries by downloading and substituting content in place
import { Utils } from './utils.js';

export class LinkContentResolver {
  constructor(documentLoader, referenceManager, jsonldProcessor) {
    this.documentLoader = documentLoader;
    this.referenceManager = referenceManager;
    this.jsonldProcessor = jsonldProcessor;
    this.resolvedContent = new Map(); // Cache for resolved content
    this.maxDepth = 3;
    this.visitedUrls = new Set(); // Track visited URLs to prevent infinite loops
  }

  /**
   * Main function: Resolve linked entries by downloading their content and substituting in place
   * @param {Object} data - The data structure containing linked entries
   * @param {string} baseUrl - Base URL for resolving relative references
   * @param {number} maxDepth - Maximum depth for recursive resolution
   * @returns {Object} - Data with linked entries resolved and substituted
   */
  async resolveLinkedEntries(data, baseUrl, maxDepth = 3) {
    console.log(`🔗 Starting link content resolution with max depth: ${maxDepth}`);
    
    this.maxDepth = maxDepth;
    this.resolvedContent.clear();
    this.visitedUrls.clear();
    
    try {
      const resolvedData = await this.processDataStructure(data, baseUrl, 0);
      console.log(`✅ Link content resolution completed. Resolved ${this.resolvedContent.size} unique URLs.`);
      return resolvedData;
    } catch (error) {
      console.error(`❌ Link content resolution failed:`, error);
      throw error;
    }
  }

  /**
   * Process data structure recursively to find and resolve linked entries
   * @param {*} data - Current data to process
   * @param {string} baseUrl - Base URL for resolving references
   * @param {number} currentDepth - Current recursion depth
   * @param {Set} visited - Set of visited objects to prevent cycles
   * @returns {*} - Processed data with resolved links
   */
  async processDataStructure(data, baseUrl, currentDepth, visited = new Set()) {
    // Stop if max depth exceeded or data is invalid
    if (currentDepth >= this.maxDepth || !data || visited.has(data)) {
      return data;
    }

    // Handle primitive types
    if (typeof data !== 'object') {
      return data;
    }

    visited.add(data);

    try {
      // Handle arrays
      if (Array.isArray(data)) {
        const processedArray = [];
        for (const item of data) {
          const processedItem = await this.processDataStructure(item, baseUrl, currentDepth, visited);
          processedArray.push(processedItem);
        }
        visited.delete(data);
        return processedArray;
      }

      // Handle objects
      const processedObject = {};
      
      for (const [key, value] of Object.entries(data)) {
        const resolvedValue = await this.resolveValue(key, value, baseUrl, currentDepth, visited);
        processedObject[key] = resolvedValue;
      }

      visited.delete(data);
      return processedObject;

    } catch (error) {
      visited.delete(data);
      console.warn(`⚠️ Error processing data structure at depth ${currentDepth}:`, error.message);
      return data; // Return original data on error
    }
  }

  /**
   * Resolve a specific value, checking if it's a linked reference that needs to be resolved
   * @param {string} key - Property key
   * @param {*} value - Property value
   * @param {string} baseUrl - Base URL for resolving references
   * @param {number} currentDepth - Current recursion depth
   * @param {Set} visited - Set of visited objects
   * @returns {*} - Resolved value
   */
  async resolveValue(key, value, baseUrl, currentDepth, visited) {
    try {
      // Handle @id-only objects (typical JSON-LD references)
      if (this.isIdOnlyObject(value)) {
        const url = this.resolveUrl(value['@id'], key, baseUrl);
        if (url && this.shouldResolveUrl(url)) {
          const resolvedContent = await this.fetchAndResolveContent(url, currentDepth + 1);
          if (resolvedContent) {
            console.log(`🔄 Substituted @id reference '${key}': ${value['@id']} -> resolved content`);
            return resolvedContent;
          }
        }
        return value;
      }

      // Handle string references in linked properties
      if (typeof value === 'string' && this.isLinkedProperty(key)) {
        const url = this.resolveUrl(value, key, baseUrl);
        if (url && this.shouldResolveUrl(url)) {
          const resolvedContent = await this.fetchAndResolveContent(url, currentDepth + 1);
          if (resolvedContent) {
            console.log(`🔄 Substituted string reference '${key}': ${value} -> resolved content`);
            return resolvedContent;
          }
        }
        return value;
      }

      // Handle arrays that might contain references
      if (Array.isArray(value)) {
        const processedArray = [];
        for (let i = 0; i < value.length; i++) {
          const item = value[i];
          
          // Check if array item is a reference
          if (this.isIdOnlyObject(item)) {
            const url = this.resolveUrl(item['@id'], key, baseUrl);
            if (url && this.shouldResolveUrl(url)) {
              const resolvedContent = await this.fetchAndResolveContent(url, currentDepth + 1);
              if (resolvedContent) {
                console.log(`🔄 Substituted array reference '${key}[${i}]': ${item['@id']} -> resolved content`);
                processedArray.push(resolvedContent);
                continue;
              }
            }
          } else if (typeof item === 'string' && this.isLinkedProperty(key)) {
            const url = this.resolveUrl(item, key, baseUrl);
            if (url && this.shouldResolveUrl(url)) {
              const resolvedContent = await this.fetchAndResolveContent(url, currentDepth + 1);
              if (resolvedContent) {
                console.log(`🔄 Substituted array string reference '${key}[${i}]': ${item} -> resolved content`);
                processedArray.push(resolvedContent);
                continue;
              }
            }
          }
          
          // Recursively process non-reference items
          const processedItem = await this.processDataStructure(item, baseUrl, currentDepth, visited);
          processedArray.push(processedItem);
        }
        return processedArray;
      }

      // Handle nested objects
      if (typeof value === 'object' && value !== null) {
        return await this.processDataStructure(value, baseUrl, currentDepth, visited);
      }

      // Return primitive values as-is
      return value;

    } catch (error) {
      console.warn(`⚠️ Error resolving value for key '${key}':`, error.message);
      return value; // Return original value on error
    }
  }

  /**
   * Fetch and resolve content from a URL
   * @param {string} url - URL to fetch
   * @param {number} currentDepth - Current recursion depth
   * @returns {Object|null} - Resolved content or null if failed
   */
  async fetchAndResolveContent(url, currentDepth) {
    // Check cache first
    if (this.resolvedContent.has(url)) {
      console.log(`📋 Using cached content for: ${url}`);
      const cached = this.resolvedContent.get(url);
      
      // Apply recursive resolution if within depth limit
      if (currentDepth < this.maxDepth) {
        return await this.processDataStructure(cached, url, currentDepth);
      }
      return cached;
    }

    // Prevent infinite loops
    if (this.visitedUrls.has(url)) {
      console.log(`🔄 Skipping already visited URL: ${url}`);
      return null;
    }

    this.visitedUrls.add(url);

    try {
      console.log(`📥 Fetching content from: ${url} (depth: ${currentDepth})`);
      
      // Fetch the document
      const rawDocument = await this.documentLoader.fetchDocument(url);
      
      // Process the document to extract the main entity
      const mainEntity = await this.extractMainEntity(rawDocument, url);
      
      if (!mainEntity) {
        console.warn(`⚠️ No main entity found in: ${url}`);
        return null;
      }

      // Cache the resolved content
      this.resolvedContent.set(url, mainEntity);
      console.log(`✅ Successfully resolved and cached content from: ${url}`);

      // Apply recursive resolution if within depth limit
      if (currentDepth < this.maxDepth) {
        return await this.processDataStructure(mainEntity, url, currentDepth);
      }
      
      return mainEntity;

    } catch (error) {
      console.error(`❌ Failed to fetch and resolve content from ${url}:`, error.message);
      return null;
    } finally {
      this.visitedUrls.delete(url);
    }
  }

  /**
   * Extract the main entity from a fetched document
   * @param {Object} document - Raw document data
   * @param {string} url - Document URL
   * @returns {Object|null} - Main entity or null if not found
   */
  async extractMainEntity(document, url) {
    try {
      // If the document has @context, try to expand it properly
      if (document['@context']) {
        // Build resolved context for this document
        const resolvedContext = await this.buildResolvedContext(document, url);
        
        // Temporarily set the resolved context for JSON-LD processing
        const originalContext = this.jsonldProcessor.resolvedContext;
        this.jsonldProcessor.resolvedContext = resolvedContext;
        
        try {
          // Expand the document
          const expandedData = await this.jsonldProcessor.safeExpand(document);
          
          // Find the main entity
          if (expandedData && expandedData.length > 0) {
            // Look for entity with matching @id first
            const mainEntity = expandedData.find(item => item['@id'] === url) || expandedData[0];
            return mainEntity;
          }
        } catch (expandError) {
          console.warn(`⚠️ JSON-LD expansion failed for ${url}, using manual extraction:`, expandError.message);
        } finally {
          // Restore original context
          this.jsonldProcessor.resolvedContext = originalContext;
        }
      }

      // Fallback: extract main entity manually
      return this.extractMainEntityManually(document, url);

    } catch (error) {
      console.warn(`⚠️ Error extracting main entity from ${url}:`, error.message);
      return document; // Return raw document as fallback
    }
  }

  /**
   * Build resolved context for a document (simplified version)
   * @param {Object} document - Document with @context
   * @param {string} baseUrl - Base URL for resolving context
   * @returns {Object} - Resolved context
   */
  async buildResolvedContext(document, baseUrl) {
    try {
      // Use existing context resolution if available
      if (this.documentLoader.collectAndLoadContexts) {
        return await this.documentLoader.collectAndLoadContexts(document['@context'], baseUrl);
      }
      
      // Fallback: return the context as-is
      return document['@context'] || {};
    } catch (error) {
      console.warn(`⚠️ Context resolution failed for ${baseUrl}:`, error.message);
      return {};
    }
  }

  /**
   * Extract main entity manually from document
   * @param {Object} document - Raw document
   * @param {string} url - Document URL
   * @returns {Object} - Extracted main entity
   */
  extractMainEntityManually(document, url) {
    // If document is an array, find entity with matching @id
    if (Array.isArray(document)) {
      const entity = document.find(item => item && item['@id'] === url);
      return entity || document[0] || {};
    }

    // If document has @graph, look for main entity there
    if (document['@graph'] && Array.isArray(document['@graph'])) {
      const entity = document['@graph'].find(item => item && item['@id'] === url);
      return entity || document['@graph'][0] || document;
    }

    // Return the document itself
    return document;
  }

  /**
   * Check if an object is an @id-only reference object
   * @param {*} obj - Object to check
   * @returns {boolean} - True if it's an @id-only object
   */
  isIdOnlyObject(obj) {
    return (
      typeof obj === 'object' &&
      obj !== null &&
      !Array.isArray(obj) &&
      obj.hasOwnProperty('@id') &&
      typeof obj['@id'] === 'string' &&
      Object.keys(obj).length <= 2 // Allow for @id and possibly @type
    );
  }

  /**
   * Check if a property is a linked property based on context
   * @param {string} key - Property key
   * @returns {boolean} - True if it's a linked property
   */
  isLinkedProperty(key) {
    return this.referenceManager.isLinkedProperty(key);
  }

  /**
   * Resolve a URL using reference manager
   * @param {string} value - Value to resolve
   * @param {string} key - Property key (for context)
   * @param {string} baseUrl - Base URL
   * @returns {string|null} - Resolved URL or null if not resolvable
   */
  resolveUrl(value, key, baseUrl) {
    try {
      const resolved = this.referenceManager.expandReference(value, key);
      
      // If still not a full URL, try resolving against base URL
      if (resolved && !resolved.startsWith('http') && baseUrl) {
        return Utils.resolveUrl(resolved, baseUrl);
      }
      
      return resolved && resolved.startsWith('http') ? resolved : null;
    } catch (error) {
      console.warn(`⚠️ Error resolving URL '${value}':`, error.message);
      return null;
    }
  }

  /**
   * Check if a URL should be resolved (not already resolved, valid HTTP URL, etc.)
   * @param {string} url - URL to check
   * @returns {boolean} - True if URL should be resolved
   */
  shouldResolveUrl(url) {
    return (
      url &&
      typeof url === 'string' &&
      url.startsWith('http') &&
      !this.resolvedContent.has(url) // Don't re-resolve already cached content
    );
  }

  /**
   * Set maximum depth for resolution
   * @param {number} depth - Maximum depth
   */
  setMaxDepth(depth) {
    this.maxDepth = Math.max(1, Math.min(depth, 10)); // Clamp between 1 and 10
    console.log(`🔧 Set maximum resolution depth to: ${this.maxDepth}`);
  }

  /**
   * Clear the resolution cache
   */
  clearCache() {
    this.resolvedContent.clear();
    this.visitedUrls.clear();
    console.log(`🧹 Cleared link content resolution cache`);
  }

  /**
   * Get cache statistics
   * @returns {Object} - Cache statistics
   */
  getCacheStats() {
    return {
      resolvedCount: this.resolvedContent.size,
      resolvedUrls: Array.from(this.resolvedContent.keys()),
      maxDepth: this.maxDepth
    };
  }

  /**
   * Manually add resolved content to cache
   * @param {string} url - URL
   * @param {Object} content - Resolved content
   */
  cacheResolvedContent(url, content) {
    this.resolvedContent.set(url, content);
    console.log(`📋 Manually cached content for: ${url}`);
  }
}
