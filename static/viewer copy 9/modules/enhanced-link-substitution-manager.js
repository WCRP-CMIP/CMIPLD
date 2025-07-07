/**
 * Enhanced Link Substitution Manager
 * Downloads linked content, substitutes it in place, and highlights broken links
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
    
    // Configuration
    this.maxDepth = 2;
    this.enabled = true;
    this.skipPatterns = ['#', 'javascript:', 'mailto:'];
  }

  /**
   * Main method: Process document and substitute all linked entries
   */
  async processDocumentWithSubstitution(document, options = {}) {
    const {
      maxDepth = 2,
      skipBrokenLinks = true,
      showProgress = true
    } = options;

    this.maxDepth = maxDepth;
    
    if (!this.enabled) {
      return document;
    }

    console.log('🔄 Starting enhanced link substitution...');
    
    try {
      // Deep clone to avoid mutating original
      const processedDocument = JSON.parse(JSON.stringify(document));
      
      // Find and process all linked entries with error handling
      await this.processLinkedEntries(processedDocument, 0);
      
      console.log('✅ Enhanced link substitution completed');
      return processedDocument;
      
    } catch (error) {
      console.error('❌ Enhanced link substitution failed:', error);
      // Return original document instead of throwing to prevent workflow failure
      console.warn('⚠️ Returning original document due to substitution error');
      return document;
    }
  }

  /**
   * Recursively process linked entries in the document
   */
  async processLinkedEntries(obj, depth = 0, path = []) {
    if (depth >= this.maxDepth || !obj || typeof obj !== 'object') {
      return obj;
    }

    try {
      if (Array.isArray(obj)) {
        // Process array items - important for linked field arrays
        for (let i = 0; i < obj.length; i++) {
          const item = obj[i];
          const newPath = [...path, i];
          
          try {
            // Check if this array item should be substituted
            if (this.isLinkToSubstitute(item, null, path)) {
              console.log(`🔄 Substituting array item [${i}] in ${path.join(' > ')}:`, item);
              const substituted = await this.substituteLink(item, depth + 1, newPath);
              obj[i] = substituted;
              console.log(`✅ Array item [${i}] substituted successfully`);
            } else if (typeof item === 'object') {
              await this.processLinkedEntries(item, depth, newPath);
            }
          } catch (itemError) {
            console.warn(`⚠️ Error processing array item at ${newPath.join(' > ')}:`, itemError.message);
            // Continue with next item
          }
        }
      } else {
        // Process object properties
        for (const [key, value] of Object.entries(obj)) {
          const newPath = [...path, key];
          
          try {
            // Check if this property value should be substituted
            if (this.isLinkToSubstitute(value, key, path)) {
              console.log(`🔄 Substituting property '${key}' in ${path.join(' > ')}:`, value);
              const substituted = await this.substituteLink(value, depth + 1, newPath, key);
              obj[key] = substituted;
              console.log(`✅ Property '${key}' substituted successfully`);
            } else if (typeof value === 'object') {
              // Before recursing, check if this object itself is a linked field with @id
              if (this.isKnownLinkedField(key) && value !== null && !Array.isArray(value) && value['@id']) {
                console.log(`🔎 Found linked field '${key}' with @id, will process @id within it`);
              }
              await this.processLinkedEntries(value, depth, newPath);
            }
          } catch (propError) {
            console.warn(`⚠️ Error processing property ${key} at ${newPath.join(' > ')}:`, propError.message);
            // Continue with next property
          }
        }
      }
    } catch (error) {
      console.warn(`⚠️ Error processing object at depth ${depth}:`, error.message);
    }

    return obj;
  }

  /**
   * Check if a value should be substituted with linked content
   * FIXED: Handle both full URLs and prefixed IDs in compact mode
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
      
      // CASE 1: @id object in an array - SHOULD substitute (common in CMIP data)
      if (typeof value === 'object' && value !== null && !Array.isArray(value) &&
          Object.keys(value).length === 1 && value['@id'] && typeof value['@id'] === 'string') {
        
        const idValue = value['@id'];
        const isValidOrExpandable = this.isValidUrl(idValue) || this.isExpandablePrefixedId(idValue);
        const inArray = parentPath.length > 0 && typeof parentPath[parentPath.length - 1] === 'number';
        
        if (isValidOrExpandable && (inArray || this.isCMIPLinkedField(parentPath))) {
          console.log(`✅ WILL SUBSTITUTE @id object in array/linked field at ${pathStr}: ${idValue}`);
          return true;
        }
      }
      
      // CASE 2: String values that are references - SHOULD substitute
      if (typeof value === 'string') {
        const isValidUrl = this.isValidUrl(value);
        const isPrefixedId = this.isExpandablePrefixedId(value);
        const isCMIPPattern = isValidUrl && this.isCMIPReferenceUrl(value);
        const isInCMIPField = this.isCMIPLinkedField(parentPath, key);
        
        if ((isValidUrl && (isCMIPPattern || isInCMIPField)) || (isPrefixedId && isInCMIPField)) {
          console.log(`✅ WILL SUBSTITUTE reference at ${pathStr} > ${key}: ${value} (URL: ${isValidUrl}, Prefixed: ${isPrefixedId})`);
          return true;
        }
      }
      
      // CASE 3: Any @id that's NOT at root and looks like a reference
      if (key === '@id' && parentPath.length > 0 && typeof value === 'string') {
        const isValidOrExpandable = this.isValidUrl(value) || this.isExpandablePrefixedId(value);
        
        if (isValidOrExpandable && !this.looksLikeObjectIdentifier(value, parentPath)) {
          console.log(`✅ WILL SUBSTITUTE expandable @id at ${pathStr}: ${value}`);
          return true;
        }
      }

      return false;
      
    } catch (error) {
      console.warn(`⚠️ Error in isLinkToSubstitute:`, error.message);
      return false; // Safe default
    }
  }

  /**
   * Check if a string is a prefixed ID that can be expanded (for compact mode)
   */
  isExpandablePrefixedId(value) {
    if (!value || typeof value !== 'string') return false;
    
    // Must contain a colon to be prefixed
    if (!value.includes(':')) return false;
    
    // Try to expand it using the reference manager
    if (this.referenceManager?.expandReference) {
      const expanded = this.referenceManager.expandReference(value);
      return expanded && expanded !== value && this.isValidUrl(expanded);
    }
    
    return false;
  }

  /**
   * Check if this @id appears to be a main object identifier
   * Main identifiers are typically at the root of objects, not in linked field contexts
   */
  isMainObjectIdentifier(parentPath) {
    if (parentPath.length === 0) return true; // Root level @id
    
    // Check if we're directly in a main object (not in a linked field)
    const immediateParent = parentPath[parentPath.length - 1];
    return !this.isKnownLinkedField(immediateParent);
  }

  /**
   * Check if the current path context indicates we're in a linked field
   */
  isInLinkedFieldContext(parentPath) {
    if (parentPath.length === 0) return false;
    
    // Check if any parent in the path is a known linked field
    // This includes direct parent and any ancestor in the path
    return parentPath.some(pathElement => 
      typeof pathElement === 'string' && this.isKnownLinkedField(pathElement)
    );
  }

  /**
   * Check if we're directly in a linked field (immediate parent is a linked field)
   */
  isDirectlyInLinkedField(parentPath) {
    if (parentPath.length === 0) return false;
    
    // Check if the immediate parent is a linked field
    const immediateParent = parentPath[parentPath.length - 1];
    return typeof immediateParent === 'string' && this.isKnownLinkedField(immediateParent);
  }

  /**
   * Check if the path or key indicates this is a CMIP linked field
   */
  isCMIPLinkedField(parentPath, key = null) {
    // Check if we're in a field that's commonly used for linking in CMIP data
    const cmipLinkedFields = [
      'activity', 'experiment', 'source', 'institution', 'grid', 'variant',
      'variable', 'member', 'table', 'realm', 'frequency', 'modeling_realm',
      'required_model_components', 'parent_experiment_id', 'parent_variant_label',
      'related', 'references', 'seeAlso', 'isVersionOf', 'isPartOf', 'derivedFrom',
      'parent-activity', 'parent-experiment', 'sub-experiment', 'model-realms'
    ];
    
    // Check if current key matches
    if (key && cmipLinkedFields.some(field => key.includes(field))) {
      return true;
    }
    
    // Check if any parent in the path matches
    return parentPath.some(pathElement => 
      typeof pathElement === 'string' && 
      cmipLinkedFields.some(field => pathElement.includes(field))
    );
  }

  /**
   * Check if a URL looks like a CMIP reference that should be substituted
   */
  isCMIPReferenceUrl(url) {
    const cmipPatterns = [
      'wcrp-cmip.github.io',
      'CMIP7-CVs',
      'WCRP-universe',
      'activity/',
      'experiment/',
      'source/',
      'institution/',
      '/CV/',
      'cmip.org'
    ];
    
    return cmipPatterns.some(pattern => url.includes(pattern));
  }

  /**
   * Check if a URL looks like an object identifier (shouldn't substitute)
   */
  looksLikeObjectIdentifier(url, parentPath) {
    // If we're at the immediate top level of an object, it's likely an identifier
    if (parentPath.length === 1 && typeof parentPath[0] === 'string') {
      return true;
    }
    
    // If the URL contains fragments that suggest it's an identifier
    const identifierPatterns = ['#', '/person/', '/organization/', '/entity/'];
    return identifierPatterns.some(pattern => url.includes(pattern));
  }

  /**
   * Check if a field is designated as a linked field that should have substitutions
   */
  isDesignatedLinkedField(key, parentPath) {
    return this.isKnownLinkedField(key) && !this.isMainObjectIdentifier(parentPath);
  }

  /**
   * Check if a property is a known linked field (not just any link property)
   * FIXED: More comprehensive list for CMIP data
   */
  isKnownLinkedField(key) {
    // Ensure key is a string before checking patterns
    if (typeof key !== 'string') {
      return false;
    }
    
    const linkedFields = [
      // Semantic Web / JSON-LD linking properties
      'seeAlso', 'sameAs', 'isDefinedBy', 'isVersionOf', 'hasVersion',
      'isPartOf', 'hasPart', 'isReferencedBy', 'references',
      'rdfs:seeAlso', 'owl:sameAs', 'dcterms:isVersionOf', 'dcterms:hasVersion',
      
      // CMIP-specific linked fields (expanded list)
      'activity', 'experiment', 'source', 'institution', 'grid', 'variant',
      'variable', 'member', 'table', 'realm', 'frequency', 'modeling_realm',
      'required_model_components', 'parent_experiment_id', 'parent_variant_label',
      'activity_id', 'experiment_id', 'source_id', 'institution_id',
      'member_id', 'table_id', 'grid_label', 'variant_label',
      'variable_id', 'realm_id', 'frequency_id',
      'parent-activity', 'parent-experiment', 'sub-experiment', 'model-realms',
      
      // Generic linked collections
      'relatedDataset', 'relatedVariable', 'relatedExperiment', 'relatedModel',
      'parentDataset', 'childDataset', 'derivedFrom', 'generates',
      'dependsOn', 'supports', 'implements', 'extends',
      'related', 'linked', 'associated', 'connected', 'references',
      'dependencies', 'relations', 'links', 'connections'
    ];
    
    return linkedFields.includes(key) || 
           key.endsWith('_id') || 
           key.endsWith('Id') ||
           key.includes('related') ||
           key.includes('linked') ||
           key.includes('ref') ||
           key.includes('Reference') ||
           key.startsWith('see') ||
           key.startsWith('same');
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
   * FIXED: Handle both full URLs and prefixed IDs
   */
  async substituteLink(linkValue, depth, path, key = null) {
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

    // Resolve URL if needed - FIXED: Better context resolution
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
      return linkValue;
    }
    
    console.log(`🔗 SUBSTITUTING link in path [${path.join(' > ')}]: ${url} -> ${resolvedUrl}`);

    // Check if already processed
    if (this.linkStatus.has(resolvedUrl)) {
      const status = this.linkStatus.get(resolvedUrl);
      console.log(`📋 Using cached status for ${resolvedUrl}: ${status.status}`);
      return this.createSubstitutionResult(originalStructure, url, resolvedUrl, status);
    }

    // Mark as loading
    this.linkStatus.set(resolvedUrl, { status: 'loading' });

    try {
      // Download content
      const content = await this.downloadLinkContent(resolvedUrl);
      
      if (content) {
        // Process the downloaded content recursively if within depth limit
        let processedContent = content;
        if (depth < this.maxDepth) {
          processedContent = await this.processLinkedEntries(content, depth);
        }

        // Store success
        const successStatus = { 
          status: 'success', 
          data: processedContent,
          timestamp: Date.now(),
          originalUrl: url,
          resolvedUrl: resolvedUrl
        };
        this.linkStatus.set(resolvedUrl, successStatus);
        console.log(`✅ Successfully substituted: ${resolvedUrl}`);

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

      // Clean up the content - remove metadata fields that might conflict
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
   * Clean substituted content by removing potential conflicting metadata
   */
  cleanSubstitutedContent(content) {
    if (!content || typeof content !== 'object') {
      return content;
    }

    // Create a clean copy without our metadata fields
    const metadataFields = [
      '@resolved', '@status', '@timestamp', '@substituted', 
      '@broken', '@loading', '@error', '@resolvedUrl'
    ];
    
    const cleaned = {};
    for (const [key, value] of Object.entries(content)) {
      if (!metadataFields.includes(key)) {
        cleaned[key] = value;
      }
    }
    
    return cleaned;
  }

  /**
   * Create the substitution result based on status
   */
  createSubstitutionResult(originalStructure, originalUrl, resolvedUrl, status) {
    const baseResult = {
      '@id': originalUrl,
      '@resolved': true,
      '@status': status.status,
      '@timestamp': status.timestamp || Date.now()
    };

    if (resolvedUrl !== originalUrl) {
      baseResult['@resolvedUrl'] = resolvedUrl;
    }

    switch (status.status) {
      case 'success':
        // For successful substitution, merge the content directly
        // This replaces the original {"@id": "url"} with the full expanded content
        const substitutedContent = {
          ...status.data, // Spread the actual content first
          ...baseResult,  // Add metadata
          '@substituted': true
        };
        
        // Ensure the original @id is preserved in the substituted content
        if (!substitutedContent['@id']) {
          substitutedContent['@id'] = originalUrl;
        }
        
        console.log(`📋 Created substituted content for ${originalUrl}:`, Object.keys(substitutedContent));
        return substitutedContent;

      case 'error':
        return {
          ...baseResult,
          '@error': status.error,
          '@broken': true,
          // Keep original structure visible for broken links
          ...(typeof originalStructure === 'object' ? originalStructure : {})
        };

      case 'loading':
        return {
          ...baseResult,
          '@loading': true,
          // Keep original structure visible while loading
          ...(typeof originalStructure === 'object' ? originalStructure : {})
        };

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
      total: this.linkStatus.size,
      success: 0,
      error: 0,
      loading: 0,
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
    console.log('🧹 Link substitution caches cleared');
  }

  /**
   * Enable/disable link substitution
   */
  setEnabled(enabled) {
    this.enabled = enabled;
  }

  /**
   * Set maximum substitution depth
   */
  setMaxDepth(depth) {
    this.maxDepth = Math.max(1, Math.min(5, depth));
  }
}
