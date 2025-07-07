// View Manager - handles creation of expanded and compacted views with auto-substitution
import { Utils } from './utils.js';

export class ViewManager {
  constructor(jsonldProcessor, contextResolutionManager, autoSubstitutionManager) {
    this.jsonldProcessor = jsonldProcessor;
    this.contextResolutionManager = contextResolutionManager;
    this.autoSubstitutionManager = autoSubstitutionManager;
  }

  // Create expanded view with auto-substitution of linked content
  async createExpandedView(mainDoc, documents, followLinks, linkedDocumentManager) {
    console.log('🔄 Creating expanded view with auto-substitution...');
    console.log('📋 Main doc expanded:', mainDoc.expanded);
    console.log('📋 Main doc resolved context:', mainDoc.resolvedContext);
    
    // Use the document's properly resolved context for expansion if needed
    if (mainDoc.resolvedContext && Object.keys(mainDoc.resolvedContext).length > 0) {
      this.jsonldProcessor.resolvedContext = mainDoc.resolvedContext;
    }
    
    // Start with the expanded main document
    let expandedView = Utils.deepClone(mainDoc.expanded);
    
    // If the expanded view is empty or doesn't contain meaningful data, 
    // fall back to using the raw document with proper context
    if (!expandedView || expandedView.length === 0 || 
        (Array.isArray(expandedView) && expandedView.every(item => !item || Object.keys(item).length === 0))) {
      console.warn('⚠️ Expanded view is empty, re-expanding raw document with resolved context');
      
      // Set the resolved context and re-expand
      if (mainDoc.resolvedContext) {
        this.jsonldProcessor.resolvedContext = mainDoc.resolvedContext;
      }
      
      expandedView = this.jsonldProcessor.createManualExpansion(mainDoc.raw, mainDoc.url || 'unknown');
      
      // Update the stored expanded data
      mainDoc.expanded = expandedView;
    }
    
    console.log('📋 Expanded view after context check:', expandedView);
    
    if (!followLinks) {
      return expandedView;
    }
    
    // Auto-substitute linked content instead of just creating substitution map
    console.log('🔄 Auto-substituting linked content...');
    try {
      const substitutedView = await this.autoSubstitutionManager.autoSubstituteLinkedEntries(
        expandedView, 
        mainDoc.url || 'unknown',
        0 // Start at depth 0
      );
      
      console.log('✅ Auto-substitution completed');
      return substitutedView;
    } catch (substitutionError) {
      console.warn('⚠️ Auto-substitution failed, falling back to original view:', substitutionError.message);
      return expandedView;
    }
  }

  // Create compacted view with auto-substitution of linked content
  async createCompactedView(mainDoc, documents, followLinks, mergedContext, linkedDocumentManager) {
    console.log('🔄 Creating compacted view with auto-substitution...');
    console.log('📋 Main doc resolved context:', mainDoc.resolvedContext);
    
    if (followLinks) {
      // When following links, we need to compact the expanded view first, then apply substitution
      console.log('🔄 Creating compacted view with auto-substituted linked entities...');
      
      // First get the expanded view WITHOUT auto-substitution to avoid double processing
      const expandedView = await this.createExpandedView(mainDoc, documents, false, linkedDocumentManager);
      
      // Create a comprehensive compaction context that includes property-scoped contexts
      const compactionContext = this.contextResolutionManager.buildCompactionContextWithPropertyScopes(mainDoc.resolvedContext, mergedContext);
      console.log('📋 Using comprehensive compaction context with', Object.keys(compactionContext).length, 'terms');
      
      let compactedView;
      if (Object.keys(compactionContext).length > 0) {
        try {
          // Set the processor context
          this.jsonldProcessor.resolvedContext = compactionContext;
          
          compactedView = await this.jsonldProcessor.safeCompact(expandedView, compactionContext);
          console.log('✅ JSON-LD compaction successful');
        } catch (compactError) {
          console.warn('⚠️ JSON-LD compaction failed:', compactError.message);
          compactedView = expandedView; // Fallback to expanded view
        }
      } else {
        compactedView = expandedView; // Fallback if no context
      }
      
      // Store the compacted version (before substitution)
      mainDoc.compacted = compactedView;
      
      // Note: Auto-substitution will be applied later in the workflow
      // This ensures substitutions happen AFTER compaction to preserve them
      return compactedView;
    } else {
      // Standard compaction without links (no auto-substitution needed)
      console.log('🔄 Creating standard compacted view (no links, no auto-substitution)...');
      
      // Create a compaction context that includes property-scoped contexts
      const compactionContext = this.contextResolutionManager.buildCompactionContextWithPropertyScopes(mainDoc.resolvedContext);
      
      console.log('📋 Using compaction context with', Object.keys(compactionContext).length, 'terms');
      
      // If we have a valid context and expanded data, try JSON-LD compaction
      if (Object.keys(compactionContext).length > 0 && mainDoc.expanded && mainDoc.expanded.length > 0) {
        console.log('🔄 Attempting JSON-LD compaction with comprehensive context');
        
        try {
          // Set the processor context
          this.jsonldProcessor.resolvedContext = compactionContext;
          
          const compactedView = await this.jsonldProcessor.safeCompact(mainDoc.expanded, compactionContext);
          console.log('✅ JSON-LD compaction successful:', compactedView);
          
          // Store the compacted version
          mainDoc.compacted = compactedView;
          return compactedView;
        } catch (compactError) {
          console.warn('⚠️ JSON-LD compaction failed:', compactError.message);
        }
      }
      
      // Fallback: Return the raw document for a more human-readable view
      console.log('📋 Using raw document as compacted view (no valid resolved context or expansion failed)');
      
      // Create a clean version of the raw document
      const rawCopy = Utils.deepClone(mainDoc.raw);
      
      // Store the compacted version
      mainDoc.compacted = rawCopy;
      return rawCopy;
    }
  }

  // Apply context insertion logic
  applyContextInsertion(viewData, insertContext, isExpanded, mainDocContext) {
    if (insertContext && isExpanded && mainDocContext) {
      // Add context to expanded view (unusual but supported)
      if (Array.isArray(viewData)) {
        viewData = {
          '@context': mainDocContext,
          '@graph': viewData
        };
      } else {
        // For non-array data, wrap it in a graph structure
        viewData = {
          '@context': mainDocContext,
          '@graph': [viewData]
        };
      }
    } else if (!insertContext && !isExpanded && viewData['@context']) {
      // Remove context from compacted view
      const { '@context': _, ...dataWithoutContext } = viewData;
      viewData = dataWithoutContext;
    }
    
    return viewData;
  }
}
