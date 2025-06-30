// Main CMIP-LD Viewer class that orchestrates all modules
import { CONFIG } from './modules/config.js';
import { Utils } from './modules/utils.js';
import { URLManager } from './modules/url-manager.js';
import { DocumentLoader } from './modules/document-loader.js';
import { ReferenceManager } from './modules/reference-manager.js';
import { JSONLDProcessor } from './modules/jsonld-processor.js';
import { LinkedItemResolver } from './modules/linked-item-resolver.js';
import { ContextExpander } from './modules/context-expander.js';
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
    this.linkedItemResolver = new LinkedItemResolver(this.referenceManager, this.jsonldProcessor, CONFIG.prefixMapping);
    this.contextExpander = new ContextExpander(this.documentLoader, CONFIG.prefixMapping);
    this.jsonRenderer = new JSONRenderer();
    this.jsonRenderer.setReferenceManager(this.referenceManager);
    this.uiManager = new UIManager(this.jsonRenderer, this.referenceManager);
    
    // Connect UI callbacks
    this.uiManager.triggerRerender = () => this.rerenderDisplay();
    this.uiManager.triggerFieldExpansion = (field, expand) => this.handleFieldExpansion(field, expand);
  }

  initializeState() {
    this.currentRawData = null;
    this.currentProcessedData = null;
    this.resolvedContext = {};
    this.originalContext = null;
    this.isExpanded = false;
  }

  initializeFromUrl() {
    const settings = URLManager.initializeFromUrl();
    
    // Apply settings to DOM
    if (settings.uri) {
      document.getElementById('uri').value = settings.uri;
    }
    if (settings.depth) {
      document.getElementById('depth').value = settings.depth;
    } else {
      document.getElementById('depth').value = CONFIG.defaults.depth;
    }
    if (settings.followLinks !== undefined) {
      document.getElementById('followLinks').checked = settings.followLinks;
    } else {
      document.getElementById('followLinks').checked = CONFIG.defaults.followLinks;
    }
    if (settings.insertContext !== undefined) {
      document.getElementById('insertContext').checked = settings.insertContext;
    } else {
      document.getElementById('insertContext').checked = CONFIG.defaults.insertContext;
    }
    
    this.isExpanded = settings.isExpanded || false;
    document.getElementById('viewToggle').checked = this.isExpanded;
    
    // Apply panel state
    if (settings.panelMinimized) {
      const inputSection = document.getElementById('inputSection');
      const minimizeIcon = document.querySelector('.minimize-icon');
      if (inputSection) {
        inputSection.classList.add('minimized');
      }
      if (minimizeIcon) {
        minimizeIcon.textContent = '+';
      }
      const minimizeBtn = document.getElementById('minimizeBtn');
      if (minimizeBtn) {
        minimizeBtn.title = 'Expand';
      }
    }
    
    console.log('Initialized from URL - isExpanded:', this.isExpanded);
    
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
    document.getElementById('followLinks').addEventListener('change', () => this.updateUrl());
    document.getElementById('insertContext').addEventListener('change', () => {
      this.updateUrl();
      this.updateView();
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
      
      // Update icon
      if (inputSection.classList.contains('minimized')) {
        minimizeIcon.textContent = '+';
        minimizeBtn.title = 'Expand';
      } else {
        minimizeIcon.textContent = '−';
        minimizeBtn.title = 'Minimize';
      }
      
      // Update URL
      this.updateUrl();
    });
  }

  initializeViewToggle() {
    const viewToggle = document.getElementById('viewToggle');
    
    const handleToggle = (checked) => {
      console.log('🔄 Toggle change:', checked);
      this.isExpanded = checked;
      this.updateUrl();
      
      if (this.currentRawData) {
        this.updateView();
      }
    };
    
    viewToggle.addEventListener('change', (e) => handleToggle(e.target.checked));
    viewToggle.addEventListener('click', (e) => {
      setTimeout(() => handleToggle(e.target.checked), 10);
    });
    viewToggle.addEventListener('input', (e) => handleToggle(e.target.checked));
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
    
    this.uiManager.showLoading(true);

    try {
      // Clear previous data
      this.clearData();
      
      this.updateUrl();
      
      // Step 1: Load main document
      const resolvedUri = Utils.resolvePrefix(uri, CONFIG.prefixMapping);
      const data = await this.documentLoader.fetchDocument(resolvedUri);
      this.currentRawData = data;
      
      console.log('📊 Loaded raw data, keys:', Object.keys(data));
      
      // Store the original context from the main file
      this.originalContext = data['@context'] || null;
      console.log('📝 Original context from file:', this.originalContext);
      
      // Identify the first context if it's an array
      let firstContext = this.originalContext;
      if (Array.isArray(this.originalContext) && this.originalContext.length > 0) {
        firstContext = this.originalContext[0];
        console.log('📝 Using FIRST context from array:', firstContext);
      }
      
      // Extract base URL from context if available
      let baseUrl = resolvedUri;
      if (data['@context']) {
        const extractedBase = this.extractBaseFromContext(data['@context']);
        if (extractedBase) {
          baseUrl = extractedBase;
          console.log('🔗 Extracted base URL from @context:', baseUrl);
        }
      }
      
      // Step 2: Load linked documents
      await this.loadLinkedDocuments(data, baseUrl, depth);
      
      // Step 3: Build resolved context from original file only
      this.resolvedContext = await this.buildResolvedContextFromOriginal(this.originalContext, baseUrl);
      
      // Also build a full merged context for internal processing
      const mergedContext = await this.documentLoader.buildResolvedContext(data, baseUrl);
      
      // Use merged context for JSON-LD processing but keep original for display
      console.log('📝 Resolved context from original file (first context only):', this.resolvedContext);
      console.log('📝 Merged context for processing:', Object.keys(mergedContext).length, 'terms');
      
      this.jsonldProcessor.resolvedContext = mergedContext; // Use full context for processing
      this.referenceManager.setResolvedContext(mergedContext); // Use full context for reference resolution
      this.jsonRenderer.setOriginalContext(this.originalContext);
      console.log('📝 Using first context with', Object.keys(this.resolvedContext).length, 'terms for display');
      
      // Step 4: Index all entities
      await this.jsonldProcessor.indexAllEntities(this.documentLoader.loadedDocuments);
      
      // Step 5: Process and display
      this.currentProcessedData = await this.processData();
      this.displayResult(this.currentProcessedData);
      
    } catch (error) {
      this.uiManager.showError(`Failed to load data: ${error.message}`);
    } finally {
      this.uiManager.showLoading(false);
    }
  }

  async loadLinkedDocuments(data, baseUrl, depth) {
    if (depth <= 0) return;

    const followLinks = document.getElementById('followLinks').checked;
    if (!followLinks) {
      console.log('🔗 Follow Links disabled - skipping linked document loading');
      return;
    }

    console.log(`🔗 Loading linked documents at depth ${depth}`);
    
    // First, expand the data to find all @id references
    let expandedData;
    try {
      expandedData = await this.jsonldProcessor.safeExpand(data);
      console.log('🔗 Expanded data for reference collection');
    } catch (error) {
      console.warn('⚠️ Could not expand data for reference collection:', error);
      expandedData = data;
    }
    
    // Collect all @id references from the expanded data
    const refs = new Set();
    this.collectExpandedReferences(expandedData, refs);
    
    // Also collect from original data using the reference manager
    const originalRefs = this.referenceManager.collectIdReferences(data);
    originalRefs.forEach(ref => refs.add(ref));
    
    console.log(`🔗 Found ${refs.size} total references to load`);
    if (refs.size > 0) {
      console.log('🔗 References:', Array.from(refs));
    }
    
    const loadedUrls = new Set();
    
    for (const ref of refs) {
      let resolvedRef = Utils.resolvePrefix(ref, CONFIG.prefixMapping);
      
      if (!resolvedRef.startsWith('http')) {
        resolvedRef = Utils.resolveUrl(resolvedRef, baseUrl);
      }

      if (loadedUrls.has(resolvedRef)) continue;
      loadedUrls.add(resolvedRef);

      try {
        console.log(`🔗 Loading linked document: ${resolvedRef}`);
        const linkedDoc = await this.documentLoader.fetchDocument(resolvedRef);
        
        if (depth > 1 && linkedDoc) {
          await this.loadLinkedDocuments(linkedDoc, resolvedRef, depth - 1);
        }
      } catch (error) {
        console.warn(`Could not load linked document ${resolvedRef}:`, error.message);
      }
    }
  }

  // Collect @id references from expanded JSON-LD data
  collectExpandedReferences(data, refs, visited = new Set()) {
    if (!data || visited.has(data)) return;
    
    if (typeof data === 'object') {
      visited.add(data);
      
      if (Array.isArray(data)) {
        data.forEach(item => this.collectExpandedReferences(item, refs, visited));
      } else {
        // Check for @id values
        if (data['@id'] && typeof data['@id'] === 'string') {
          // Only add if this looks like a reference we should load
          if (Object.keys(data).length === 1 || 
              (Object.keys(data).length === 2 && data['@type'])) {
            refs.add(data['@id']);
          }
        }
        
        // Recursively check all values
        Object.values(data).forEach(value => {
          this.collectExpandedReferences(value, refs, visited);
        });
      }
      
      visited.delete(data);
    }
  }

  async processData() {
    if (!this.currentRawData) return null;

    console.log('🔄 === PROCESSING DATA ===');
    console.log('📋 isExpanded:', this.isExpanded);
    console.log('📋 Insert Context:', document.getElementById('insertContext').checked);
    console.log('📋 Follow Links:', document.getElementById('followLinks').checked);

    try {
      // Step 1: Always start with jsonld.expand to get normalized data
      console.log('🔄 Step 1: Running jsonld.expand on raw data...');
      let expandedData;
      try {
        expandedData = await this.jsonldProcessor.safeExpand(this.currentRawData);
        console.log('✅ Initial expansion complete, got', expandedData.length, 'items');
      } catch (expandError) {
        console.error('❌ Failed to expand data:', expandError);
        // If expansion fails completely, return the raw data
        this.uiManager.showError(`JSON-LD expansion failed: ${expandError.message}`);
        return this.currentRawData;
      }
      
      // Step 2: Find all links that need expansion
      console.log('🔄 Step 2: Finding links to expand...');
      const followLinks = document.getElementById('followLinks').checked;
      const depth = parseInt(document.getElementById('depth').value) || 2;
      
      let linksToExpand = new Set();
      if (followLinks && depth > 0) {
        linksToExpand = this.findLinksToExpand(expandedData);
        console.log('🔗 Found', linksToExpand.size, 'unique links to expand:', Array.from(linksToExpand));
      } else {
        console.log('🔗 Link following disabled or depth is 0');
      }
      
      // Step 3: Expand the links and build substitution map
      console.log('🔄 Step 3: Expanding linked documents...');
      const substitutionMap = new Map();
      
      for (const link of linksToExpand) {
        try {
          // Check if we already have this document loaded
          let linkedDoc = null;
          
          // Try to get from loaded documents
          for (const [url, doc] of this.documentLoader.loadedDocuments) {
            if (url === link || (doc['@id'] && doc['@id'] === link)) {
              linkedDoc = doc;
              break;
            }
          }
          
          // If not found, try to load it
          if (!linkedDoc && link.startsWith('http')) {
            try {
              linkedDoc = await this.documentLoader.fetchDocument(link);
            } catch (e) {
              console.warn(`Could not fetch ${link}:`, e.message);
            }
          }
          
          if (linkedDoc) {
            // Expand the linked document
            const expandedLinkedDoc = await this.jsonldProcessor.safeExpand(linkedDoc);
            if (expandedLinkedDoc && expandedLinkedDoc.length > 0) {
              // Find the entity with matching @id
              const entity = expandedLinkedDoc.find(item => item['@id'] === link) || expandedLinkedDoc[0];
              if (entity) {
                substitutionMap.set(link, entity);
                console.log(`✅ Expanded link: ${link}`);
              }
            }
          }
        } catch (error) {
          console.warn(`Failed to expand link ${link}:`, error.message);
        }
      }
      
      console.log('📦 Built substitution map with', substitutionMap.size, 'expanded entities');
      
      // Step 4: Substitute expanded links into the expanded data
      console.log('🔄 Step 4: Substituting expanded links...');
      let substitutedData = expandedData;
      if (substitutionMap.size > 0) {
        substitutedData = this.substituteLinks(expandedData, substitutionMap, 0, depth);
      }
      console.log('✅ Substitution complete');
      
      // Step 5: Return appropriate format
      if (this.isExpanded) {
        console.log('📋 Returning expanded view (jsonld.expand output)');
        
        // For expanded view, we already have the expanded data with substitutions
        // The expanded view should NOT have context - it's fully expanded
        // Only add context if explicitly requested
        const insertContext = document.getElementById('insertContext').checked;
        if (insertContext && this.originalContext) {
          console.log('📝 Adding context to expanded view (unusual but requested)');
          // Wrap in a container with context
          if (Array.isArray(substitutedData) && substitutedData.length > 0) {
            return {
              '@context': this.originalContext,
              '@graph': substitutedData
            };
          }
        }
        
        // Normal expanded view - just return the expanded data
        return substitutedData;
      } else {
        // For compacted view, use jsonld.compact on the substituted expanded data
        console.log('🔄 Step 5: Creating compacted view using jsonld.compact...');
        
        // Determine which context to use for compaction
        let compactionContext = {};
        
        // Priority: resolved context > original context > empty context
        if (this.resolvedContext && Object.keys(this.resolvedContext).length > 0) {
          compactionContext = this.resolvedContext;
          console.log('📝 Using resolved context for compaction:', Object.keys(compactionContext).length, 'terms');
        } else if (this.originalContext) {
          // Use the first context if it's an array
          compactionContext = Array.isArray(this.originalContext) ? this.originalContext[0] : this.originalContext;
          console.log('📝 Using original context for compaction');
        } else {
          console.log('⚠️ No context available for compaction');
        }
        
        console.log('🔄 Running jsonld.compact with expanded+substituted data...');
        let compactedData;
        try {
          compactedData = await this.jsonldProcessor.safeCompact(substitutedData, compactionContext);
          console.log('✅ Compaction complete');
        } catch (compactError) {
          console.error('❌ Compaction failed:', compactError);
          // Fall back to expanded data if compaction fails
          this.uiManager.showError(`JSON-LD compaction failed: ${compactError.message}`);
          return substitutedData;
        }
        
        // Handle context insertion/removal based on checkbox
        const insertContext = document.getElementById('insertContext').checked;
        if (!insertContext && compactedData['@context']) {
          // Remove context if checkbox is unchecked
          console.log('📝 Removing context from compacted view (Insert Context unchecked)');
          const { '@context': _, ...dataWithoutContext } = compactedData;
          compactedData = dataWithoutContext;
        } else if (insertContext && !compactedData['@context']) {
          // Add context if checkbox is checked but no context present
          console.log('📝 Adding context to compacted view (Insert Context checked)');
          compactedData = {
            '@context': compactionContext,
            ...compactedData
          };
        }
        
        return compactedData;
      }
    } catch (error) {
      console.error('❌ Data processing failed:', error);
      return this.currentRawData;
    }
  }
  
  // Find all links that need expansion in the expanded data
  findLinksToExpand(data, links = new Set(), visited = new Set()) {
    if (!data || visited.has(data)) return links;
    
    if (typeof data === 'object') {
      visited.add(data);
      
      if (Array.isArray(data)) {
        data.forEach(item => this.findLinksToExpand(item, links, visited));
      } else {
        // Check each property value
        Object.entries(data).forEach(([key, value]) => {
          // Check if this is a link reference (object with only @id)
          if (typeof value === 'object' && value !== null && !Array.isArray(value) &&
              Object.keys(value).length === 1 && value['@id'] && typeof value['@id'] === 'string') {
            links.add(value['@id']);
          } else if (Array.isArray(value)) {
            // Check array items for link references
            value.forEach(item => {
              if (typeof item === 'object' && item !== null && !Array.isArray(item) &&
                  Object.keys(item).length === 1 && item['@id'] && typeof item['@id'] === 'string') {
                links.add(item['@id']);
              } else {
                this.findLinksToExpand(item, links, visited);
              }
            });
          } else {
            this.findLinksToExpand(value, links, visited);
          }
        });
      }
      
      visited.delete(data);
    }
    
    return links;
  }
  
  // Substitute expanded links in the data
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
            // Recursively substitute in the substituted entity (but increase depth)
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

  async updateView() {
    if (!this.currentRawData) {
      console.log('⚠️  No raw data available for view update');
      return;
    }

    console.log('🔄 === UPDATING VIEW ===');

    const toggleContainer = document.querySelector('.result-header');
    if (toggleContainer) {
      toggleContainer.style.opacity = '0.6';
    }

    try {
      this.jsonRenderer.clearHiddenFields();
      this.currentProcessedData = await this.processData();
      this.displayResult(this.currentProcessedData);
      
      console.log('✅ === VIEW UPDATE COMPLETE ===');
    } catch (error) {
      console.error('❌ Failed to update view:', error);
      this.uiManager.showError(`Failed to update view: ${error.message}`);
    } finally {
      if (toggleContainer) {
        toggleContainer.style.opacity = '1';
      }
    }
  }

  displayResult(data) {
    const resultSection = document.getElementById('resultSection');
    const statsElement = document.getElementById('resultStats');
    const jsonViewer = document.getElementById('jsonViewer');
    const viewToggle = document.getElementById('viewToggle');
    
    if (!resultSection || !jsonViewer) {
      console.error('Required DOM elements not found:', { resultSection, jsonViewer });
      return;
    }
    
    if (viewToggle) {
      viewToggle.checked = this.isExpanded;
    }
    
    // Calculate statistics
    const displayData = this.jsonRenderer.filterHiddenFields(data);
    console.log('📋 Data structure:', {
      isArray: Array.isArray(data),
      hasGraph: data['@graph'] !== undefined,
      topLevelKeys: Object.keys(data),
      sampleData: JSON.stringify(data, null, 2).substring(0, 500) + '...'
    });
    const jsonString = JSON.stringify(displayData, null, 2);
    const lines = jsonString.split('\n').length;
    const size = new Blob([jsonString]).size;
    const loadedUrls = this.documentLoader.loadedDocuments.size;
    const indexedEntities = this.jsonldProcessor.entityIndex.size;
    const contextKeys = Object.keys(this.resolvedContext).length;
    const contextDocs = this.documentLoader.contextDocuments.size;
    
    const viewMode = this.isExpanded ? 
      '🔄 EXPANDED VIEW: jsonld.expand output (absolute URIs, no context)' : 
      '📄 COMPACTED VIEW: jsonld.compact output (human-readable with context)';
    
    if (statsElement) {
      statsElement.textContent = `${viewMode} • ${lines} lines • ${Utils.formatBytes(size)} • ${loadedUrls} documents • ${indexedEntities} entities • ${contextKeys} context terms • ${contextDocs} context docs`;
    } else {
      console.error('Stats element not found');
    }
    
    // Create field toggles - pass the processed data for field detection
    console.log('📋 Creating field toggles, data keys:', Object.keys(data));
    this.uiManager.createFieldToggles(data, this.resolvedContext);
    
    // Render JSON
    if (jsonViewer) {
      this.jsonRenderer.renderJson(displayData, jsonViewer);
    }
    
    if (resultSection) {
      resultSection.style.display = 'block';
      resultSection.scrollIntoView({ behavior: 'smooth' });
    }
  }

  // UI callback handlers
  rerenderDisplay() {
    if (this.currentProcessedData) {
      const jsonViewer = document.getElementById('jsonViewer');
      const displayData = this.jsonRenderer.filterHiddenFields(this.currentProcessedData);
      this.jsonRenderer.renderJson(displayData, jsonViewer);
    }
  }

  handleFieldExpansion(field, expand) {
    if (!this.currentProcessedData) return;
    
    if (expand) {
      // Force expand field logic would go here
      console.log(`🔗 Force expanding field: ${field}`);
    } else {
      // Revert expansion
      console.log(`🔗 Reverting field expansion: ${field}`);
    }
    
    this.rerenderDisplay();
  }
  
  // Build resolved context from original file only - use FIRST context
  async buildResolvedContextFromOriginal(originalContext, baseUrl) {
    const result = {};
    
    // Only process the original context, not contexts from linked documents
    if (!originalContext) return result;
    
    // Get the FIRST context only
    let firstContext = originalContext;
    if (Array.isArray(originalContext) && originalContext.length > 0) {
      firstContext = originalContext[0];
    }
    
    if (typeof firstContext === 'string') {
      // First context is a URL - load only this specific context
      try {
        const contextDoc = await this.documentLoader.fetchDocument(firstContext);
        if (contextDoc && contextDoc['@context']) {
          // Use the context directly, don't merge or process further
          if (typeof contextDoc['@context'] === 'object' && !Array.isArray(contextDoc['@context'])) {
            return contextDoc['@context'];
          } else {
            return this.extractContextTerms(contextDoc['@context']);
          }
        }
      } catch (e) {
        console.warn(`Could not load first context from: ${firstContext}`, e);
      }
    } else if (typeof firstContext === 'object' && firstContext !== null) {
      // First context is a direct object - use it as is
      return firstContext;
    }
    
    return result;
  }
  
  // Extract context terms from a context object
  extractContextTerms(context) {
    const terms = {};
    if (typeof context === 'object' && context !== null && !Array.isArray(context)) {
      Object.assign(terms, context);
    } else if (Array.isArray(context)) {
      for (const ctx of context) {
        if (typeof ctx === 'object' && ctx !== null) {
          Object.assign(terms, ctx);
        }
      }
    }
    return terms;
  }

  // Extract base URL from context
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
      
      // Also check for base URL patterns in context values
      for (const [key, value] of Object.entries(context)) {
        if (typeof value === 'string' && value.startsWith('http') && value.endsWith('/')) {
          // This might be a base URL
          console.log(`🔍 Found potential base URL in context['${key}']: ${value}`);
        }
      }
    }
    
    return null;
  }

  // Export functions
  async copyToClipboard() {
    if (!this.currentProcessedData) return;
    
    try {
      const displayData = this.jsonRenderer.filterHiddenFields(this.currentProcessedData);
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
    const displayData = this.jsonRenderer.filterHiddenFields(this.currentProcessedData);
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
    if (!this.currentProcessedData) return;
    
    const displayData = this.jsonRenderer.filterHiddenFields(this.currentProcessedData);
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
    this.documentLoader.clear();
    this.jsonldProcessor.clear();
    this.currentRawData = null;
    this.currentProcessedData = null;
    this.resolvedContext = {};
    this.originalContext = null;
    this.jsonRenderer.setOriginalContext(null);
  }

  // Ensure linked fields are present and resolved in compacted data
  ensureLinkedFieldsPresent(compactedData, expandedData) {
    if (!this.referenceManager.linkProperties || this.referenceManager.linkProperties.size === 0) {
      return compactedData;
    }

    console.log('🔗 Resolving linked fields in compacted data');
    
    // Helper function to resolve and add linked fields to an object
    const resolveLinkedFieldsInObject = (obj) => {
      if (typeof obj !== 'object' || obj === null || Array.isArray(obj)) {
        return obj;
      }
      
      const result = { ...obj };
      
      // For each linked property defined in the context
      for (const linkedProp of this.referenceManager.linkProperties) {
        // Check if this property exists and needs resolution
        if (result[linkedProp] !== undefined) {
          const value = result[linkedProp];
          
          if (typeof value === 'string') {
            // Single reference - resolve it
            const resolvedEntity = this.resolveLinkedReference(value);
            if (resolvedEntity) {
              console.log(`🔗 Resolved linked field '${linkedProp}': ${value}`);
              result[linkedProp] = resolvedEntity;
            }
          } else if (Array.isArray(value)) {
            // Array of references - resolve each
            const resolved = value.map(item => {
              if (typeof item === 'string') {
                const resolvedEntity = this.resolveLinkedReference(item);
                return resolvedEntity || item;
              }
              return item;
            });
            console.log(`🔗 Resolved linked field array '${linkedProp}':`, value);
            result[linkedProp] = resolved;
          } else if (typeof value === 'object' && value['@id']) {
            // Object with @id - resolve it
            const resolvedEntity = this.resolveLinkedReference(value['@id']);
            if (resolvedEntity) {
              console.log(`🔗 Resolved linked field object '${linkedProp}': ${value['@id']}`);
              result[linkedProp] = { ...resolvedEntity, ...value };
            }
          }
        } else {
          // Field is missing - try to find it in the original data
          const originalValue = this.findOriginalLinkedValue(obj, linkedProp);
          if (originalValue !== undefined) {
            // Resolve the original value
            if (typeof originalValue === 'string') {
              const resolvedEntity = this.resolveLinkedReference(originalValue);
              if (resolvedEntity) {
                console.log(`🔗 Added and resolved missing linked field '${linkedProp}': ${originalValue}`);
                result[linkedProp] = resolvedEntity;
              } else {
                result[linkedProp] = originalValue;
              }
            } else if (Array.isArray(originalValue)) {
              const resolved = originalValue.map(item => {
                if (typeof item === 'string') {
                  const resolvedEntity = this.resolveLinkedReference(item);
                  return resolvedEntity || item;
                }
                return item;
              });
              console.log(`🔗 Added and resolved missing linked field array '${linkedProp}'`);
              result[linkedProp] = resolved;
            } else {
              result[linkedProp] = originalValue;
            }
          }
        }
      }
      
      return result;
    };
    
    // Process the data structure
    if (Array.isArray(compactedData)) {
      return compactedData.map(item => resolveLinkedFieldsInObject(item));
    } else if (compactedData['@graph'] && Array.isArray(compactedData['@graph'])) {
      return {
        ...compactedData,
        '@graph': compactedData['@graph'].map(item => resolveLinkedFieldsInObject(item))
      };
    } else {
      return resolveLinkedFieldsInObject(compactedData);
    }
  }

  // Resolve a linked reference to its full entity data
  resolveLinkedReference(reference) {
    if (!reference || typeof reference !== 'string') {
      return null;
    }
    
    // Try to get from the entity index
    const entity = this.jsonldProcessor.getEntityFromIndex(reference, CONFIG.prefixMapping);
    if (entity) {
      // Return a compacted version of the entity
      const compacted = this.compactEntity(entity);
      return compacted;
    }
    
    // Try to resolve the reference
    const resolvedRef = Utils.resolvePrefix(reference, CONFIG.prefixMapping);
    
    // Check if we have this document loaded
    if (this.documentLoader.loadedDocuments.has(resolvedRef)) {
      const doc = this.documentLoader.loadedDocuments.get(resolvedRef);
      return this.compactEntity(doc);
    }
    
    console.warn(`⚠️ Could not resolve linked reference: ${reference}`);
    return null;
  }

  // Compact an entity for display
  compactEntity(entity) {
    if (!entity) return null;
    
    // If it's already compacted, return as is
    if (!Array.isArray(entity) && !entity['@type'] && entity.type) {
      return entity;
    }
    
    // Simple compaction - just use the context mapping
    const compacted = {};
    
    for (const [key, value] of Object.entries(entity)) {
      // Find the compact form of the key
      let compactKey = key;
      
      // Check if this is an expanded URI that maps to a compact name
      if (this.referenceManager.expandedToCompactMap && 
          this.referenceManager.expandedToCompactMap.has(key)) {
        compactKey = this.referenceManager.expandedToCompactMap.get(key);
      } else if (key === '@type') {
        compactKey = 'type';
      } else if (key === '@id') {
        compactKey = 'id';
      }
      
      // Don't include @context in the compacted entity
      if (key !== '@context') {
        compacted[compactKey] = value;
      }
    }
    
    return compacted;
  }

  // Find the original object from raw data
  findOriginalObject(obj) {
    const objId = obj['@id'] || obj['id'];
    if (!objId || !this.currentRawData) {
      return null;
    }
    
    const findInData = (data, id) => {
      if (typeof data !== 'object' || data === null) {
        return null;
      }
      
      if (Array.isArray(data)) {
        for (const item of data) {
          const found = findInData(item, id);
          if (found) return found;
        }
      } else {
        // Check if this is the object we're looking for
        if (data['@id'] === id || data['id'] === id) {
          return data;
        }
        
        // Search in @graph
        if (data['@graph']) {
          const found = findInData(data['@graph'], id);
          if (found) return found;
        }
        
        // Search in other properties
        for (const value of Object.values(data)) {
          if (typeof value === 'object') {
            const found = findInData(value, id);
            if (found) return found;
          }
        }
      }
      
      return null;
    };
    
    return findInData(this.currentRawData, objId);
  }

  // Find the original linked value for an object
  findOriginalLinkedValue(obj, linkedProp) {
    // Get the object's ID to find it in the original data
    const objId = obj['@id'] || obj['id'];
    
    if (!objId || !this.currentRawData) {
      return undefined;
    }
    
    // Search for this object in the original data
    const findInData = (data, id) => {
      if (typeof data !== 'object' || data === null) {
        return undefined;
      }
      
      if (Array.isArray(data)) {
        for (const item of data) {
          const found = findInData(item, id);
          if (found !== undefined) return found;
        }
      } else {
        // Check if this is the object we're looking for
        if ((data['@id'] === id || data['id'] === id) && data[linkedProp] !== undefined) {
          return data[linkedProp];
        }
        
        // Search in @graph
        if (data['@graph']) {
          return findInData(data['@graph'], id);
        }
        
        // Search in other properties
        for (const value of Object.values(data)) {
          if (typeof value === 'object') {
            const found = findInData(value, id);
            if (found !== undefined) return found;
          }
        }
      }
      
      return undefined;
    };
    
    return findInData(this.currentRawData, objId);
  }
}

// Initialize the viewer when the page loads
document.addEventListener('DOMContentLoaded', () => {
  new CMIPLDViewer();
});
