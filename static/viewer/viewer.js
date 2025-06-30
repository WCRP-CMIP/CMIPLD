// CMIP-LD Viewer v2 - Clean implementation following the specified workflow
import { CONFIG } from './modules/config.js';
import { Utils } from './modules/utils.js';
import { URLManager } from './modules/url-manager.js';
import { DocumentLoader } from './modules/document-loader.js';
import { ReferenceManager } from './modules/reference-manager.js';
import { JSONLDProcessor } from './modules/jsonld-processor.js';
import { JSONRenderer } from './modules/json-renderer.js';
import { UIManager } from './modules/ui-manager.js';

export class CMIPLDViewer {
  constructor() {
    this.initializeModules();
    this.initializeState();
    this.initializeFromUrl();
    this.initializeEventListeners();
  }

  initializeModules() {
    // Core modules
    this.documentLoader = new DocumentLoader(CONFIG.corsProxies);
    this.referenceManager = new ReferenceManager(CONFIG.prefixMapping);
    this.jsonldProcessor = new JSONLDProcessor(this.documentLoader, {});
    this.jsonRenderer = new JSONRenderer();
    this.jsonRenderer.setReferenceManager(this.referenceManager);
    this.uiManager = new UIManager(this.jsonRenderer, this.referenceManager);
    
    // Connect UI callbacks
    this.uiManager.triggerRerender = () => this.rerenderDisplay();
    this.uiManager.triggerFieldExpansion = (field, expand) => this.handleFieldExpansion(field, expand);
  }

  initializeState() {
    // Storage for all documents in their various forms
    this.documents = new Map(); // URL -> { raw, expanded, compacted, context }
    this.mainDocumentUrl = null;
    this.mergedContext = {};
    this.isExpanded = false;
    this.currentViewData = null;
  }

  initializeFromUrl() {
    const settings = URLManager.initializeFromUrl();
    
    // Apply settings to DOM
    if (settings.uri) {
      document.getElementById('uri').value = settings.uri;
    }
    document.getElementById('depth').value = settings.depth || CONFIG.defaults.depth;
    document.getElementById('followLinks').checked = settings.followLinks !== undefined ? 
      settings.followLinks : CONFIG.defaults.followLinks;
    document.getElementById('insertContext').checked = settings.insertContext !== undefined ? 
      settings.insertContext : CONFIG.defaults.insertContext;
    
    this.isExpanded = settings.isExpanded || false;
    document.getElementById('viewToggle').checked = this.isExpanded;
    
    // Apply panel state
    if (settings.panelMinimized) {
      const inputSection = document.getElementById('inputSection');
      const minimizeIcon = document.querySelector('.minimize-icon');
      if (inputSection) inputSection.classList.add('minimized');
      if (minimizeIcon) minimizeIcon.textContent = '+';
      const minimizeBtn = document.getElementById('minimizeBtn');
      if (minimizeBtn) minimizeBtn.title = 'Expand';
    }
    
    // Auto-load if URI is provided
    if (settings.uri) {
      setTimeout(() => this.loadData(), 100);
    }
  }

  initializeEventListeners() {
    // Basic controls
    document.getElementById('loadBtn').addEventListener('click', () => this.loadData());
    document.getElementById('uri').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.loadData();
    });
    
    // Minimize button
    this.initializeMinimizeButton();
    
    // Settings changes
    document.getElementById('uri').addEventListener('input', () => this.updateUrl());
    document.getElementById('depth').addEventListener('change', () => this.updateUrl());
    document.getElementById('followLinks').addEventListener('change', () => {
      this.updateUrl();
      if (this.mainDocumentUrl) this.updateView();
    });
    document.getElementById('insertContext').addEventListener('change', () => {
      this.updateUrl();
      if (this.mainDocumentUrl) this.updateView();
    });
    
    // Export functions
    document.getElementById('copyBtn').addEventListener('click', () => this.copyToClipboard());
    document.getElementById('downloadBtn').addEventListener('click', () => this.downloadJson());
    
    // View toggle
    this.initializeViewToggle();
  }

  initializeMinimizeButton() {
    const minimizeBtn = document.getElementById('minimizeBtn');
    const inputSection = document.getElementById('inputSection');
    const minimizeIcon = minimizeBtn.querySelector('.minimize-icon');
    
    minimizeBtn.addEventListener('click', () => {
      inputSection.classList.toggle('minimized');
      
      if (inputSection.classList.contains('minimized')) {
        minimizeIcon.textContent = '+';
        minimizeBtn.title = 'Expand';
      } else {
        minimizeIcon.textContent = '−';
        minimizeBtn.title = 'Minimize';
      }
      
      this.updateUrl();
    });
  }

  initializeViewToggle() {
    const viewToggle = document.getElementById('viewToggle');
    
    viewToggle.addEventListener('change', (e) => {
      this.isExpanded = e.target.checked;
      this.updateUrl();
      if (this.mainDocumentUrl) this.updateView();
    });
  }

  updateUrl() {
    const inputSection = document.getElementById('inputSection');
    const settings = {
      uri: document.getElementById('uri').value.trim(),
      depth: document.getElementById('depth').value,
      followLinks: document.getElementById('followLinks').checked,
      insertContext: document.getElementById('insertContext').checked,
      isExpanded: this.isExpanded,
      panelMinimized: inputSection.classList.contains('minimized')
    };
    
    URLManager.updateUrl(settings);
  }

  async loadData() {
    const uri = document.getElementById('uri').value.trim();
    if (!uri) {
      this.uiManager.showError('Please enter a URI or prefix');
      return;
    }

    const depth = parseInt(document.getElementById('depth').value) || 2;
    const followLinks = document.getElementById('followLinks').checked;
    
    this.uiManager.showLoading(true);

    try {
      // Clear previous data
      this.clearData();
      this.updateUrl();
      
      // Step 1: Resolve prefix and get the URL
      const resolvedUri = Utils.resolvePrefix(uri, CONFIG.prefixMapping);
      this.mainDocumentUrl = resolvedUri;
      console.log('📍 Step 1: Resolved URI:', resolvedUri);
      
      // Step 2: Get data
      console.log('📥 Step 2: Fetching main document...');
      const rawData = await this.documentLoader.fetchDocument(resolvedUri);
      console.log('✅ Fetched main document, keys:', Object.keys(rawData));
      
      // Step 3: Expand the view
      console.log('📋 Step 3: Expanding main document...');
      const expandedData = await this.jsonldProcessor.safeExpand(rawData);
      console.log('✅ Expanded main document, got', expandedData.length, 'items');
      
      // Store the main document
      this.documents.set(resolvedUri, {
        raw: rawData,
        expanded: expandedData,
        compacted: null, // Will be computed on demand
        context: rawData['@context'] || null,
        isMain: true
      });
      
      // Step 4 & 5: Find and fetch linked files if enabled
      if (followLinks && depth > 0) {
        console.log('🔗 Step 4: Finding linked files from context and expanded data...');
        await this.loadLinkedDocuments(expandedData, rawData['@context'], resolvedUri, depth);
      }
      
      // Build merged context from all loaded documents
      await this.buildMergedContext();
      
      // Set up reference manager with the merged context
      this.referenceManager.setResolvedContext(this.mergedContext);
      this.jsonldProcessor.resolvedContext = this.mergedContext;
      
      // Update the view
      await this.updateView();
      
    } catch (error) {
      console.error('❌ Failed to load data:', error);
      this.uiManager.showError(`Failed to load data: ${error.message}`);
    } finally {
      this.uiManager.showLoading(false);
    }
  }

  async loadLinkedDocuments(expandedData, context, baseUrl, depth) {
    if (depth <= 0) return;
    
    const linkedUrls = new Set();
    
    // Find @id references in the expanded data
    this.findLinkedUrls(expandedData, linkedUrls);
    
    // Also check context for @type: @id properties and their values
    if (context) {
      await this.findLinkedUrlsFromContext(context, baseUrl, linkedUrls);
    }
    
    console.log(`🔗 Found ${linkedUrls.size} linked URLs to fetch:`, Array.from(linkedUrls));
    
    // Fetch each linked document
    for (const url of linkedUrls) {
      if (this.documents.has(url)) continue; // Already loaded
      
      try {
        console.log(`📥 Fetching linked document: ${url}`);
        const rawLinkedDoc = await this.documentLoader.fetchDocument(url);
        
        // Expand the linked document
        const expandedLinkedDoc = await this.jsonldProcessor.safeExpand(rawLinkedDoc);
        console.log(`✅ Expanded linked document: ${url}`);
        
        // Store the linked document
        this.documents.set(url, {
          raw: rawLinkedDoc,
          expanded: expandedLinkedDoc,
          compacted: null, // Will be computed on demand
          context: rawLinkedDoc['@context'] || null,
          isMain: false
        });
        
        // Recursively load more linked documents
        if (depth > 1) {
          await this.loadLinkedDocuments(expandedLinkedDoc, rawLinkedDoc['@context'], url, depth - 1);
        }
      } catch (error) {
        console.warn(`⚠️ Could not fetch linked document ${url}:`, error.message);
      }
    }
  }

  findLinkedUrls(data, urls, visited = new Set()) {
    if (!data || visited.has(data)) return;
    
    if (typeof data === 'object') {
      visited.add(data);
      
      if (Array.isArray(data)) {
        data.forEach(item => this.findLinkedUrls(item, urls, visited));
      } else {
        // Check for @id references (objects with only @id property)
        Object.values(data).forEach(value => {
          if (typeof value === 'object' && value !== null && !Array.isArray(value) &&
              Object.keys(value).length === 1 && value['@id'] && 
              typeof value['@id'] === 'string' && value['@id'].startsWith('http')) {
            urls.add(value['@id']);
          } else if (Array.isArray(value)) {
            value.forEach(item => {
              if (typeof item === 'object' && item !== null && !Array.isArray(item) &&
                  Object.keys(item).length === 1 && item['@id'] && 
                  typeof item['@id'] === 'string' && item['@id'].startsWith('http')) {
                urls.add(item['@id']);
              } else {
                this.findLinkedUrls(item, urls, visited);
              }
            });
          } else {
            this.findLinkedUrls(value, urls, visited);
          }
        });
      }
      
      visited.delete(data);
    }
  }

  async findLinkedUrlsFromContext(context, baseUrl, urls) {
    // Process context to find properties marked as @type: @id
    const processContext = async (ctx) => {
      if (typeof ctx === 'string' && ctx.startsWith('http')) {
        // Load external context
        try {
          const contextDoc = await this.documentLoader.fetchDocument(ctx);
          if (contextDoc && contextDoc['@context']) {
            await processContext(contextDoc['@context']);
          }
        } catch (e) {
          console.warn(`Could not load context: ${ctx}`);
        }
      } else if (Array.isArray(ctx)) {
        for (const item of ctx) {
          await processContext(item);
        }
      } else if (typeof ctx === 'object' && ctx !== null) {
        // Check for link properties
        for (const [key, value] of Object.entries(ctx)) {
          if (typeof value === 'object' && value !== null && value['@type'] === '@id') {
            // This is a link property - mark it
            this.referenceManager.markAsLinkProperty(key);
          }
        }
      }
    };
    
    await processContext(context);
  }

  async buildMergedContext() {
    this.mergedContext = {};
    
    // Merge contexts from all documents
    for (const [url, doc] of this.documents) {
      if (doc.context) {
        const resolvedContext = await this.resolveContext(doc.context, url);
        Object.assign(this.mergedContext, resolvedContext);
      }
    }
    
    console.log('📝 Built merged context with', Object.keys(this.mergedContext).length, 'terms');
  }

  async resolveContext(context, baseUrl) {
    const result = {};
    
    if (typeof context === 'string') {
      try {
        const contextDoc = await this.documentLoader.fetchDocument(context);
        if (contextDoc && contextDoc['@context']) {
          return this.resolveContext(contextDoc['@context'], context);
        }
      } catch (e) {
        console.warn(`Could not resolve context: ${context}`);
      }
    } else if (Array.isArray(context)) {
      for (const ctx of context) {
        const resolved = await this.resolveContext(ctx, baseUrl);
        Object.assign(result, resolved);
      }
    } else if (typeof context === 'object' && context !== null) {
      Object.assign(result, context);
    }
    
    return result;
  }

  async updateView() {
    if (!this.mainDocumentUrl) return;
    
    console.log('🔄 === UPDATING VIEW ===');
    console.log('📋 View mode:', this.isExpanded ? 'EXPANDED' : 'COMPACTED');
    
    const toggleContainer = document.querySelector('.result-header');
    if (toggleContainer) toggleContainer.style.opacity = '0.6';
    
    try {
      // Get the main document
      const mainDoc = this.documents.get(this.mainDocumentUrl);
      if (!mainDoc) {
        throw new Error('Main document not found');
      }
      
      let viewData;
      
      if (this.isExpanded) {
        // Step 5: Create expanded view with substitutions
        viewData = await this.createExpandedView(mainDoc);
      } else {
        // Step 6: Create compacted view
        viewData = await this.createCompactedView(mainDoc);
      }
      
      // Handle context insertion
      const insertContext = document.getElementById('insertContext').checked;
      if (insertContext && this.isExpanded && mainDoc.context) {
        // Add context to expanded view (unusual but supported)
        if (Array.isArray(viewData)) {
          viewData = {
            '@context': mainDoc.context,
            '@graph': viewData
          };
        }
      } else if (!insertContext && !this.isExpanded && viewData['@context']) {
        // Remove context from compacted view
        const { '@context': _, ...dataWithoutContext } = viewData;
        viewData = dataWithoutContext;
      }
      
      this.currentViewData = viewData;
      this.displayResult(viewData);
      
    } catch (error) {
      console.error('❌ Failed to update view:', error);
      this.uiManager.showError(`Failed to update view: ${error.message}`);
    } finally {
      if (toggleContainer) toggleContainer.style.opacity = '1';
    }
  }

  async createExpandedView(mainDoc) {
    // Start with the expanded main document
    let expandedView = JSON.parse(JSON.stringify(mainDoc.expanded)); // Deep clone
    
    const followLinks = document.getElementById('followLinks').checked;
    if (!followLinks) {
      return expandedView;
    }
    
    // Build substitution map from all loaded documents
    const substitutionMap = new Map();
    for (const [url, doc] of this.documents) {
      if (url === this.mainDocumentUrl) continue; // Skip main doc
      
      // Find the main entity in the expanded document
      if (doc.expanded && doc.expanded.length > 0) {
        const entity = doc.expanded.find(item => item['@id'] === url) || doc.expanded[0];
        if (entity) {
          substitutionMap.set(url, entity);
        }
      }
    }
    
    console.log('📦 Built substitution map with', substitutionMap.size, 'entities');
    
    // Substitute linked references
    if (substitutionMap.size > 0) {
      expandedView = this.substituteLinks(expandedView, substitutionMap);
    }
    
    return expandedView;
  }

  async createCompactedView(mainDoc) {
    // First create the expanded view with substitutions
    const expandedView = await this.createExpandedView(mainDoc);
    
    // Get the appropriate context for compaction
    let compactionContext = mainDoc.context || {};
    
    // If the main document has a context reference, try to resolve it
    if (typeof compactionContext === 'string') {
      const resolved = await this.resolveContext(compactionContext, this.mainDocumentUrl);
      if (Object.keys(resolved).length > 0) {
        compactionContext = resolved;
      }
    } else if (Array.isArray(compactionContext) && compactionContext.length > 0) {
      // Use the first context for compaction
      compactionContext = compactionContext[0];
      if (typeof compactionContext === 'string') {
        const resolved = await this.resolveContext(compactionContext, this.mainDocumentUrl);
        if (Object.keys(resolved).length > 0) {
          compactionContext = resolved;
        }
      }
    }
    
    // Compact the expanded view
    console.log('🔄 Compacting with context:', 
      typeof compactionContext === 'object' ? Object.keys(compactionContext).length + ' terms' : compactionContext);
    
    const compactedView = await this.jsonldProcessor.safeCompact(expandedView, compactionContext);
    
    // Store the compacted version
    const doc = this.documents.get(this.mainDocumentUrl);
    if (doc) {
      doc.compacted = compactedView;
    }
    
    return compactedView;
  }

  substituteLinks(data, substitutionMap, depth = 0, maxDepth = 10, visited = new Set()) {
    if (!data || visited.has(data) || depth > maxDepth) return data;
    
    if (typeof data === 'object') {
      visited.add(data);
      
      if (Array.isArray(data)) {
        const result = data.map(item => this.substituteLinks(item, substitutionMap, depth, maxDepth, visited));
        visited.delete(data);
        return result;
      } else {
        const result = {};
        
        Object.entries(data).forEach(([key, value]) => {
          // Check if this is a link reference that we can substitute
          if (typeof value === 'object' && value !== null && !Array.isArray(value) &&
              Object.keys(value).length === 1 && value['@id'] && 
              substitutionMap.has(value['@id'])) {
            // Substitute with the expanded entity
            const substituted = substitutionMap.get(value['@id']);
            console.log(`🔄 Substituting ${key}: ${value['@id']}`);
            result[key] = this.substituteLinks(substituted, substitutionMap, depth + 1, maxDepth, new Set());
          } else if (Array.isArray(value)) {
            // Process array items
            result[key] = value.map(item => {
              if (typeof item === 'object' && item !== null && !Array.isArray(item) &&
                  Object.keys(item).length === 1 && item['@id'] && 
                  substitutionMap.has(item['@id'])) {
                console.log(`🔄 Substituting ${key}[]: ${item['@id']}`);
                return this.substituteLinks(substitutionMap.get(item['@id']), substitutionMap, depth + 1, maxDepth, new Set());
              }
              return this.substituteLinks(item, substitutionMap, depth, maxDepth, visited);
            });
          } else {
            // Recursively process other values
            result[key] = this.substituteLinks(value, substitutionMap, depth, maxDepth, visited);
          }
        });
        
        visited.delete(data);
        return result;
      }
    }
    
    return data;
  }

  async displayResult(data) {
    const resultSection = document.getElementById('resultSection');
    const statsElement = document.getElementById('resultStats');
    const jsonViewer = document.getElementById('jsonViewer');
    const viewToggle = document.getElementById('viewToggle');
    
    if (!resultSection || !jsonViewer) {
      console.error('Required DOM elements not found');
      return;
    }
    
    if (viewToggle) {
      viewToggle.checked = this.isExpanded;
    }
    
    // Calculate statistics
    const displayData = this.jsonRenderer.filterHiddenFields(data);
    const jsonString = JSON.stringify(displayData, null, 2);
    const lines = jsonString.split('\n').length;
    const size = new Blob([jsonString]).size;
    const loadedDocs = this.documents.size;
    const contextTerms = Object.keys(this.mergedContext).length;
    
    const viewMode = this.isExpanded ? 
      '🔄 EXPANDED VIEW: jsonld.expand output (absolute URIs)' : 
      '📄 COMPACTED VIEW: jsonld.compact output (human-readable)';
    
    if (statsElement) {
      statsElement.textContent = `${viewMode} • ${lines} lines • ${Utils.formatBytes(size)} • ${loadedDocs} documents loaded • ${contextTerms} context terms`;
    }
    
    // Get the main document context for field toggles
    const mainDoc = this.documents.get(this.mainDocumentUrl);
    const contextForToggles = mainDoc ? await this.resolveContext(mainDoc.context, this.mainDocumentUrl) : {};
    
    // Create field toggles
    this.uiManager.createFieldToggles(data, contextForToggles);
    
    // Render JSON
    this.jsonRenderer.renderJson(displayData, jsonViewer);
    
    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
  }

  // UI callback handlers
  rerenderDisplay() {
    if (this.currentViewData) {
      const jsonViewer = document.getElementById('jsonViewer');
      const displayData = this.jsonRenderer.filterHiddenFields(this.currentViewData);
      this.jsonRenderer.renderJson(displayData, jsonViewer);
    }
  }

  handleFieldExpansion(field, expand) {
    console.log(`🔗 Field expansion request: ${field}, expand: ${expand}`);
    // This could be implemented to dynamically expand/collapse specific fields
    this.rerenderDisplay();
  }

  // Export functions
  async copyToClipboard() {
    if (!this.currentViewData) return;
    
    try {
      const displayData = this.jsonRenderer.filterHiddenFields(this.currentViewData);
      const jsonString = JSON.stringify(displayData, null, 2);
      await navigator.clipboard.writeText(jsonString);
      
      const btn = document.getElementById('copyBtn');
      const originalText = btn.textContent;
      btn.textContent = 'Copied!';
      btn.style.backgroundColor = 'var(--success-color)';
      
      setTimeout(() => {
        btn.textContent = originalText;
        btn.style.backgroundColor = '';
      }, 2000);
    } catch (error) {
      this.fallbackCopy();
    }
  }

  fallbackCopy() {
    const displayData = this.jsonRenderer.filterHiddenFields(this.currentViewData);
    const jsonString = JSON.stringify(displayData, null, 2);
    const textArea = document.createElement('textarea');
    textArea.value = jsonString;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    
    const btn = document.getElementById('copyBtn');
    const originalText = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {
      btn.textContent = originalText;
    }, 2000);
  }

  downloadJson() {
    if (!this.currentViewData) return;
    
    const displayData = this.jsonRenderer.filterHiddenFields(this.currentViewData);
    const jsonString = JSON.stringify(displayData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `cmipld-data-${this.isExpanded ? 'expanded' : 'compacted'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  // Utility methods
  clearData() {
    this.documents.clear();
    this.mainDocumentUrl = null;
    this.mergedContext = {};
    this.currentViewData = null;
    this.documentLoader.clear();
    this.jsonldProcessor.clear();
    this.jsonRenderer.setOriginalContext(null);
  }
}

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', () => {
  window.cmipldViewer = new CMIPLDViewer();
});
