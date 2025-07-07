// Inline Document Loading Manager - handles loading documents for inline display
export class InlineDocumentManager {
  constructor(documentLoader, contextResolutionManager, jsonldProcessor, jsonRenderer, referenceManager) {
    this.documentLoader = documentLoader;
    this.contextResolutionManager = contextResolutionManager;
    this.jsonldProcessor = jsonldProcessor;
    this.jsonRenderer = jsonRenderer;
    this.referenceManager = referenceManager;
    this.loadedDocuments = new Map(); // Cache for loaded documents
  }

  // Load and render a document inline
  async loadDocumentInline(url, container, depth, followLinks = true, insertContext = false, isExpanded = false) {
    console.log(`📥 Loading document inline: ${url} at depth ${depth}`);
    
    try {
      // Check cache first
      if (this.loadedDocuments.has(url)) {
        console.log(`📋 Using cached document: ${url}`);
        const cachedDoc = this.loadedDocuments.get(url);
        await this.renderInlineDocument(cachedDoc, container, depth, followLinks, insertContext, isExpanded);
        return;
      }
      
      // Load the document
      const rawData = await this.documentLoader.fetchDocument(url);
      console.log(`✅ Fetched inline document: ${url}`, Object.keys(rawData));
      
      // Resolve context for the document
      const resolvedContext = await this.contextResolutionManager.buildResolvedContext(rawData, url);
      console.log(`✅ Resolved context for inline document: ${url} with ${Object.keys(resolvedContext).length} terms`);
      
      // Expand the document
      const originalContext = this.jsonldProcessor.resolvedContext;
      this.jsonldProcessor.resolvedContext = resolvedContext;
      
      let expandedData;
      try {
        expandedData = await this.jsonldProcessor.safeExpand(rawData);
      } catch (expandError) {
        console.warn(`⚠️ JSON-LD expansion failed for inline document ${url}, using manual expansion:`, expandError.message);
        expandedData = this.jsonldProcessor.createManualExpansion(rawData, url);
      }
      
      // Restore original context
      this.jsonldProcessor.resolvedContext = originalContext;
      
      // Store in cache
      const documentData = {
        raw: rawData,
        expanded: expandedData,
        compacted: null,
        context: rawData['@context'] || null,
        resolvedContext: resolvedContext,
        url: url
      };
      
      this.loadedDocuments.set(url, documentData);
      
      // Render the document
      await this.renderInlineDocument(documentData, container, depth, followLinks, insertContext, isExpanded);
      
    } catch (error) {
      console.error(`❌ Failed to load inline document ${url}:`, error);
      container.innerHTML = `<span style="color: #d32f2f;">Failed to load document: ${error.message}</span>`;
    }
  }

  // Render the loaded document inline
  async renderInlineDocument(documentData, container, depth, followLinks, insertContext, isExpanded) {
    console.log(`🎨 Rendering inline document: ${documentData.url} (expanded: ${isExpanded})`);
    
    // Set up temporary reference manager context
    const originalResolvedContext = this.referenceManager.resolvedContext;
    this.referenceManager.setResolvedContext(documentData.resolvedContext);
    
    try {
      let viewData;
      
      if (isExpanded) {
        // Use expanded view
        viewData = documentData.expanded;
      } else {
        // Create compacted view
        if (!documentData.compacted) {
          // Try to compact the document
          try {
            if (Object.keys(documentData.resolvedContext).length > 0) {
              const compactedView = await this.jsonldProcessor.safeCompact(documentData.expanded, documentData.resolvedContext);
              documentData.compacted = compactedView;
            } else {
              documentData.compacted = documentData.raw;
            }
          } catch (compactError) {
            console.warn(`⚠️ Compaction failed for inline document, using raw data:`, compactError.message);
            documentData.compacted = documentData.raw;
          }
        }
        viewData = documentData.compacted;
      }
      
      // Apply context insertion
      if (insertContext && isExpanded && documentData.context) {
        if (Array.isArray(viewData)) {
          viewData = {
            '@context': documentData.context,
            '@graph': viewData
          };
        } else {
          viewData = {
            '@context': documentData.context,
            '@graph': [viewData]
          };
        }
      } else if (!insertContext && !isExpanded && viewData['@context']) {
        const { '@context': _, ...dataWithoutContext } = viewData;
        viewData = dataWithoutContext;
      }
      
      // Configure JSON renderer for inline loading
      const originalInlineCallback = this.jsonRenderer.inlineLoadCallback;
      const originalMaxDepth = this.jsonRenderer.maxDepth;
      
      // Set up inline loading callback if followLinks is enabled and we haven't reached max depth
      if (followLinks) {
        this.jsonRenderer.setMaxDepth(3); // Reasonable default for inline loading
        this.jsonRenderer.setInlineLoadCallback(async (url, targetContainer, newDepth) => {
          await this.loadDocumentInline(url, targetContainer, newDepth, followLinks, insertContext, isExpanded);
        });
      } else {
        this.jsonRenderer.setInlineLoadCallback(null);
      }
      
      // Render the document
      this.jsonRenderer.renderJson(viewData, container, 0, depth);
      
      // Restore original settings  
      this.jsonRenderer.setInlineLoadCallback(originalInlineCallback);
      this.jsonRenderer.setMaxDepth(originalMaxDepth);
      
    } finally {
      // Restore original reference manager context
      this.referenceManager.setResolvedContext(originalResolvedContext);
    }
  }

  // Clear the document cache
  clearCache() {
    this.loadedDocuments.clear();
  }

  // Get document from cache
  getCachedDocument(url) {
    return this.loadedDocuments.get(url);
  }

  // Check if document is cached
  isDocumentCached(url) {
    return this.loadedDocuments.has(url);
  }
}
