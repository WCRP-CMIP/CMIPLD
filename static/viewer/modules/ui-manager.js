// UI management for fields and controls
import { CONFIG } from './config.js';

export class UIManager {
  constructor(jsonRenderer, referenceManager) {
    this.jsonRenderer = jsonRenderer;
    this.referenceManager = referenceManager;
  }

  // Create field toggle buttons with proper JSON-LD grouping
  createFieldToggles(data, resolvedContext) {
    const togglesContainer = document.getElementById('fieldToggles');
    togglesContainer.innerHTML = '';
    
    // Store current data for field existence check
    this.currentData = data;
    this.fieldExistsInData = null; // Reset cache
    
    // Extract fields from the actual data structure
    const allFields = this.jsonRenderer.extractFields(data);
    
    // Also get all fields defined in the context (including linked fields)
    const contextDefinedFieldNames = new Set();
    if (resolvedContext) {
      for (const key of Object.keys(resolvedContext)) {
        if (!key.startsWith('@')) {
          contextDefinedFieldNames.add(key);
        }
      }
    }
    
    // Merge both sets to ensure we don't miss any fields
    const allFieldsSet = new Set([...allFields, ...contextDefinedFieldNames]);
    
    console.log('📋 All fields found in data:', Array.from(allFields));
    console.log('📋 All fields defined in context:', Array.from(contextDefinedFieldNames));
    console.log('📋 Combined field set:', Array.from(allFieldsSet));
    console.log('📋 Reference manager link properties:', this.referenceManager?.linkProperties ? Array.from(this.referenceManager.linkProperties) : 'none');
    
    // Categorize all fields into proper groups
    const presentJsonLDFields = [];
    const linkedFields = [];
    const otherFields = [];
    
    // First, add ALL linked properties from context to ensure they appear
    if (this.referenceManager && this.referenceManager.linkProperties) {
      for (const linkProp of this.referenceManager.linkProperties) {
        if (!CONFIG.jsonLDFields.includes(linkProp)) {
          linkedFields.push(linkProp);
        }
      }
    }
    
    // Then categorize the remaining fields
    for (const field of allFieldsSet) {
      if (CONFIG.jsonLDFields.includes(field)) {
        // JSON-LD system fields
        presentJsonLDFields.push(field);
      } else if (linkedFields.includes(field)) {
        // Already added as a linked field, skip
        continue;
      } else if (this.isLinkedField(field, data)) {
        // Fields that contain linked data (but weren't in context)
        linkedFields.push(field);
      } else {
        // All other fields (including context-defined but not linked)
        otherFields.push(field);
      }
    }
    
    console.log('📋 Field categorization:');
    console.log('  - JSON-LD fields:', presentJsonLDFields);
    console.log('  - Linked fields:', linkedFields);
    console.log('  - Other fields:', otherFields);
    
    // Create sections
    if (presentJsonLDFields.length > 0) {
      this.createFieldSection('JSON-LD Fields:', presentJsonLDFields, 'jsonld-field', togglesContainer);
    }
    
    if (linkedFields.length > 0) {
      this.createFieldSection('Linked Fields (@type: @id):', linkedFields, 'linked-field', togglesContainer);
    }
    
    if (otherFields.length > 0) {
      this.createFieldSection('Other Fields:', otherFields, 'content-field', togglesContainer);
    }
  }

  // Check if a field is defined in the context
  isContextDefinedField(field, resolvedContext) {
    // Check if the field exists in the context
    if (resolvedContext && resolvedContext.hasOwnProperty(field)) {
      return true;
    }
    
    // In expanded view, check if this field is an expanded URI that maps to a context term
    if (this.referenceManager && this.referenceManager.expandedToCompactMap) {
      return this.referenceManager.expandedToCompactMap.has(field);
    }
    
    return false;
  }

  // Check if field contains linked content
  isLinkedField(field, data) {
    // ALWAYS check if it's marked as a link in the context first
    // This ensures linked fields are identified even if they don't have data
    if (this.referenceManager && this.referenceManager.isLinkedProperty(field)) {
      console.log(`✅ Field '${field}' is a linked property (marked in context)`);
      return true;
    }
    
    // For fields not marked in context, check if they currently contain references
    const values = this.getFieldValues(field, data);
    
    for (const value of values) {
      if (typeof value === 'string' && this.referenceManager.isExpandableReference(value, field)) {
        return true;
      }
      // Note: We don't check for objects with @id here because that would include
      // already-expanded data, which should be categorized by context marking instead
    }
    
    return false;
  }

  // Get all values for a field
  getFieldValues(field, obj, values = []) {
    if (typeof obj !== 'object' || obj === null) {
      return values;
    }

    if (Array.isArray(obj)) {
      obj.forEach(item => this.getFieldValues(field, item, values));
    } else {
      if (obj.hasOwnProperty(field)) {
        if (Array.isArray(obj[field])) {
          values.push(...obj[field]);
        } else {
          values.push(obj[field]);
        }
      }
      
      Object.values(obj).forEach(value => {
        if (typeof value === 'object') {
          this.getFieldValues(field, value, values);
        }
      });
    }

    return values;
  }

  // Create field section
  createFieldSection(title, fields, className, container) {
    const header = document.createElement('div');
    header.className = 'field-section-header';
    header.textContent = title;
    container.appendChild(header);
    
    const sectionContainer = document.createElement('div');
    sectionContainer.className = 'field-section';
    
    fields.forEach(field => {
      const button = this.createFieldToggleButton(field);
      button.classList.add(className);
      
      if (className === 'linked-field') {
        this.addExpandFunctionality(button, field);
      }
      
      sectionContainer.appendChild(button);
    });
    
    container.appendChild(sectionContainer);
  }

  // Create field toggle button
  createFieldToggleButton(field) {
    const button = document.createElement('button');
    button.className = 'field-toggle';
    button.textContent = field;
    
    // Check if field is currently hidden
    if (this.jsonRenderer.hiddenFields.has(field)) {
      button.classList.add('hidden');
    }
    
    // Add visual indicator if field is not present in data
    if (!this.fieldExistsInData) {
      // Cache for performance
      this.fieldExistsInData = new Set();
      this.jsonRenderer.extractFields(this.currentData, this.fieldExistsInData);
    }
    
    if (!this.fieldExistsInData.has(field)) {
      button.style.opacity = '0.6';
      button.title = `${field} (defined in context but not present in data)`;
    }
    
    button.onclick = () => {
      const isHidden = this.jsonRenderer.toggleField(field);
      if (isHidden) {
        button.classList.add('hidden');
      } else {
        button.classList.remove('hidden');
      }
      
      // Trigger re-render
      this.triggerRerender();
    };
    
    return button;
  }

  // Add expand functionality to linked fields
  addExpandFunctionality(button, field) {
    const expandIcon = document.createElement('span');
    expandIcon.className = 'expand-icon';
    expandIcon.textContent = ' ▶';
    expandIcon.style.cursor = 'pointer';
    expandIcon.style.marginLeft = '5px';
    expandIcon.style.fontSize = '0.7em';
    expandIcon.style.opacity = '0.7';
    
    expandIcon.onclick = (e) => {
      e.stopPropagation();
      this.toggleFieldExpansion(field, expandIcon);
    };
    
    button.appendChild(expandIcon);
  }

  // Toggle field expansion (placeholder - needs to be connected to main viewer)
  toggleFieldExpansion(field, expandIcon) {
    const depth = parseInt(document.getElementById('depth').value) || 2;
    
    if (depth <= 0) {
      alert('Expansion depth is 0. Increase depth to expand linked fields.');
      return;
    }
    
    const isExpanded = expandIcon.textContent.includes('▼');
    
    if (isExpanded) {
      expandIcon.textContent = ' ▶';
      expandIcon.style.opacity = '0.7';
      console.log(`🔗 Reverting field expansion: ${field}`);
    } else {
      expandIcon.textContent = ' ▼';
      expandIcon.style.opacity = '1';
      console.log(`🔗 Force expanding field: ${field}`);
    }
    
    // This needs to be connected to the main viewer for actual functionality
    this.triggerFieldExpansion(field, !isExpanded);
  }

  // Placeholder for triggering re-render (to be connected to main viewer)
  triggerRerender() {
    console.log('🔄 Triggering re-render...');
    // This will be connected to the main viewer
  }

  // Placeholder for field expansion (to be connected to main viewer)
  triggerFieldExpansion(field, expand) {
    console.log(`🔗 Field expansion request: ${field}, expand: ${expand}`);
    // This will be connected to the main viewer
  }

  // Show loading state
  showLoading(show) {
    document.getElementById('loading').style.display = show ? 'block' : 'none';
    document.getElementById('loadBtn').disabled = show;
  }

  // Show error message
  showError(message) {
    const resultSection = document.getElementById('resultSection');
    if (!resultSection) {
      console.error('Result section not found');
      alert(message);
      return;
    }
    
    // Clear previous results but keep the structure
    const jsonViewer = document.getElementById('jsonViewer');
    if (jsonViewer) {
      jsonViewer.innerHTML = `<div class="error-message">${message}</div>`;
    }
    
    // Hide stats and field toggles
    const resultStats = document.getElementById('resultStats');
    if (resultStats) {
      resultStats.textContent = 'Error';
    }
    
    const fieldToggles = document.getElementById('fieldToggles');
    if (fieldToggles) {
      fieldToggles.innerHTML = '';
    }
    
    resultSection.style.display = 'block';
  }
}
