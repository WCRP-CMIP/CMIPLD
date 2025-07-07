/**
 * Enhanced Link Substitution Manager
 * Downloads linked content, substitutes it in place, and highlights broken links
 * UPDATED: Only substitute URLs linked to 'id' or '@id' fields, add progress tracking
 */

export class EnhancedLinkSubstitutionManager {
  constructor(documentLoader, jsonldProcessor, referenceManager, jsonRenderer) {
    this.documentLoader = documentLoader;
    this.jsonldProcessor = jsonldProcessor;
    this.referenceManager = referenceManager;
    this.jsonRenderer = jsonRenderer;
    
    // Track link status
    this.linkStatus = new Map(); // url -> { status: 'loading'|'success'|'error', data?: any, error?: string }
    this.substitutionCache = new Map();
    
    // Configuration - removed depth, simplified
    this.enabled = true;
    this.skipPatterns = ['#', 'javascript:', 'mailto:'];
    
    // Processing statistics and progress tracking
    this.processStats = {
      totalSubstitutions: 0,
      successfulSubstitutions: 0,
      failedSubstitutions: 0
    };
    
    // Progress tracking
    this.progressCallback = null;
    this.totalLinksToProcess = 0;
    this.processedLinks = 0;
  }

  /**
   * Enable/disable link substitution
   */
  setEnabled(enabled) {
    this.enabled = enabled;
    console.log(`🔧 Link substitution ${enabled ? 'enabled' : 'disabled'}`);
  }

  /**
   * Set progress callback for UI updates
   */
  setProgressCallback(callback) {
    this.progressCallback = callback;
  }

  /**
   * Report progress to the UI
   */
  reportProgress(message = null) {
    if (this.progressCallback) {
      this.progressCallback({
        current: this.processedLinks,
        total: this.totalLinksToProcess,
        message: message
      });
    }
  }

  /**
   * Count the total number of links that will be processed for progress tracking
   */
  countLinksToProcess(obj, path = []) {
    if (!obj || typeof obj !== 'object') {
      return 0;
    }

    let count = 0;

    try {
      if (Array.isArray(obj)) {
        for (let i = 0; i < obj.length; i++) {
          const item = obj[i];
          const newPath = [...path, i];
          
          if (this.isLinkToSubstitute(item, null, path)) {
            count++;
          } else if (typeof item === 'object') {
            count += this.countLinksToProcess(item, newPath);
          }
        }
      } else {
        for (const [key, value] of Object.entries(obj)) {
          const newPath = [...path, key];
          
          if (this.isLinkToSubstitute(value, key, path)) {
            count++;
          } else if (typeof value === 'object') {
            count += this.countLinksToProcess(value, newPath);
          }
        }
      }
    } catch (error) {
      console.warn(`⚠️ Error counting links:`, error.message);
    }

    return count;
  }

  /**
   * Main method: Process document and substitute all linked entries
   * UPDATED: Added progress tracking
   */
  async processDocumentWithSubstitution(document, options = {}) {
    const {
      skipBrokenLinks = true,
      showProgress = true
    } = options;
    
    if (!this.enabled) {
      console.log('🚫 Link substitution disabled, skipping processing');
      return document;
    }

    console.log('🔄 === STARTING ENHANCED LINK SUBSTITUTION ===');
    console.log('📋 Reference manager available:', !!this.referenceManager);
    console.log('📋 Reference manager link properties:', this.referenceManager?.linkProperties?.size || 0);
    console.log('📋 Document sample:', document);
    
    try {
      // Deep clone to avoid mutating original
      const processedDocument = JSON.parse(JSON.stringify(document));
      
      // Reset processing statistics and progress
      this.processStats = {
        totalSubstitutions: 0,
        successfulSubstitutions: 0,
        failedSubstitutions: 0
      };
      this.processedLinks = 0;
      
      // First pass: count links to process for progress tracking
      this.totalLinksToProcess = this.countLinksToProcess(processedDocument);
      console.log(`📊 Found ${this.totalLinksToProcess} links to process`);
      
      // Report initial progress
      this.reportProgress('Analyzing document structure...');
      
      // Find and process all linked entries
      const result = await this.processLinkedEntries(processedDocument, []);
      
      console.log(`✅ Enhanced link substitution completed. Success: ${this.processStats.successfulSubstitutions}, Failed: ${this.processStats.failedSubstitutions}`);
      
      return result;
      
    } catch (error) {
      console.error('❌ Enhanced link substitution failed:', error);
      // Return original document instead of throwing to prevent workflow failure
      console.warn('⚠️ Returning original document due to substitution error');
      return document;
    }
  }

  /**
   * Recursively process linked entries in the document
   * UPDATED: Removed depth tracking, simplified logic
   */
  async processLinkedEntries(obj, path = []) {
    if (!obj || typeof obj !== 'object') {
      return obj;
    }

    try {
      if (Array.isArray(obj)) {
        // Process array items
        const processedArray = [];
        for (let i = 0; i < obj.length; i++) {
          const item = obj[i];
          const newPath = [...path, i];
          
          try {
            // Check if this array item should be substituted
            if (this.isLinkToSubstitute(item, null, path)) {
              console.log(`🔄 Substituting array item [${i}] in ${path.join(' > ')}:`, item);
              
              const substituted = await this.substituteLink(item, newPath);
              processedArray.push(substituted);
              
              console.log(`✅ Array item [${i}] substituted successfully`);
            } else if (typeof item === 'object') {
              // Recursively process non-substituted objects
              const processed = await this.processLinkedEntries(item, newPath);
              processedArray.push(processed);
            } else {
              processedArray.push(item);
            }
          } catch (itemError) {
            console.warn(`⚠️ Error processing array item at ${newPath.join(' > ')}:`, itemError.message);
            processedArray.push(item); // Keep original on error
          }
        }
        return processedArray;
      } else {
        // Process object properties
        const processedObject = {};
        
        for (const [key, value] of Object.entries(obj)) {
          const newPath = [...path, key];
          
          try {
            // Check if this property value should be substituted
            if (this.isLinkToSubstitute(value, key, path)) {
              console.log(`🔄 Substituting property '${key}' in ${path.join(' > ')}:`, value);
              
              const substituted = await this.substituteLink(value, newPath, key);
              processedObject[key] = substituted;
              
              console.log(`✅ Property '${key}' substituted successfully`);
            } else if (typeof value === 'object') {
              // Recursively process non-substituted objects
              const processed = await this.processLinkedEntries(value, newPath);
              processedObject[key] = processed;
            } else {
              processedObject[key] = value;
            }
          } catch (propError) {
            console.warn(`⚠️ Error processing property ${key} at ${newPath.join(' > ')}:`, propError.message);
            processedObject[key] = value; // Keep original on error
          }
        }
        
        return processedObject;
      }
    } catch (error) {
      console.warn(`⚠️ Error processing object:`, error.message);
      return obj; // Return original on error
    }
  }

  /**
   * Check if a value should be substituted with linked content
   * UPDATED: Use reference manager to detect linked properties from context
   */
  isLinkToSubstitute(value, key = null, parentPath = []) {
    try {
      // Debug logging
      const pathStr = parentPath.length > 0 ? `[${parentPath.join(' > ')}]` : '[ROOT]';
      
      // Never substitute the main document's @id (at root level)
      if (key === '@id' && parentPath.length === 0) {
        console.log(`🚫 SKIPPING main document @id at ${pathStr} > ${key}`);
        return false;
      }
      
      // CASE 1: Always substitute @id fields (except main document)
      if (key === '@id' || key === 'id') {
        return this.shouldSubstituteIdField(value, key, pathStr);
      }
      
      // CASE 2: Check if this is a linked property according to the context
      // UPDATED: Only use JSON-LD context-based detection, no hardcoded fallbacks
      if (this.referenceManager && this.referenceManager.isLinkedProperty && this.referenceManager.isLinkedProperty(key)) {
        console.log(`🔗 '${key}' is a linked property according to JSON-LD context`);
        return this.shouldSubstituteLinkedProperty(value, key, pathStr);
      }
      
      // Debug: Log what we're skipping
      if (key && typeof value === 'string' && value.length > 0) {
        console.log(`🚫 SKIPPING field '${key}' with value '${value}' (not identified as linked)`);
      }

      return false;
      
    } catch (error) {
      console.warn(`⚠️ Error in isLinkToSubstitute:`, error.message);
      return false; // Safe default
    }
  }

  /**
   * Check if an @id or id field should be substituted
   */
  shouldSubstituteIdField(value, key, pathStr) {
    // CASE 1: @id object - SHOULD substitute (common in CMIP data)
    if (typeof value === 'object' && value !== null && !Array.isArray(value) &&
        Object.keys(value).length === 1 && value['@id'] && typeof value['@id'] === 'string') {
      
      const idValue = value['@id'];
      
      // SKIP if ID ends with "none" (ignoring path and prefix)
      if (this.shouldSkipNoneId(idValue)) {
        console.log(`🚫 SKIPPING @id with "none": ${idValue}`);
        return false;
      }
      
      const isValidOrExpandable = this.isValidUrl(idValue) || this.isExpandablePrefixedId(idValue);
      
      if (isValidOrExpandable) {
        console.log(`✅ WILL SUBSTITUTE @id object at ${pathStr}: ${idValue}`);
        return true;
      }
    }
    
    // CASE 2: String values in id/@id fields - SHOULD substitute
    if (typeof value === 'string') {
      // SKIP if ID ends with "none" (ignoring path and prefix)
      if (this.shouldSkipNoneId(value)) {
        console.log(`🚫 SKIPPING id/@id reference with "none": ${value}`);
        return false;
      }
      
      const isValidUrl = this.isValidUrl(value);
      const isPrefixedId = this.isExpandablePrefixedId(value);
      
      if (isValidUrl || isPrefixedId) {
        console.log(`✅ WILL SUBSTITUTE id/@id reference at ${pathStr} > ${key}: ${value} (URL: ${isValidUrl}, Prefixed: ${isPrefixedId})`);
        return true;
      } else {
        console.log(`🚫 SKIPPING id/@id reference at ${pathStr} > ${key}: ${value} (not valid URL or expandable prefix)`);
      }
    }
    
    return false;
  }

  /**
   * Check if a linked property should be substituted
   */
  shouldSubstituteLinkedProperty(value, key, pathStr) {
    // Handle string values
    if (typeof value === 'string') {
      // SKIP if value ends with "none" (ignoring path and prefix)
      if (this.shouldSkipNoneId(value)) {
        console.log(`🚫 SKIPPING linked property with "none": ${key}=${value}`);
        return false;
      }
      
      const isValidUrl = this.isValidUrl(value);
      const isPrefixedId = this.isExpandablePrefixedId(value);
      
      if (isValidUrl || isPrefixedId) {
        console.log(`✅ WILL SUBSTITUTE linked property at ${pathStr} > ${key}: ${value} (URL: ${isValidUrl}, Prefixed: ${isPrefixedId})`);
        return true;
      } else {
        console.log(`🚫 SKIPPING linked property at ${pathStr} > ${key}: ${value} (not valid URL or expandable prefix)`);
      }
    }
    
    // Handle @id objects in linked properties
    if (typeof value === 'object' && value !== null && !Array.isArray(value) &&
        Object.keys(value).length === 1 && value['@id'] && typeof value['@id'] === 'string') {
      
      const idValue = value['@id'];
      
      // SKIP if ID ends with "none"
      if (this.shouldSkipNoneId(idValue)) {
        console.log(`🚫 SKIPPING linked property @id with "none": ${key}=${idValue}`);
        return false;
      }
      
      const isValidOrExpandable = this.isValidUrl(idValue) || this.isExpandablePrefixedId(idValue);
      
      if (isValidOrExpandable) {
        console.log(`✅ WILL SUBSTITUTE linked property @id object at ${pathStr} > ${key}: ${idValue}`);
        return true;
      }
    }
    
    return false;
  }

  /**
   * Check if an ID should be skipped because it ends with "none"
   * Ignores path and prefix, just checks the final part
   */
  shouldSkipNoneId(idValue) {
    if (!idValue || typeof idValue !== 'string') {
      return false;
    }
    
    // Extract the final part after the last slash or colon
    const lastPart = idValue.split(/[\/:]/).pop().toLowerCase();
    
    return lastPart === 'none';
  }

  /**
   * Check if a string is a prefixed ID that can be expanded (for compact mode)
   */
  isExpandablePrefixedId(value) {
    if (!value || typeof value !== 'string') return false;
    
    // Must contain a colon to be prefixed
    if (!value.includes(':')) return false;
    
    // Skip certain protocols that shouldn't be treated as prefixed IDs
    if (value.startsWith('http:') || value.startsWith('https:') || value.startsWith('ftp:') || value.startsWith('mailto:')) {
      return false;
    }
    
    // Try to expand it using the reference manager
    if (this.referenceManager?.expandReference) {
      const expanded = this.referenceManager.expandReference(value);
      return expanded && expanded !== value && this.isValidUrl(expanded);
    }
    
    return false;
  }

  /**
   * Check if URL is valid and should be processed
   */
  isValidUrl(url) {
    if (!url || typeof url !== 'string') return false;
    
    // Skip certain patterns
    if (this.skipPatterns.some(pattern => url.includes(pattern))) return false;
    
    // Must be HTTP/HTTPS
    return url.startsWith('http://') || url.startsWith('https://');
  }

  /**
   * Substitute a link with its downloaded content
   * UPDATED: Added progress reporting
   */
  async substituteLink(linkValue, path, key = null) {
    let url;
    let originalStructure = linkValue;

    // Extract URL from different structures
    if (typeof linkValue === 'object' && linkValue['@id']) {
      url = linkValue['@id'];
    } else if (typeof linkValue === 'string') {
      url = linkValue;
    } else {
      return linkValue; // Can't process
    }

    // Resolve URL if needed
    let resolvedUrl = url;
    if (this.referenceManager?.expandReference) {
      try {
        const expanded = this.referenceManager.expandReference(url, key);
        if (expanded && expanded !== url && this.isValidUrl(expanded)) {
          resolvedUrl = expanded;
        }
      } catch (expansionError) {
        console.warn(`⚠️ URL expansion failed for ${url}:`, expansionError.message);
      }
    }
    
    // If we still don't have a valid URL after expansion, skip substitution
    if (!this.isValidUrl(resolvedUrl)) {
      console.log(`🚫 SKIPPING substitution - not a valid URL after expansion: ${url} -> ${resolvedUrl}`);
      this.processedLinks++;
      this.reportProgress();
      return linkValue;
    }
    
    console.log(`🔗 SUBSTITUTING link in path [${path.join(' > ')}]: ${url} -> ${resolvedUrl}`);

    // Track substitution attempt
    this.processStats.totalSubstitutions++;
    
    // Report progress
    this.reportProgress(`Processing: ${resolvedUrl}`);

    // Check if already processed
    if (this.linkStatus.has(resolvedUrl)) {
      const status = this.linkStatus.get(resolvedUrl);
      console.log(`📋 Using cached status for ${resolvedUrl}: ${status.status}`);
      this.processedLinks++;
      this.reportProgress();
      return this.createSubstitutionResult(originalStructure, url, resolvedUrl, status);
    }

    // Mark as loading
    this.linkStatus.set(resolvedUrl, { status: 'loading' });

    try {
      // Download content
      const content = await this.downloadLinkContent(resolvedUrl);
      
      if (content) {
        // Process the downloaded content recursively
        let processedContent = content;
        processedContent = await this.processLinkedEntries(content, [...path, '@substituted']);

        // Store success
        const successStatus = { 
          status: 'success', 
          data: processedContent,
          timestamp: Date.now(),
          originalUrl: url,
          resolvedUrl: resolvedUrl
        };
        this.linkStatus.set(resolvedUrl, successStatus);
        
        this.processStats.successfulSubstitutions++;
        this.processedLinks++;
        console.log(`✅ Successfully substituted: ${resolvedUrl}`);
        this.reportProgress();

        return this.createSubstitutionResult(originalStructure, url, resolvedUrl, successStatus);
        
      } else {
        throw new Error('No content received');
      }

    } catch (error) {
      console.warn(`⚠️ Failed to substitute link ${resolvedUrl}:`, error.message);
      
      // Store error
      const errorStatus = { 
        status: 'error', 
        error: error.message,
        timestamp: Date.now(),
        originalUrl: url,
        resolvedUrl: resolvedUrl
      };
      this.linkStatus.set(resolvedUrl, errorStatus);
      
      this.processStats.failedSubstitutions++;
      this.processedLinks++;
      this.reportProgress();

      return this.createSubstitutionResult(originalStructure, url, resolvedUrl, errorStatus);
    }
  }

  /**
   * Download and process link content
   */
  async downloadLinkContent(url) {
    // Check cache first
    if (this.substitutionCache.has(url)) {
      console.log(`📋 Using cached content for: ${url}`);
      return this.substitutionCache.get(url);
    }

    try {
      console.log(`📥 Downloading link content: ${url}`);
      const rawContent = await this.documentLoader.fetchDocument(url);
      
      if (!rawContent) {
        throw new Error('Empty response');
      }

      // Process JSON-LD if applicable
      let processedContent = rawContent;
      if (this.isJsonLd(rawContent)) {
        try {
          console.log(`🔧 Processing JSON-LD content from: ${url}`);
          const expanded = await this.jsonldProcessor.expand(rawContent);
          
          // Extract main entity if it's an array
          if (Array.isArray(expanded) && expanded.length > 0) {
            // Find entity with matching @id or use first one
            const mainEntity = expanded.find(item => item['@id'] === url) || expanded[0];
            processedContent = mainEntity;
            console.log(`📄 Extracted main entity from ${url}:`, Object.keys(processedContent));
          } else if (expanded && typeof expanded === 'object') {
            processedContent = expanded;
          }
        } catch (jsonLdError) {
          console.warn(`⚠️ JSON-LD processing failed for ${url}, using raw content:`, jsonLdError.message);
          processedContent = rawContent;
        }
      }

      // Clean up the content - remove ALL @ fields
      const cleanedContent = this.cleanSubstitutedContent(processedContent);
      
      // Cache the result
      this.substitutionCache.set(url, cleanedContent);
      
      console.log(`✅ Successfully processed content from ${url}`);
      return cleanedContent;
      
    } catch (error) {
      console.error(`❌ Failed to download ${url}:`, error);
      throw error;
    }
  }

  /**
   * Clean substituted content by removing ALL @ fields
   * UPDATED: Remove ALL fields starting with '@'
   * FIXED: Also handle nested @id objects properly
   */
  cleanSubstitutedContent(content) {
    if (!content || typeof content !== 'object') {
      return content;
    }

    if (Array.isArray(content)) {
      // Process arrays recursively
      return content.map(item => this.cleanSubstitutedContent(item));
    }

    // Create a clean copy without ANY @ fields
    const cleaned = {};
    for (const [key, value] of Object.entries(content)) {
      // Skip ALL fields that start with '@'
      if (!key.startsWith('@')) {
        // Recursively clean nested objects
        if (typeof value === 'object' && value !== null) {
          // SPECIAL CASE: If this is a single @id object, extract just the string value
          if (!Array.isArray(value) && Object.keys(value).length === 1 && value['@id'] && typeof value['@id'] === 'string') {
            cleaned[key] = value['@id'];
            console.log(`🧽 Flattened @id object in '${key}': ${value['@id']}`);
          } else {
            cleaned[key] = this.cleanSubstitutedContent(value);
          }
        } else {
          cleaned[key] = value;
        }
      }
    }
    
    return cleaned;
  }

  /**
   * Create the substitution result based on status
   * UPDATED: Add green box for successful substitutions, red for failed
   * FIXED: Ensure @id is always a string in substituted results
   */
  createSubstitutionResult(originalStructure, originalUrl, resolvedUrl, status) {
    switch (status.status) {
      case 'success':
        // For successful substitution, wrap in green indicator box
        const successResult = {
          ...status.data, // Spread the actual content
          '@substituted': true,
          '@id': originalUrl, // ENSURE @id is the original URL string, not an object
          '@original-id': originalUrl,
          '@status': 'success',
          '@resolved-url': resolvedUrl !== originalUrl ? resolvedUrl : undefined
        };
        console.log(`📋 Created substituted content with green indicator for ${originalUrl}`);
        return successResult;

      case 'error':
        // For errors, wrap in red indicator box
        const errorResult = {
          '@broken': true,
          '@id': originalUrl,
          '@original-id': originalUrl,
          '@status': 'error',
          '@error': status.error,
          '@resolved-url': resolvedUrl !== originalUrl ? resolvedUrl : undefined,
          '@timestamp': status.timestamp
        };
        console.warn(`❌ Created failed substitution indicator for ${originalUrl}: ${status.error}`);
        return errorResult;

      case 'loading':
        // For loading state, return original structure
        return originalStructure;

      default:
        return originalStructure;
    }
  }

  /**
   * Check if content is JSON-LD
   */
  isJsonLd(content) {
    if (!content || typeof content !== 'object') return false;
    
    return !!(
      content['@context'] ||
      content['@id'] ||
      content['@type'] ||
      content['@graph'] ||
      (Array.isArray(content) && content.some(item => 
        item && typeof item === 'object' && (item['@context'] || item['@id'] || item['@type'])
      ))
    );
  }

  /**
   * Get statistics about link processing
   */
  getLinkStats() {
    const stats = {
      enabled: this.enabled,
      total: this.linkStatus.size,
      success: 0,
      error: 0,
      loading: 0,
      processStats: this.processStats,
      urls: {
        success: [],
        error: [],
        loading: []
      }
    };

    for (const [url, status] of this.linkStatus.entries()) {
      stats[status.status]++;
      stats.urls[status.status].push(url);
    }

    return stats;
  }

  /**
   * Clear all caches and reset state
   */
  clearAll() {
    this.linkStatus.clear();
    this.substitutionCache.clear();
    this.processStats = {
      totalSubstitutions: 0,
      successfulSubstitutions: 0,
      failedSubstitutions: 0
    };
    console.log('🧹 Link substitution caches and stats cleared');
  }

  /**
   * Get current configuration
   */
  getConfig() {
    return {
      enabled: this.enabled,
      cacheSize: this.substitutionCache.size,
      linkStatusSize: this.linkStatus.size,
      processStats: this.processStats
    };
  }
}
