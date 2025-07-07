// JSON rendering and display
import { Utils } from './utils.js';

export class JSONRenderer {
  constructor() {
    this.hiddenFields = new Set();
    this.referenceManager = null;
    this.originalContext = null;
    this.documentLoader = null;
    this.inlineLoadCallback = null;
    this.currentDepth = 0;
    this.maxDepth = 3;
  }

  // Set reference manager for linked field detection
  setReferenceManager(referenceManager) {
    this.referenceManager = referenceManager;
  }
  
  // Set original context for base URL extraction
  setOriginalContext(context) {
    this.originalContext = context;
  }

  // Set document loader for inline loading functionality
  setDocumentLoader(documentLoader) {
    this.documentLoader = documentLoader;
  }

  // Set inline load callback for expandable content
  setInlineLoadCallback(callback) {
    this.inlineLoadCallback = callback;
  }

  // Set current depth for inline loading
  setCurrentDepth(depth) {
    this.currentDepth = depth || 0;
  }

  // Set maximum depth for inline loading
  setMaxDepth(depth) {
    this.maxDepth = depth || 3;
  }

  // Render JSON with syntax highlighting
  renderJson(data, container, level = 0) {
    container.innerHTML = '';
    const jsonElement = this.createJsonElement(data, level);
    container.appendChild(jsonElement);
  }

  // Create syntax-highlighted JSON element
  createJsonElement(data, level = 0, key = null) {
    const container = document.createElement('div');
    container.style.marginLeft = `${level * 20}px`;
    
    if (data === null) {
      container.innerHTML = '<span class="json-null">null</span>';
    } else if (typeof data === 'boolean') {
      container.innerHTML = `<span class="json-boolean">${data}</span>`;
    } else if (typeof data === 'number') {
      container.innerHTML = `<span class="json-number">${data}</span>`;
    } else if (typeof data === 'string') {
      // Check if string is a URL and make it clickable
      if (this.isUrl(data)) {
        const link = document.createElement('a');
        link.href = this.resolveUrl(data, key);
        link.target = '_blank';
        link.className = 'json-string json-url';
        link.textContent = `"${data}"`;
        container.appendChild(link);
      } else {
        container.innerHTML = `<span class="json-string">"${Utils.escapeHtml(data)}"</span>`;
      }
    } else if (Array.isArray(data)) {
      this.createArrayElement(data, container, level);
    } else if (typeof data === 'object') {
      // FIXED: Special handling for expanded JSON-LD objects with only @id
      // This is where the [object Object] issue was occurring
      if (Object.keys(data).length === 1 && data['@id']) {
        // Render as a clickable link with proper string handling
        const idValue = data['@id'];
        if (typeof idValue === 'string') {
          if (this.isUrl(idValue)) {
            const link = document.createElement('a');
            link.href = this.resolveUrl(idValue, '@id');
            link.target = '_blank';
            link.className = 'json-string json-url';
            link.textContent = `{"@id": "${idValue}"}`;
            container.appendChild(link);
          } else {
            container.innerHTML = `<span class="json-object-inline">{"@id": "${Utils.escapeHtml(idValue)}"}</span>`;
          }
        } else {
          // Check if this is resolved/substituted content (has meaningful properties)
          if (typeof idValue === 'object' && idValue !== null) {
            const keys = Object.keys(idValue);
            const hasSubstantialContent = keys.length > 1 && 
                                        (idValue.id || idValue.name || idValue.title || 
                                         idValue.description || idValue.url || idValue.label);
            
            if (hasSubstantialContent) {
              // This is resolved content, not an error - render it as successfully substituted content
              console.log('✅ @id contains resolved content with', keys.length, 'properties:', idValue);
              
              // Create a substituted content display (similar to createSubstitutedLinkElement)
              const resolvedContainer = document.createElement('div');
              resolvedContainer.className = 'json-resolved-id-container';
              resolvedContainer.style.borderLeft = '4px solid #10b981';
              resolvedContainer.style.paddingLeft = '12px';
              resolvedContainer.style.backgroundColor = '#f0fdf4';
              resolvedContainer.style.borderRadius = '6px';
              resolvedContainer.style.margin = '8px 0';
              resolvedContainer.style.padding = '12px';
              
              // Success indicator with expand/collapse functionality
              const header = document.createElement('div');
              header.className = 'json-resolved-header';
              header.style.cursor = 'pointer';
              header.style.display = 'flex';
              header.style.alignItems = 'center';
              header.style.marginBottom = '8px';
              
              const toggleIcon = document.createElement('span');
              toggleIcon.className = 'json-toggle-icon';
              toggleIcon.textContent = '▼';
              toggleIcon.style.marginRight = '8px';
              toggleIcon.style.color = '#059669';
              toggleIcon.style.fontWeight = 'bold';
              toggleIcon.style.transition = 'transform 0.2s ease';
              
              const successIndicator = document.createElement('span');
              successIndicator.className = 'json-success-indicator';
              successIndicator.style.color = '#059669';
              successIndicator.style.fontWeight = 'bold';
              successIndicator.style.fontSize = '0.9em';
              successIndicator.style.flexGrow = '1';
              successIndicator.textContent = '✅ RESOLVED @id: ' + (idValue.id || idValue.name || idValue.title || 'Content');
              
              header.appendChild(toggleIcon);
              header.appendChild(successIndicator);
              
              // Content container (collapsible)
              const contentContainer = document.createElement('div');
              contentContainer.className = 'json-resolved-content';
              contentContainer.style.borderTop = '1px solid #d1fae5';
              contentContainer.style.paddingTop = '8px';
              contentContainer.style.marginTop = '8px';
              contentContainer.style.maxHeight = '400px';
              contentContainer.style.overflowY = 'auto';
              
              // Render the resolved content
              const contentElement = this.createJsonElement(idValue, level + 1);
              contentContainer.appendChild(contentElement);
              
              // Add expand/collapse functionality
              let isExpanded = true;
              const toggleContent = () => {
                if (isExpanded) {
                  contentContainer.style.display = 'none';
                  toggleIcon.textContent = '▶';
                  isExpanded = false;
                } else {
                  contentContainer.style.display = 'block';
                  toggleIcon.textContent = '▼';
                  isExpanded = true;
                }
              };
              
              header.addEventListener('click', toggleContent);
              
              resolvedContainer.appendChild(header);
              resolvedContainer.appendChild(contentContainer);
              container.appendChild(resolvedContainer);
              
              return container;
            }
          }
          
          // If we get here, it's actually an invalid @id (not resolved content)
          console.warn('Invalid @id value (not a string and no substantial content):', idValue);
          
          // Create an expandable error display showing the actual invalid content
          const errorContainer = document.createElement('div');
          errorContainer.className = 'json-invalid-id-container';
          
          const errorHeader = document.createElement('div');
          errorHeader.className = 'json-error-header';
          errorHeader.style.color = '#dc2626';
          errorHeader.style.fontWeight = 'bold';
          errorHeader.style.cursor = 'pointer';
          errorHeader.style.padding = '4px 8px';
          errorHeader.style.backgroundColor = '#fef2f2';
          errorHeader.style.border = '1px solid #fecaca';
          errorHeader.style.borderRadius = '4px';
          errorHeader.style.marginBottom = '4px';
          
          const toggleIcon = document.createElement('span');
          toggleIcon.textContent = '▼ ';
          toggleIcon.style.marginRight = '4px';
          
          const errorText = document.createElement('span');
          errorText.textContent = '❌ INVALID @id (should be string, got object)';
          
          errorHeader.appendChild(toggleIcon);
          errorHeader.appendChild(errorText);
          
          // Create collapsible content showing the actual invalid @id content
          const errorContent = document.createElement('div');
          errorContent.className = 'json-invalid-id-content';
          errorContent.style.padding = '8px';
          errorContent.style.backgroundColor = '#fee2e2';
          errorContent.style.border = '1px solid #fecaca';
          errorContent.style.borderRadius = '4px';
          errorContent.style.fontSize = '0.9em';
          
          // Render the actual invalid @id content
          const actualContent = this.createJsonElement(idValue, level + 1, '@id');
          errorContent.appendChild(actualContent);
          
          // Add expand/collapse functionality
          let isExpanded = true;
          const toggleContent = () => {
            if (isExpanded) {
              errorContent.style.display = 'none';
              toggleIcon.textContent = '▶ ';
              isExpanded = false;
            } else {
              errorContent.style.display = 'block';
              toggleIcon.textContent = '▼ ';
              isExpanded = true;
            }
          };
          
          errorHeader.addEventListener('click', toggleContent);
          
          errorContainer.appendChild(errorHeader);
          errorContainer.appendChild(errorContent);
          container.appendChild(errorContainer);
        }
      } else {
        this.createObjectElement(data, container, level);
      }
    }
    
    return container;
  }

  // Create key display with potential hyperlink
  createKeyDisplay(key, parentObj) {
    const keyText = `"${key}"`;
    
    // Check if the key itself is a URL or can be resolved to one
    if (this.isUrl(key)) {
      const link = document.createElement('a');
      link.href = this.resolveUrl(key, 'key');
      link.target = '_blank';
      link.className = 'json-key-link';
      link.textContent = keyText;
      return link;
    }
    
    // Check if we can build a URL from base + key
    const baseUrl = this.getBaseUrl();
    if (baseUrl && this.couldBeRelativeUrl(key)) {
      const fullUrl = this.resolveUrl(key, 'key');
      const link = document.createElement('a');
      link.href = fullUrl;
      link.target = '_blank';
      link.className = 'json-key-link';
      link.textContent = keyText;
      return link;
    }
    
    return document.createTextNode(keyText);
  }

  // Create value element with proper handling for URLs and context-aware resolution
  createValueElement(data, level, key) {
    // FIXED: Better handling of objects to prevent [object Object] display
    // Handle substituted/broken/loading links
    if (typeof data === 'object' && data !== null && data['@id']) {
      return this.createEnhancedLinkElement(data, level, key);
    }
    
    // Handle prefixed IDs in compact mode (e.g., "universal:activity/cmip")
    if (typeof data === 'string' && this.isPrefixedId(data) && this.isLinkedField(key)) {
      return this.createSubstitutableLinkElement(data, level, key, 'prefixed');
    }
    
    // Handle URLs in compact mode
    if (typeof data === 'string' && this.isUrl(data) && this.isLinkedField(key)) {
      return this.createSubstitutableLinkElement(data, level, key, 'url');
    }
    
    // Handle regular URLs (not in linked fields) - just make clickable
    if (typeof data === 'string' && this.isUrl(data)) {
      const container = document.createElement('span');
      const link = document.createElement('a');
      link.href = this.resolveUrl(data, key);
      link.target = '_blank';
      link.className = 'json-string json-url';
      link.textContent = `"${data}"`;
      container.appendChild(link);
      return container;
    }
    
    return this.createJsonElement(data, level, key);
  }

  /**
   * Create a substitutable link element with inline substitution functionality
   * @param {string} linkValue - The link value (prefixed ID or URL)
   * @param {number} level - Nesting level
   * @param {string} key - Property key
   * @param {string} type - Type of link ('prefixed' or 'url')
   */
  createSubstitutableLinkElement(linkValue, level, key, type = 'prefixed') {
    const container = document.createElement('div');
    container.className = 'json-substitutable-link-container';
    container.style.display = 'inline-block';
    container.style.position = 'relative';
    
    // Create the main link display
    const linkContainer = document.createElement('span');
    linkContainer.style.display = 'inline-block';
    
    const link = document.createElement('a');
    link.href = this.resolveUrl(linkValue, key);
    link.target = '_blank';
    link.className = `json-string json-url ${type === 'prefixed' ? 'json-prefixed-link' : ''}`;
    link.textContent = `"${linkValue}"`;
    link.title = type === 'prefixed' ? `Prefixed reference: ${linkValue}` : `URL: ${linkValue}`;
    
    linkContainer.appendChild(link);
    
    // Add substitution button
    const substituteBtn = document.createElement('button');
    substituteBtn.className = 'json-substitute-btn';
    substituteBtn.innerHTML = '⬇';
    substituteBtn.title = 'Substitute with actual content';
    substituteBtn.style.cssText = `
      margin-left: 4px;
      padding: 2px 6px;
      border: 1px solid #d1d5db;
      background: #f9fafb;
      border-radius: 3px;
      cursor: pointer;
      font-size: 0.8em;
      color: #374151;
      vertical-align: top;
      transition: all 0.2s ease;
    `;
    
    // Hover effects
    substituteBtn.addEventListener('mouseenter', () => {
      substituteBtn.style.backgroundColor = '#e5e7eb';
      substituteBtn.style.borderColor = '#9ca3af';
    });
    
    substituteBtn.addEventListener('mouseleave', () => {
      substituteBtn.style.backgroundColor = '#f9fafb';
      substituteBtn.style.borderColor = '#d1d5db';
    });
    
    // Add click handler for substitution
    substituteBtn.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      await this.performInlineSubstitution(linkValue, key, container, substituteBtn, level);
    });
    
    container.appendChild(linkContainer);
    container.appendChild(substituteBtn);
    
    return container;
  }

  /**
   * Perform inline substitution of a link
   * @param {string} linkValue - The link to substitute
   * @param {string} key - Property key
   * @param {HTMLElement} container - Container element
   * @param {HTMLElement} button - The substitute button
   * @param {number} level - Nesting level
   */
  async performInlineSubstitution(linkValue, key, container, button, level) {
    // Disable button and show loading state
    button.disabled = true;
    button.innerHTML = '⏳';
    button.style.cursor = 'not-allowed';
    button.title = 'Loading content...';
    
    try {
      // Resolve the URL if it's a prefixed reference
      let resolvedUrl = linkValue;
      if (this.referenceManager?.expandReference) {
        console.log(`🔄 Expanding reference: ${linkValue}`);
        const expandResult = this.referenceManager.expandReference(linkValue, key);
        
        // Handle both sync and async expansion
        if (expandResult && typeof expandResult.then === 'function') {
          // It's a Promise, await it
          resolvedUrl = await expandResult;
          console.log(`🔄 Async expansion completed: ${linkValue} -> ${resolvedUrl}`);
        } else {
          // It's a direct value
          resolvedUrl = expandResult || linkValue;
          console.log(`🔄 Sync expansion completed: ${linkValue} -> ${resolvedUrl}`);
        }
      }
      
      // Ensure we have a string URL
      if (typeof resolvedUrl !== 'string') {
        throw new Error(`Reference expansion returned non-string value: ${typeof resolvedUrl} - ${resolvedUrl}`);
      }
      
      if (!this.isValidHttpUrl(resolvedUrl)) {
        throw new Error(`Cannot resolve to valid HTTP URL: ${linkValue} -> ${resolvedUrl}`);
      }
      
      console.log(`🔄 Performing inline substitution: ${linkValue} -> ${resolvedUrl}`);
      
      // Download the content
      const content = await this.fetchLinkContent(resolvedUrl);
      
      if (!content) {
        throw new Error('No content received');
      }
      
      // Clean the content (remove @ fields)
      const cleanedContent = this.cleanSubstitutedContent(content);
      
      // Create the substituted display
      this.createInlineSubstitutedDisplay(container, linkValue, resolvedUrl, cleanedContent, level);
      
      console.log(`✅ Inline substitution successful: ${linkValue}`);
      
    } catch (error) {
      console.warn(`⚠️ Inline substitution failed for ${linkValue}:`, error.message);
      
      // Show error state
      this.createInlineErrorDisplay(container, linkValue, error.message);
    }
  }

  /**
   * Fetch content for inline substitution
   */
  async fetchLinkContent(url) {
    if (!this.documentLoader) {
      throw new Error('Document loader not available');
    }
    
    try {
      const rawContent = await this.documentLoader.fetchDocument(url);
      
      if (!rawContent) {
        throw new Error('Empty response');
      }
      
      // For JSON-LD content, try to extract the main entity
      if (this.isJsonLd(rawContent)) {
        // If it's an array, find the main entity or use the first one
        if (Array.isArray(rawContent)) {
          return rawContent.find(item => item['@id'] === url) || rawContent[0];
        }
      }
      
      return rawContent;
      
    } catch (error) {
      console.error(`Failed to fetch ${url}:`, error);
      throw error;
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
   * Clean substituted content by removing @ fields
   */
  cleanSubstitutedContent(content) {
    if (!content || typeof content !== 'object') {
      return content;
    }

    if (Array.isArray(content)) {
      return content.map(item => this.cleanSubstitutedContent(item));
    }

    const cleaned = {};
    for (const [key, value] of Object.entries(content)) {
      // Skip ALL fields that start with '@'
      if (!key.startsWith('@')) {
        // Recursively clean nested objects
        if (typeof value === 'object' && value !== null) {
          // Handle @id objects by extracting just the string value
          if (!Array.isArray(value) && Object.keys(value).length === 1 && 
              value['@id'] && typeof value['@id'] === 'string') {
            cleaned[key] = value['@id'];
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
   * Create inline substituted content display
   */
  createInlineSubstitutedDisplay(container, originalValue, resolvedUrl, content, level) {
    // Clear container
    container.innerHTML = '';
    container.className = 'json-inline-substituted-container';
    container.style.cssText = `
      border-left: 4px solid #10b981;
      padding-left: 12px;
      background-color: #f0fdf4;
      border-radius: 6px;
      margin: 8px 0;
      padding: 12px;
      display: block;
    `;
    
    // Header with original link info
    const header = document.createElement('div');
    header.className = 'json-inline-substituted-header';
    header.style.cssText = `
      display: flex;
      align-items: center;
      margin-bottom: 8px;
      cursor: pointer;
    `;
    
    const toggleIcon = document.createElement('span');
    toggleIcon.textContent = '▼';
    toggleIcon.style.cssText = `
      margin-right: 8px;
      color: #059669;
      font-weight: bold;
      transition: transform 0.2s ease;
    `;
    
    const successLabel = document.createElement('span');
    successLabel.style.cssText = `
      color: #059669;
      font-weight: bold;
      font-size: 0.9em;
      flex-grow: 1;
    `;
    successLabel.textContent = '✅ SUBSTITUTED: ';
    
    const originalLink = document.createElement('a');
    originalLink.href = resolvedUrl;
    originalLink.target = '_blank';
    originalLink.className = 'json-url';
    originalLink.textContent = originalValue;
    originalLink.style.cssText = `
      margin-left: 8px;
      font-size: 0.85em;
    `;
    
    successLabel.appendChild(originalLink);
    header.appendChild(toggleIcon);
    header.appendChild(successLabel);
    
    // Content container
    const contentContainer = document.createElement('div');
    contentContainer.className = 'json-inline-substituted-content';
    contentContainer.style.cssText = `
      border-top: 1px solid #d1fae5;
      padding-top: 8px;
      margin-top: 8px;
      max-height: 300px;
      overflow-y: auto;
    `;
    
    // Render the substituted content
    const contentElement = this.createJsonElement(content, level + 1);
    contentContainer.appendChild(contentElement);
    
    // Add expand/collapse functionality
    let isExpanded = true;
    const toggleContent = () => {
      if (isExpanded) {
        contentContainer.style.display = 'none';
        toggleIcon.textContent = '▶';
        isExpanded = false;
      } else {
        contentContainer.style.display = 'block';
        toggleIcon.textContent = '▼';
        isExpanded = true;
      }
    };
    
    header.addEventListener('click', toggleContent);
    
    container.appendChild(header);
    container.appendChild(contentContainer);
  }

  /**
   * Create inline error display
   */
  createInlineErrorDisplay(container, originalValue, errorMessage) {
    // Clear container and show error state
    container.innerHTML = '';
    container.className = 'json-inline-error-container';
    container.style.cssText = `
      border-left: 4px solid #dc2626;
      padding-left: 12px;
      background-color: #fef2f2;
      border-radius: 6px;
      margin: 8px 0;
      padding: 12px;
      display: block;
    `;
    
    const errorHeader = document.createElement('div');
    errorHeader.style.cssText = `
      color: #dc2626;
      font-weight: bold;
      font-size: 0.9em;
      margin-bottom: 4px;
    `;
    errorHeader.textContent = '❌ SUBSTITUTION FAILED: ' + originalValue;
    
    const errorDetails = document.createElement('div');
    errorDetails.style.cssText = `
      color: #991b1b;
      font-size: 0.8em;
      font-family: monospace;
    `;
    errorDetails.textContent = errorMessage;
    
    // Add retry button
    const retryBtn = document.createElement('button');
    retryBtn.textContent = '🔄 Retry';
    retryBtn.style.cssText = `
      margin-top: 8px;
      padding: 4px 8px;
      border: 1px solid #dc2626;
      background: #fef2f2;
      color: #dc2626;
      border-radius: 3px;
      cursor: pointer;
      font-size: 0.8em;
    `;
    
    retryBtn.addEventListener('click', async () => {
      // Reset to original state and retry
      const newContainer = this.createSubstitutableLinkElement(originalValue, 0, '', 'prefixed');
      container.parentNode.replaceChild(newContainer, container);
    });
    
    container.appendChild(errorHeader);
    container.appendChild(errorDetails);
    container.appendChild(retryBtn);
  }

  /**
   * Check if a URL is a valid HTTP/HTTPS URL
   */
  isValidHttpUrl(url) {
    if (typeof url !== 'string') return false;
    return url.startsWith('http://') || url.startsWith('https://');
  }

  /**
   * Check if a string is a prefixed ID (e.g., "universal:activity/cmip")
   */
  isPrefixedId(str) {
    if (typeof str !== 'string') return false;
    return str.includes(':') && !str.startsWith('http://') && !str.startsWith('https://');
  }

  /**
   * Check if a field is a linked field (should be highlighted and substituted)
   * UPDATED: Only use reference manager for proper JSON-LD based detection
   */
  isLinkedField(key) {
    if (!key) return false;
    
    // ONLY use reference manager - no fallback to hardcoded lists
    // Linked fields are ONLY those that have @type: "@id" or nested @context in the JSON-LD context
    if (this.referenceManager && this.referenceManager.isLinkedProperty) {
      const isLinked = this.referenceManager.isLinkedProperty(key);
      if (isLinked) {
        console.log(`🔗 Field '${key}' identified as linked via JSON-LD context analysis`);
      }
      return isLinked;
    }
    
    // Without reference manager, we cannot reliably determine linked fields
    return false;
  }

  // Create enhanced link element with status indicators
  createEnhancedLinkElement(data, level, key) {
    const container = document.createElement('div');
    const originalId = data['@id'];
    
    // FIXED: Ensure @id is a string before processing
    if (typeof originalId !== 'string') {
      console.warn('Enhanced link element received non-string @id:', originalId);
      container.innerHTML = '<span class="json-error">Invalid @id (not a string)</span>';
      return container;
    }
    
    // Check link status
    if (data['@broken']) {
      return this.createBrokenLinkElement(data, container);
    } else if (data['@loading']) {
      return this.createLoadingLinkElement(data, container);
    } else if (data['@substituted']) {
      return this.createSubstitutedLinkElement(data, level, container);
    } else {
      // Regular link
      return this.createRegularLinkElement(data, container);
    }
  }

  // Create broken link element (subtle, unobtrusive styling)
  createBrokenLinkElement(data, container) {
    container.className = 'json-broken-link-container';
    
    const errorIndicator = document.createElement('span');
    errorIndicator.className = 'json-error-indicator';
    errorIndicator.textContent = '❌ BROKEN: ';
    errorIndicator.style.color = '#dc2626';
    errorIndicator.style.fontWeight = 'bold';
    errorIndicator.style.fontSize = '0.9em';
    
    const link = document.createElement('span');
    link.className = 'json-string json-broken-link';
    
    // FIXED: Safely handle @id display
    const idValue = data['@id'] || data['@original-id'] || '[UNKNOWN]';
    link.textContent = `"${typeof idValue === 'string' ? idValue : '[INVALID ID]'}"`;
    
    link.style.color = '#dc2626';
    link.style.backgroundColor = '#fef2f2';
    link.style.border = '1px solid #fecaca';
    link.style.borderRadius = '3px';
    link.style.padding = '2px 4px';
    link.style.textDecoration = 'line-through';
    link.title = `Failed to load: ${data['@error'] || 'Unknown error'}`;
    
    container.appendChild(errorIndicator);
    container.appendChild(link);
    
    if (data['@error']) {
      const errorDetails = document.createElement('div');
      errorDetails.className = 'json-error-details';
      errorDetails.style.fontSize = '0.8em';
      errorDetails.style.color = '#991b1b';
      errorDetails.style.marginTop = '4px';
      errorDetails.style.padding = '4px 8px';
      errorDetails.style.backgroundColor = '#fee2e2';
      errorDetails.style.borderRadius = '3px';
      errorDetails.textContent = `Error: ${data['@error']}`;
      container.appendChild(errorDetails);
    }
    
    return container;
  }

  // Create loading link element (blue styling with animation)
  createLoadingLinkElement(data, container) {
    container.className = 'json-loading-link-container';
    
    const loadingIndicator = document.createElement('span');
    loadingIndicator.className = 'json-loading-indicator';
    loadingIndicator.textContent = '⏳ LOADING: ';
    loadingIndicator.style.color = '#2563eb';
    loadingIndicator.style.fontWeight = 'bold';
    loadingIndicator.style.fontSize = '0.9em';
    loadingIndicator.style.animation = 'pulse 1.5s infinite';
    
    const link = document.createElement('a');
    link.href = data['@resolvedUrl'] || data['@id'];
    link.target = '_blank';
    link.className = 'json-string json-loading-link';
    
    // FIXED: Safely handle @id display
    const idValue = data['@id'];
    link.textContent = `"${typeof idValue === 'string' ? idValue : '[INVALID ID]'}"`;
    
    link.style.color = '#2563eb';
    link.style.backgroundColor = '#eff6ff';
    link.style.border = '1px solid #bfdbfe';
    link.style.borderRadius = '3px';
    link.style.padding = '2px 4px';
    link.title = 'Content is being loaded...';
    
    container.appendChild(loadingIndicator);
    container.appendChild(link);
    
    return container;
  }

  // Create substituted link element (green styling with expanded content)
  createSubstitutedLinkElement(data, level, container) {
    container.className = 'json-substituted-link-container';
    container.style.borderLeft = '4px solid #10b981';
    container.style.paddingLeft = '12px';
    container.style.backgroundColor = '#f0fdf4';
    container.style.borderRadius = '6px';
    container.style.margin = '8px 0';
    container.style.padding = '12px';
    
    // Success indicator with expand/collapse functionality
    const header = document.createElement('div');
    header.className = 'json-substituted-header';
    header.style.cursor = 'pointer';
    header.style.display = 'flex';
    header.style.alignItems = 'center';
    header.style.marginBottom = '8px';
    
    const toggleIcon = document.createElement('span');
    toggleIcon.className = 'json-toggle-icon';
    toggleIcon.textContent = '▼';
    toggleIcon.style.marginRight = '8px';
    toggleIcon.style.color = '#059669';
    toggleIcon.style.fontWeight = 'bold';
    toggleIcon.style.transition = 'transform 0.2s ease';
    
    const successIndicator = document.createElement('span');
    successIndicator.className = 'json-success-indicator';
    successIndicator.style.color = '#059669';
    successIndicator.style.fontWeight = 'bold';
    successIndicator.style.fontSize = '0.9em';
    successIndicator.style.flexGrow = '1';
    
    const originalLink = document.createElement('a');
    originalLink.href = data['@resolvedUrl'] || data['@resolved-url'] || data['@id'];
    originalLink.target = '_blank';
    originalLink.className = 'json-url';
    
    // FIXED: Safely handle @id display
    const idValue = data['@id'];
    originalLink.textContent = typeof idValue === 'string' ? idValue : '[INVALID ID]';
    
    originalLink.style.marginLeft = '8px';
    originalLink.style.fontSize = '0.85em';
    
    successIndicator.innerHTML = '✅ SUBSTITUTED: ';
    successIndicator.appendChild(originalLink);
    
    header.appendChild(toggleIcon);
    header.appendChild(successIndicator);
    
    // Add timestamp if available
    if (data['@timestamp']) {
      const timestamp = document.createElement('div');
      timestamp.className = 'json-timestamp';
      timestamp.style.fontSize = '0.75em';
      timestamp.style.color = '#6b7280';
      timestamp.style.marginBottom = '8px';
      timestamp.textContent = `Loaded: ${new Date(data['@timestamp']).toLocaleString()}`;
      container.appendChild(timestamp);
    }
    
    // Content container (collapsible)
    const contentContainer = document.createElement('div');
    contentContainer.className = 'json-substituted-content';
    contentContainer.style.borderTop = '1px solid #d1fae5';
    contentContainer.style.paddingTop = '8px';
    contentContainer.style.marginTop = '8px';
    contentContainer.style.maxHeight = '400px';
    contentContainer.style.overflowY = 'auto';
    
    // Filter out metadata fields for display and render content
    const contentData = this.filterMetadataFields(data);
    
    // Check if there's substantial content to show
    const hasSubstantialContent = Object.keys(contentData).length > 1 || 
                                  (Object.keys(contentData).length === 1 && !contentData['@id']);
    
    if (hasSubstantialContent) {
      const contentElement = this.createJsonElement(contentData, level + 1);
      contentContainer.appendChild(contentElement);
      
      // Add expand/collapse functionality
      let isExpanded = true;
      const toggleContent = () => {
        if (isExpanded) {
          contentContainer.style.display = 'none';
          toggleIcon.textContent = '▶';
          toggleIcon.style.transform = 'rotate(0deg)';
          isExpanded = false;
        } else {
          contentContainer.style.display = 'block';
          toggleIcon.textContent = '▼';
          toggleIcon.style.transform = 'rotate(0deg)';
          isExpanded = true;
        }
      };
      
      header.addEventListener('click', toggleContent);
      
    } else {
      // No substantial content, just show a message
      contentContainer.innerHTML = '<em style="color: #6b7280; font-size: 0.9em;">No additional content to display</em>';
      toggleIcon.style.display = 'none';
      header.style.cursor = 'default';
    }
    
    container.appendChild(header);
    container.appendChild(contentContainer);
    
    return container;
  }

  // Create regular link element
  createRegularLinkElement(data, container) {
    const link = document.createElement('a');
    link.href = data['@resolvedUrl'] || data['@resolved-url'] || data['@id'];
    link.target = '_blank';
    link.className = 'json-string json-url';
    
    // FIXED: Safely handle @id display
    const idValue = data['@id'];
    link.textContent = `{"@id": "${typeof idValue === 'string' ? idValue : '[INVALID ID]'}"}`;
    
    container.appendChild(link);
    return container;
  }

  // Filter out metadata fields from substituted content
  // UPDATED: Remove ALL @ fields from display
  filterMetadataFields(data) {
    if (!data || typeof data !== 'object') {
      return data;
    }
    
    if (Array.isArray(data)) {
      return data.map(item => this.filterMetadataFields(item));
    }
    
    const filtered = {};
    for (const [key, value] of Object.entries(data)) {
      // Skip ALL fields that start with '@'
      if (!key.startsWith('@')) {
        // Recursively filter nested objects
        if (typeof value === 'object' && value !== null) {
          filtered[key] = this.filterMetadataFields(value);
        } else {
          filtered[key] = value;
        }
      }
    }
    
    return filtered;
  }

  // Check if a string is a URL
  isUrl(str) {
    if (typeof str !== 'string') return false;
    return str.startsWith('http://') || str.startsWith('https://') || 
           str.startsWith('/') || this.couldBeRelativeUrl(str);
  }

  // Check if string could be a relative URL
  couldBeRelativeUrl(str) {
    if (typeof str !== 'string') return false;
    // Simple heuristic: contains no spaces and has some URL-like characteristics
    return !str.includes(' ') && 
           (str.includes('/') || str.includes('.') || str.includes('-')) &&
           str.length > 0 &&
           /^[a-zA-Z0-9\-._~:/?#[\]@!$&'()*+,;=]+$/.test(str);
  }

  // Check if a field represents an ID field
  isIdField(key) {
    return key === '@id' || key === 'id' || key.endsWith('Id') || key.endsWith('_id') || key.includes('identifier');
  }

  // Get base URL from context or configuration
  getBaseUrl() {
    // First check if we have an original context with @base
    if (this.originalContext) {
      const base = this.extractBaseFromContext(this.originalContext);
      if (base) return base;
    }
    
    // Fallback to resolved context
    if (this.referenceManager && this.referenceManager.resolvedContext) {
      const context = this.referenceManager.resolvedContext;
      return context['@base'] || context['@vocab'] || '';
    }
    return '';
  }
  
  // Extract base URL from context (same logic as in viewer)
  extractBaseFromContext(context) {
    if (!context) return null;
    
    // Handle array of contexts
    if (Array.isArray(context)) {
      for (const ctx of context) {
        const base = this.extractBaseFromContext(ctx);
        if (base) return base;
      }
    } else if (typeof context === 'object' && context !== null) {
      // Look for @base in the context
      if (context['@base']) {
        return context['@base'];
      }
    }
    
    return null;
  }

  // Resolve URL with proper context-aware resolution
  resolveUrl(url, key = null) {
    // If we have a reference manager, use it for proper context resolution
    if (this.referenceManager) {
      // For @id fields or explicit ID-type fields, use reference expansion
      if (key === '@id' || key === 'id' || this.isIdField(key)) {
        const resolved = this.referenceManager.expandReference(url, key);
        console.log(`🔗 Resolving ID link: ${url} -> ${resolved}`);
        return resolved;
      }
      // For other URL-like values, still try reference expansion
      else if (this.referenceManager.isValidReference(url)) {
        const resolved = this.referenceManager.expandReference(url, key);
        console.log(`🔗 Resolving reference link: ${url} -> ${resolved}`);
        return resolved;
      }
    }
    
    // Fallback to basic URL resolution
    if (url.startsWith('http://') || url.startsWith('https://')) {
      return url;
    }
    
    const baseUrl = this.getBaseUrl();
    if (baseUrl) {
      if (url.startsWith('/')) {
        // Absolute path
        const base = new URL(baseUrl);
        return base.origin + url;
      }
      // Relative path
      return baseUrl + (baseUrl.endsWith('/') ? '' : '/') + url;
    }
    
    return url;
  }

  // Create array element
  createArrayElement(array, container, level) {
    // For simple arrays (strings, numbers, etc.), display inline
    const isSimpleArray = array.every(item => 
      typeof item === 'string' || 
      typeof item === 'number' || 
      typeof item === 'boolean' || 
      item === null
    );
    
    if (isSimpleArray) {
      // Display simple arrays inline
      const arrayDisplay = document.createElement('span');
      arrayDisplay.className = 'json-array-inline';
      arrayDisplay.textContent = '[';
      
      if (array.length === 0) {
        arrayDisplay.appendChild(document.createTextNode(']'));
      } else {
        array.forEach((item, index) => {
          if (index > 0) {
            arrayDisplay.appendChild(document.createTextNode(', '));
          }
          
          if (typeof item === 'string') {
            if (this.isUrl(item)) {
              const link = document.createElement('a');
              link.href = this.resolveUrl(item, 'array-item');
              link.target = '_blank';
              link.className = 'json-string json-url';
              link.textContent = `"${item}"`;
              arrayDisplay.appendChild(link);
            } else {
              const stringSpan = document.createElement('span');
              stringSpan.className = 'json-string';
              stringSpan.textContent = `"${Utils.escapeHtml(item)}"`;
              arrayDisplay.appendChild(stringSpan);
            }
          } else if (typeof item === 'number') {
            const numberSpan = document.createElement('span');
            numberSpan.className = 'json-number';
            numberSpan.textContent = item;
            arrayDisplay.appendChild(numberSpan);
          } else if (typeof item === 'boolean') {
            const boolSpan = document.createElement('span');
            boolSpan.className = 'json-boolean';
            boolSpan.textContent = item;
            arrayDisplay.appendChild(boolSpan);
          } else if (item === null) {
            const nullSpan = document.createElement('span');
            nullSpan.className = 'json-null';
            nullSpan.textContent = 'null';
            arrayDisplay.appendChild(nullSpan);
          }
        });
        
        arrayDisplay.appendChild(document.createTextNode(']'));
      }
      
      container.appendChild(arrayDisplay);
    } else {
      // Display complex arrays with collapsible structure
      const toggle = document.createElement('span');
      toggle.className = 'json-toggle';
      toggle.textContent = array.length > 0 ? '▼' : '';
      
      const header = document.createElement('div');
      header.appendChild(toggle);
      header.appendChild(document.createTextNode(`Array(${array.length})`));
      
      const content = document.createElement('div');
      content.className = 'json-array';
      
      array.forEach((item, index) => {
        const itemElement = document.createElement('div');
        itemElement.appendChild(document.createTextNode(`${index}: `));
        itemElement.appendChild(this.createJsonElement(item, level + 1));
        content.appendChild(itemElement);
      });
      
      if (array.length > 0) {
        toggle.onclick = () => this.toggleCollapse(content, toggle);
      }
      
      container.appendChild(header);
      container.appendChild(content);
    }
  }

  // Create object element
  createObjectElement(obj, container, level) {
    // Preserve original key order
    const keys = Object.keys(obj);
    
    const toggle = document.createElement('span');
    toggle.className = 'json-toggle';
    toggle.textContent = keys.length > 0 ? '▼' : '';
    
    const header = document.createElement('div');
    header.appendChild(toggle);
    header.appendChild(document.createTextNode(`Object(${keys.length})`));
    
    const content = document.createElement('div');
    content.className = 'json-object';
    
    keys.forEach(key => {
      const itemElement = document.createElement('div');
      const keySpan = document.createElement('span');
      keySpan.className = 'json-key';
      
      // Check if this is a linked property - use enhanced detection
      if (this.isLinkedField(key)) {
        keySpan.classList.add('linked-property');
      }
      
      // Make key a hyperlink if it's a URL or can be resolved to one
      const keyDisplay = this.createKeyDisplay(key, obj);
      keySpan.appendChild(keyDisplay);
      keySpan.appendChild(document.createTextNode(': '));
      
      itemElement.appendChild(keySpan);
      
      // Create value display with hyperlinks for URLs
      const valueElement = this.createValueElement(obj[key], level + 1, key);
      itemElement.appendChild(valueElement);
      
      content.appendChild(itemElement);
    });
    
    toggle.onclick = () => this.toggleCollapse(content, toggle);
    
    container.appendChild(header);
    container.appendChild(content);
  }

  // Toggle collapse/expand of JSON sections
  toggleCollapse(element, toggle) {
    if (element.style.display === 'none') {
      element.style.display = 'block';
      toggle.textContent = '▼';
    } else {
      element.style.display = 'none';
      toggle.textContent = '▶';
    }
  }

  // Filter out hidden fields
  filterHiddenFields(obj) {
    if (typeof obj !== 'object' || obj === null) {
      return obj;
    }

    if (Array.isArray(obj)) {
      return obj.map(item => this.filterHiddenFields(item));
    }

    const filtered = {};
    for (const [key, value] of Object.entries(obj)) {
      if (!this.hiddenFields.has(key)) {
        filtered[key] = this.filterHiddenFields(value);
      }
    }
    return filtered;
  }

  // Extract all field names from data
  extractFields(obj, fields = new Set()) {
    if (typeof obj !== 'object' || obj === null) {
      return fields;
    }

    if (Array.isArray(obj)) {
      obj.forEach(item => this.extractFields(item, fields));
      return fields;
    }

    Object.keys(obj).forEach(key => {
      fields.add(key);
      this.extractFields(obj[key], fields);
    });

    return fields;
  }

  // Toggle field visibility
  toggleField(field) {
    if (this.hiddenFields.has(field)) {
      this.hiddenFields.delete(field);
      return false; // Now visible
    } else {
      this.hiddenFields.add(field);
      return true; // Now hidden
    }
  }

  clearHiddenFields() {
    this.hiddenFields.clear();
  }

  // Add styles for enhanced link display
  addEnhancedLinkStyles() {
    if (document.getElementById('enhanced-link-styles')) return;

    const style = document.createElement('style');
    style.id = 'enhanced-link-styles';
    style.textContent = `
      @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
      }
      
      .json-broken-link-container {
        margin: 4px 0;
        padding: 8px;
        border-radius: 4px;
        background-color: #fef2f2;
        border: 1px solid #fecaca;
      }
      
      .json-loading-link-container {
        margin: 4px 0;
        padding: 8px;
        border-radius: 4px;
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
      }
      
      .json-substituted-link-container {
        margin: 8px 0 !important;
        box-shadow: 0 2px 4px rgba(16, 185, 129, 0.1);
      }
      
      .json-error-details {
        font-family: monospace;
      }
      
      .json-substituted-content {
        font-size: 0.95em;
      }
      
      .json-prefixed-link {
        background-color: #fef3c7 !important;
        border: 1px solid #f59e0b !important;
        border-radius: 3px;
        padding: 2px 4px;
        font-weight: 500;
      }
      
      .linked-property {
        background-color: #e0f2fe !important;
        border-radius: 3px;
        padding: 2px 4px;
        font-weight: 600;
        border: 1px solid #0284c7;
      }
      
      .json-error {
        color: #dc2626;
        background-color: #fef2f2;
        padding: 2px 4px;
        border-radius: 3px;
        font-weight: bold;
      }
      
      .json-invalid-id-container {
        margin: 4px 0;
        border-radius: 4px;
      }
      
      .json-error-header:hover {
        background-color: #fee2e2 !important;
      }
      
      .json-resolved-id-container {
        margin: 8px 0 !important;
        box-shadow: 0 2px 4px rgba(16, 185, 129, 0.1);
      }
      
      .json-resolved-header:hover {
        background-color: #ecfdf5 !important;
      }
      
      .json-resolved-content {
        font-size: 0.95em;
      }
      
      .json-substitute-btn {
        transition: all 0.2s ease;
      }
      
      .json-substitute-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
      }
      
      .json-substitute-btn:active {
        transform: translateY(0);
      }
      
      .json-substitutable-link-container {
        position: relative;
      }
      
      .json-inline-substituted-container {
        box-shadow: 0 2px 4px rgba(16, 185, 129, 0.1);
      }
      
      .json-inline-substituted-header:hover {
        background-color: #ecfdf5;
        border-radius: 4px;
        padding: 2px 4px;
        margin: -2px -4px;
      }
      
      .json-inline-error-container {
        box-shadow: 0 2px 4px rgba(220, 38, 38, 0.1);
      }
    `;
    
    document.head.appendChild(style);
  }
}