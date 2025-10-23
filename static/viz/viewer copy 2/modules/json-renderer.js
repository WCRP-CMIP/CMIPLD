// JSON rendering and display
import { Utils } from './utils.js';

export class JSONRenderer {
  constructor() {
    this.hiddenFields = new Set();
    this.referenceManager = null;
    this.originalContext = null;
  }

  // Set reference manager for linked field detection
  setReferenceManager(referenceManager) {
    this.referenceManager = referenceManager;
  }
  
  // Set original context for base URL extraction
  setOriginalContext(context) {
    this.originalContext = context;
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
        link.href = this.resolveUrl(data);
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
        // Render as a clickable link instead of an object
        const idValue = data['@id'];
        if (this.isUrl(idValue)) {
          const link = document.createElement('a');
          link.href = this.resolveUrl(idValue);
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
      link.href = this.resolveUrl(key);
      link.target = '_blank';
      link.className = 'json-key-link';
      link.textContent = keyText;
      return link;
    }
    
    // Check if we can build a URL from base + key
    const baseUrl = this.getBaseUrl();
    if (baseUrl && this.couldBeRelativeUrl(key)) {
      const fullUrl = this.resolveUrl(key);
      const link = document.createElement('a');
      link.href = fullUrl;
      link.target = '_blank';
      link.className = 'json-key-link';
      link.textContent = keyText;
      return link;
    }
    
    return document.createTextNode(keyText);
  }

  // Create value element with proper handling for URLs
  createValueElement(data, level, key) {
    if (typeof data === 'string' && this.isUrl(data)) {
      const container = document.createElement('span');
      const link = document.createElement('a');
      link.href = this.resolveUrl(data);
      link.target = '_blank';
      link.className = 'json-string json-url';
      link.textContent = `"${data}"`;
      container.appendChild(link);
      return container;
    }
    return this.createJsonElement(data, level, key);
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

  // Resolve URL with base
  resolveUrl(url) {
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
              link.href = this.resolveUrl(item);
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
      
      // Check if this is a linked property
      if (this.referenceManager && this.referenceManager.isLinkedProperty(key)) {
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
}
