// Workflow Manager - coordinates complex multi-step operations
// UPDATED: Remove depth parameter, use substituteLinkedFiles toggle
export class WorkflowManager {
  constructor(dataLoadingManager, viewManager, displayManager, stateManager, uiManager, linkedDocumentManager, enhancedLinkSubstitution = null) {
    this.dataLoadingManager = dataLoadingManager;
    this.viewManager = viewManager;
    this.displayManager = displayManager;
    this.stateManager = stateManager;
    this.uiManager = uiManager;
    this.linkedDocumentManager = linkedDocumentManager;
    this.enhancedLinkSubstitution = enhancedLinkSubstitution;
  }

  // Execute the complete load and display workflow
  // UPDATED: Remove depth parameter, use substituteLinkedFiles
  async executeLoadAndDisplayWorkflow(uri, substituteLinkedFiles) {
    const workflow = new LoadAndDisplayWorkflow(
      this.dataLoadingManager,
      this.viewManager,
      this.displayManager,
      this.stateManager,
      this.uiManager,
      this.linkedDocumentManager,
      this.enhancedLinkSubstitution
    );
    
    return await workflow.execute(uri, substituteLinkedFiles);
  }

  // Execute view update workflow
  async executeViewUpdateWorkflow() {
    const workflow = new ViewUpdateWorkflow(
      this.viewManager,
      this.displayManager,
      this.stateManager,
      this.uiManager,
      this.linkedDocumentManager,
      this.enhancedLinkSubstitution
    );
    
    return await workflow.execute();
  }
}

// Specific workflow for loading and displaying data
class LoadAndDisplayWorkflow {
  constructor(dataLoadingManager, viewManager, displayManager, stateManager, uiManager, linkedDocumentManager, enhancedLinkSubstitution = null) {
    this.dataLoadingManager = dataLoadingManager;
    this.viewManager = viewManager;
    this.displayManager = displayManager;
    this.stateManager = stateManager;
    this.uiManager = uiManager;
    this.linkedDocumentManager = linkedDocumentManager;
    this.enhancedLinkSubstitution = enhancedLinkSubstitution;
  }

  // UPDATED: Use substituteLinkedFiles instead of depth and followLinks
  async execute(uri, substituteLinkedFiles) {
    try {
      // Phase 1: Load data
      console.log('🚀 Phase 1: Loading data...');
      await this.dataLoadingManager.loadData(uri, substituteLinkedFiles);
      
      // Phase 2: Create view
      console.log('🚀 Phase 2: Creating view...');
      const mainDoc = this.stateManager.getMainDocument();
      if (!mainDoc) {
        throw new Error('Main document not found after loading');
      }
      
      const viewData = await this.createViewData(mainDoc, substituteLinkedFiles);
      
      // Phase 3: Display results
      console.log('🚀 Phase 3: Displaying results...');
      this.stateManager.setCurrentViewData(viewData);
      await this.displayManager.displayResult(
        viewData, 
        this.stateManager.getExpanded(), 
        this.stateManager.getAllDocuments(), 
        this.stateManager.getMergedContext()
      );
      
      console.log('✅ Load and display workflow completed successfully');
      return true;
      
    } catch (error) {
      console.error('❌ Load and display workflow failed:', error);
      throw error;
    }
  }

  // UPDATED: Use substituteLinkedFiles parameter
  async createViewData(mainDoc, substituteLinkedFiles) {
    let viewData;
    
    if (this.stateManager.getExpanded()) {
      // For expanded view, create the view first then apply substitution
      viewData = await this.viewManager.createExpandedView(
        mainDoc, 
        this.stateManager.getAllDocuments(), 
        false, // Don't do auto-substitution here
        this.linkedDocumentManager
      );
    } else {
      // For compacted view, create the view first then apply substitution
      viewData = await this.viewManager.createCompactedView(
        mainDoc, 
        this.stateManager.getAllDocuments(), 
        false, // Don't do auto-substitution here
        this.stateManager.getMergedContext(),
        this.linkedDocumentManager
      );
    }
    
    // Apply enhanced link substitution BEFORE context insertion if enabled
    if (this.enhancedLinkSubstitution && substituteLinkedFiles) {
      console.log('🔄 Applying enhanced link substitution...');
      viewData = await this.enhancedLinkSubstitution.processDocumentWithSubstitution(viewData, {
        skipBrokenLinks: false,
        showProgress: true
      });
      console.log('✅ Enhanced link substitution completed');
    }
    
    // Apply context insertion after substitution
    const insertContext = document.getElementById('insertContext')?.checked || false;
    let finalViewData = this.viewManager.applyContextInsertion(
      viewData, 
      insertContext, 
      this.stateManager.getExpanded(), 
      mainDoc.context
    );
    
    return finalViewData;
  }
}

// Specific workflow for updating views
class ViewUpdateWorkflow {
  constructor(viewManager, displayManager, stateManager, uiManager, linkedDocumentManager, enhancedLinkSubstitution = null) {
    this.viewManager = viewManager;
    this.displayManager = displayManager;
    this.stateManager = stateManager;
    this.uiManager = uiManager;
    this.linkedDocumentManager = linkedDocumentManager;
    this.enhancedLinkSubstitution = enhancedLinkSubstitution;
  }

  async execute() {
    const mainDocumentUrl = this.stateManager.mainDocumentUrl;
    if (!mainDocumentUrl) {
      console.warn('No main document URL found, skipping view update');
      return false;
    }
    
    console.log('🔄 === EXECUTING VIEW UPDATE WORKFLOW ===');
    console.log('📋 View mode:', this.stateManager.getExpanded() ? 'EXPANDED' : 'COMPACTED');
    
    const toggleContainer = document.querySelector('.result-header');
    if (toggleContainer) toggleContainer.style.opacity = '0.6';
    
    try {
      const mainDoc = this.stateManager.getMainDocument();
      if (!mainDoc) {
        throw new Error('Main document not found');
      }
      
      // Create view data using current substitute setting
      const substituteLinkedFiles = document.getElementById('substituteLinkedFiles')?.checked || false;
      const viewData = await this.createViewData(mainDoc, substituteLinkedFiles);
      
      // Update state and display
      this.stateManager.setCurrentViewData(viewData);
      await this.displayManager.displayResult(
        viewData, 
        this.stateManager.getExpanded(), 
        this.stateManager.getAllDocuments(), 
        this.stateManager.getMergedContext()
      );
      
      console.log('✅ View update workflow completed successfully');
      return true;
      
    } catch (error) {
      console.error('❌ View update workflow failed:', error);
      this.uiManager.showError(`Failed to update view: ${error.message}`);
      return false;
    } finally {
      if (toggleContainer) toggleContainer.style.opacity = '1';
    }
  }

  // UPDATED: Use substituteLinkedFiles parameter
  async createViewData(mainDoc, substituteLinkedFiles) {
    let viewData;
    
    if (this.stateManager.getExpanded()) {
      // For expanded view, create the view first then apply substitution
      viewData = await this.viewManager.createExpandedView(
        mainDoc, 
        this.stateManager.getAllDocuments(), 
        false, // Don't do auto-substitution here
        this.linkedDocumentManager
      );
    } else {
      // For compacted view, create the view first then apply substitution
      viewData = await this.viewManager.createCompactedView(
        mainDoc, 
        this.stateManager.getAllDocuments(), 
        false, // Don't do auto-substitution here
        this.stateManager.getMergedContext(),
        this.linkedDocumentManager
      );
    }
    
    // Apply enhanced link substitution BEFORE context insertion if enabled
    if (this.enhancedLinkSubstitution && substituteLinkedFiles) {
      console.log('🔄 Applying enhanced link substitution (view update)...');
      viewData = await this.enhancedLinkSubstitution.processDocumentWithSubstitution(viewData, {
        skipBrokenLinks: false,
        showProgress: true
      });
      console.log('✅ Enhanced link substitution completed (view update)');
    }
    
    // Apply context insertion after substitution
    const insertContext = document.getElementById('insertContext')?.checked || false;
    let finalViewData = this.viewManager.applyContextInsertion(
      viewData, 
      insertContext, 
      this.stateManager.getExpanded(), 
      mainDoc.context
    );
    
    return finalViewData;
  }
}