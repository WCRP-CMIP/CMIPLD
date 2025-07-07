// Data Loading Manager - handles the complex data loading workflow
// UPDATED: Remove depth parameter, use substituteLinkedFiles toggle
import { Utils } from '../utils.js';
import { CONFIG } from '../config.js';

export class DataLoadingManager {
  constructor(stateManager, documentLoader, contextResolutionManager, jsonldProcessor, linkedDocumentManager, jsonldValidator = null) {
    this.stateManager = stateManager;
    this.documentLoader = documentLoader;
    this.contextResolutionManager = contextResolutionManager;
    this.jsonldProcessor = jsonldProcessor;
    this.linkedDocumentManager = linkedDocumentManager;
    this.jsonldValidator = jsonldValidator;
  }

  // Execute the complete data loading workflow
  // UPDATED: Simplified parameters - removed depth, use substituteLinkedFiles
  async loadData(uri, substituteLinkedFiles) {
    // Step 1: Resolve prefix and get the URL
    const resolvedUri = Utils.resolvePrefix(uri, CONFIG.prefixMapping);
    this.stateManager.setMainDocumentUrl(resolvedUri);
    console.log('📍 Step 1: Resolved URI:', resolvedUri);
    
    // Step 2: Fetch and validate main document
    console.log('📥 Step 2: Fetching and validating main document...');
    let rawData = await this.documentLoader.fetchDocument(resolvedUri);
    console.log('✅ Fetched main document, keys:', Object.keys(rawData));
    
    // Validate and fix JSON-LD issues
    if (this.jsonldValidator) {
      const validationResult = this.jsonldValidator.validateAndFix(rawData, {
        fix: true,
        logErrors: true
      });
      
      if (!validationResult.isValid) {
        console.warn(`⚠️ Found ${validationResult.errors.length} validation issues in main document`);
        if (validationResult.fixes.length > 0) {
          console.log(`🔧 Applied ${validationResult.fixes.length} fixes to main document`);
          rawData = validationResult.document;
        }
      }
    }
    
    // Step 3: Resolve context for main document
    console.log('🔄 Step 3: Resolving and storing context with property-specific contexts...');
    const resolvedContext = await this.contextResolutionManager.buildResolvedContext(rawData, resolvedUri);
    
    // Update the JSON-LD processor with the resolved context
    this.jsonldProcessor.resolvedContext = resolvedContext;
    
    // Step 4: Expand the main document
    console.log('📋 Step 4: Expanding main document...');
    const expandedData = await this.jsonldProcessor.safeExpand(rawData);
    console.log('✅ Expanded main document, got', expandedData.length, 'items');
    
    // Step 5: Store the main document
    this.stateManager.storeDocument(resolvedUri, {
      raw: rawData,
      expanded: expandedData,
      compacted: null, // Will be computed on demand
      context: rawData['@context'] || null,
      resolvedContext: resolvedContext,
      isMain: true,
      url: resolvedUri
    });
    
    // Step 6: Load linked documents if substitution is enabled
    if (substituteLinkedFiles) {
      await this.loadLinkedDocuments(expandedData, rawData['@context'], resolvedUri);
    } else {
      console.log('🚫 Link substitution disabled, skipping linked document loading');
    }
    
    // Step 7: Build merged context and update references
    await this.finalizeContextAndReferences();
    
    return resolvedUri;
  }

  // Load linked documents with error handling
  // UPDATED: Removed depth parameter, simplified
  async loadLinkedDocuments(expandedData, context, resolvedUri) {
    console.log('🔗 Step 6: Finding and loading linked files from context and expanded data...');
    try {
      await this.linkedDocumentManager.loadLinkedDocuments(
        expandedData, 
        context, 
        resolvedUri, 
        this.stateManager.getAllDocuments()
      );
    } catch (linkError) {
      console.warn('⚠️ Some linked documents could not be loaded:', linkError.message);
      // Continue processing even if some linked documents fail
    }
  }

  // Finalize context resolution and reference management
  async finalizeContextAndReferences() {
    console.log('🔄 Step 7: Finalizing context and references...');
    
    // Build merged context from all loaded documents
    const mergedContext = await this.contextResolutionManager.buildMergedContext(this.stateManager.getAllDocuments());
    this.stateManager.setMergedContext(mergedContext);
    
    // Update the JSON-LD processor with the merged context for operations that use it
    this.jsonldProcessor.resolvedContext = mergedContext;
    
    console.log('✅ Finalized context with', Object.keys(mergedContext).length, 'terms');
  }

  // Validate input parameters
  validateInput(uri) {
    if (!uri || uri.trim() === '') {
      throw new Error('Please enter a URI or prefix');
    }
    return uri.trim();
  }

  // Extract form parameters
  // UPDATED: Use substituteLinkedFiles instead of depth and followLinks
  extractFormParameters() {
    const uri = document.getElementById('uri')?.value || '';
    const substituteLinkedFiles = document.getElementById('substituteLinkedFiles')?.checked || false;
    
    return { uri, substituteLinkedFiles };
  }
}