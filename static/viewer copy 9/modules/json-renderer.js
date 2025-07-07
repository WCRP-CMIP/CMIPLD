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
      // Special handling for expanded JSON-LD objects with only @id
      if (Object.keys(data).length === 1 && data['@id']) {
        // Render as a clickable link
        const idValue = data['@id'];
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
    // Handle substituted/broken/loading links
    if (typeof data === 'object' && data !== null && data['@id']) {
      return this.createEnhancedLinkElement(data, level, key);
    }
    
    // Handle prefixed IDs in compact mode (e.g., "universal:activity/cmip")
    if (typeof data === 'string' && this.isPrefixedId(data) && this.isLinkedField(key)) {
      const container = document.createElement('span');
      const link = document.createElement('a');
      link.href = this.resolveUrl(data, key);
      link.target = '_blank';
      link.className = 'json-string json-url json-prefixed-link';
      link.textContent = `"${data}"`;
      link.title = `Prefixed reference: ${data}`;
      container.appendChild(link);
      return container;
    }
    
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
   * Check if a string is a prefixed ID (e.g., "universal:activity/cmip")
   */
  isPrefixedId(str) {
    if (typeof str !== 'string') return false;
    return str.includes(':') && !str.startsWith('http://') && !str.startsWith('https://');
  }

  /**
   * Check if a field is a linked field (should be highlighted and substituted)
   */
  isLinkedField(key) {
    if (!key) return false;
    
    // Check with reference manager first
    if (this.referenceManager && this.referenceManager.isLinkedProperty(key)) {
      return true;
    }
    
    // Fallback: check against known CMIP linked fields
    const cmipLinkedFields = [
      'activity', 'experiment', 'source', 'institution', 'grid', 'variant',
      'variable', 'member', 'table', 'realm', 'frequency', 'modeling_realm',
      'required_model_components', 'parent_experiment_id', 'parent_variant_label',
      'activity_id', 'experiment_id', 'source_id', 'institution_id',
      'member_id', 'table_id', 'grid_label', 'variant_label',
      'variable_id', 'realm_id', 'frequency_id',
      'parent-activity', 'parent-experiment', 'sub-experiment', 'model-realms',
      'related', 'references', 'seeAlso', 'isVersionOf', 'isPartOf', 'derivedFrom'
    ];
    
    return cmipLinkedFields.includes(key) || 
           key.endsWith('_id') || 
           key.endsWith('Id') ||
           key.includes('related') ||
           key.includes('linked') ||
           key.includes('ref') ||
           key.includes('Reference') ||
           key.startsWith('see') ||
           key.startsWith('same');
  }

  // Create enhanced link element with status indicators
  createEnhancedLinkElement(data, level, key) {
    const container = document.createElement('div');
    const originalId = data['@id'];
    
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

  // Create broken link element (red styling)
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
    link.textContent = `"${data['@id']}"`;
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
    link.textContent = `"${data['@id']}"`;
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
    originalLink.href = data['@resolvedUrl'] || data['@id'];
    originalLink.target = '_blank';
    originalLink.className = 'json-url';
    originalLink.textContent = data['@id'];
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
    link.href = data['@resolvedUrl'] || data['@id'];
    link.target = '_blank';
    link.className = 'json-string json-url';
    link.textContent = `{"@id": "${data['@id']}"}`;
    container.appendChild(link);
    return container;
  }

  // Filter out metadata fields from substituted content
  filterMetadataFields(data) {
    const metadataFields = [
      '@resolved', '@status', '@timestamp', '@substituted', 
      '@broken', '@loading', '@error', '@resolvedUrl'
    ];
    
    const filtered = {};
    for (const [key, value] of Object.entries(data)) {
      if (!metadataFields.includes(key)) {
        filtered[key] = value;
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
    `;
    
    document.head.appendChild(style);
  }
}
