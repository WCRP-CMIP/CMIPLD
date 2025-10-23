// Workflow Manager - coordinates complex multi-step operations
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
  async executeLoadAndDisplayWorkflow(uri, depth, followLinks) {
    const workflow = new LoadAndDisplayWorkflow(
      this.dataLoadingManager,
      this.viewManager,
      this.displayManager,
      this.stateManager,
      this.uiManager,
      this.linkedDocumentManager,
      this.enhancedLinkSubstitution
    );
    
    return await workflow.execute(uri, depth, followLinks);
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

  async execute(uri, depth, followLinks) {
    try {
      // Phase 1: Load data
      console.log('🚀 Phase 1: Loading data...');
      await this.dataLoadingManager.loadData(uri, depth, followLinks);
      
      // Phase 2: Create view
      console.log('🚀 Phase 2: Creating view...');
      const mainDoc = this.stateManager.getMainDocument();
      if (!mainDoc) {
        throw new Error('Main document not found after loading');
      }
      
      const viewData = await this.createViewData(mainDoc, followLinks);
      
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

  async createViewData(mainDoc, followLinks) {
    let viewData;
    
    if (this.stateManager.getExpanded()) {
      viewData = await this.viewManager.createExpandedView(
        mainDoc, 
        this.stateManager.getAllDocuments(), 
        followLinks,
        this.linkedDocumentManager
      );
    } else {
      viewData = await this.viewManager.createCompactedView(
        mainDoc, 
        this.stateManager.getAllDocuments(), 
        followLinks, 
        this.stateManager.getMergedContext(),
        this.linkedDocumentManager
      );
    }
    
    // Apply context insertion
    const insertContext = document.getElementById('insertContext')?.checked || false;
    let finalViewData = this.viewManager.applyContextInsertion(
      viewData, 
      insertContext, 
      this.stateManager.getExpanded(), 
      mainDoc.context
    );
    
    // Apply enhanced link substitution if available
    if (this.enhancedLinkSubstitution && followLinks) {
      console.log('🔄 Applying enhanced link substitution...');
      const depth = parseInt(document.getElementById('depth')?.value) || 2;
      finalViewData = await this.enhancedLinkSubstitution.processDocumentWithSubstitution(finalViewData, {
        maxDepth: depth,
        skipBrokenLinks: false,
        showProgress: true
      });
      console.log('✅ Enhanced link substitution completed');
    }
    
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
      
      // Create view data
      const followLinks = document.getElementById('followLinks')?.checked || false;
      const viewData = await this.createViewData(mainDoc, followLinks);
      
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

  async createViewData(mainDoc, followLinks) {
    let viewData;
    
    if (this.stateManager.getExpanded()) {
      viewData = await this.viewManager.createExpandedView(
        mainDoc, 
        this.stateManager.getAllDocuments(), 
        followLinks,
        this.linkedDocumentManager
      );
    } else {
      viewData = await this.viewManager.createCompactedView(
        mainDoc, 
        this.stateManager.getAllDocuments(), 
        followLinks, 
        this.stateManager.getMergedContext(),
        this.linkedDocumentManager
      );
    }
    
    // Apply context insertion
    const insertContext = document.getElementById('insertContext')?.checked || false;
    let finalViewData = this.viewManager.applyContextInsertion(
      viewData, 
      insertContext, 
      this.stateManager.getExpanded(), 
      mainDoc.context
    );
    
    // Apply enhanced link substitution if available
    if (this.enhancedLinkSubstitution && followLinks) {
      console.log('🔄 Applying enhanced link substitution (view update)...');
      const depth = parseInt(document.getElementById('depth')?.value) || 2;
      finalViewData = await this.enhancedLinkSubstitution.processDocumentWithSubstitution(finalViewData, {
        maxDepth: depth,
        skipBrokenLinks: false,
        showProgress: true
      });
      console.log('✅ Enhanced link substitution completed (view update)');
    }
    
    return finalViewData;
  }
}
