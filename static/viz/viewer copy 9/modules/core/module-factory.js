// Module Factory - creates and configures all modules with proper dependencies
import { StateManager } from '../state-manager.js';
import { DocumentLoader } from '../document-loader.js';
import { ReferenceManager } from '../reference-manager.js';
import { JSONLDProcessor } from '../jsonld-processor.js';
import { JSONRenderer } from '../json-renderer.js';
import { UIManager } from '../ui-manager.js';
import { ContextResolutionManager } from '../context-resolution-manager.js';
import { LinkedDocumentManager } from '../linked-document-manager.js';
import { ViewManager } from '../view-manager.js';
import { EventManager } from '../event-manager.js';
import { ExportManager } from '../export-manager.js';
import { DisplayManager } from '../display-manager.js';
import { InitializationManager } from './initialization-manager.js';
import { DataLoadingManager } from './data-loading-manager.js';
import { AutoSubstitutionManager } from '../auto-substitution-manager.js';
import { InlineDocumentManager } from '../inline-document-manager.js';
import { WorkflowManager } from './workflow-manager.js';
import { EnhancedLinkSubstitutionManager } from '../enhanced-link-substitution-manager.js';
import { CONFIG } from '../config.js';

export class ModuleFactory {
  // Create and configure all modules with proper dependency injection
  static createModules(viewer) {
    const modules = {};
    
    // Core state management
    modules.stateManager = new StateManager();
    
    // Core data modules
    modules.documentLoader = new DocumentLoader(CONFIG.corsProxies);
    modules.referenceManager = new ReferenceManager(CONFIG.prefixMapping);
    modules.jsonldProcessor = new JSONLDProcessor(modules.documentLoader, {});
    modules.jsonRenderer = new JSONRenderer();
    
    // Set up relationships
    modules.jsonRenderer.setReferenceManager(modules.referenceManager);
    
    // Specialized managers
    modules.contextResolutionManager = new ContextResolutionManager(modules.documentLoader);
    modules.autoSubstitutionManager = new AutoSubstitutionManager(
      modules.documentLoader,
      modules.contextResolutionManager,
      modules.jsonldProcessor,
      modules.referenceManager
    );
    modules.linkedDocumentManager = new LinkedDocumentManager(
      modules.documentLoader, 
      modules.jsonldProcessor, 
      modules.referenceManager
    );
    modules.viewManager = new ViewManager(
      modules.jsonldProcessor, 
      modules.contextResolutionManager,
      modules.autoSubstitutionManager
    );
    modules.exportManager = new ExportManager(modules.jsonRenderer);
    
    // UI managers
    modules.uiManager = new UIManager(modules.jsonRenderer, modules.referenceManager);
    modules.displayManager = new DisplayManager(modules.jsonRenderer, modules.uiManager);
    modules.eventManager = new EventManager(viewer);
    
    // New core managers
    modules.initializationManager = new InitializationManager(modules.stateManager);
    modules.dataLoadingManager = new DataLoadingManager(
      modules.stateManager,
      modules.documentLoader,
      modules.contextResolutionManager,
      modules.jsonldProcessor,
      modules.linkedDocumentManager
    );
    modules.inlineDocumentManager = new InlineDocumentManager(
      modules.documentLoader,
      modules.contextResolutionManager,
      modules.jsonldProcessor,
      modules.jsonRenderer,
      modules.referenceManager
    );
    modules.workflowManager = new WorkflowManager(
      modules.dataLoadingManager,
      modules.viewManager,
      modules.displayManager,
      modules.stateManager,
      modules.uiManager,
      modules.linkedDocumentManager,
      null // enhancedLinkSubstitution will be set after creation
    );
    modules.enhancedLinkSubstitution = new EnhancedLinkSubstitutionManager(
      modules.documentLoader,
      modules.jsonldProcessor,
      modules.referenceManager,
      modules.jsonRenderer
    );
    
    // Update workflow manager with the enhanced link substitution
    modules.workflowManager.enhancedLinkSubstitution = modules.enhancedLinkSubstitution;
    
    return modules;
  }

  // Configure UI callbacks and relationships
  static configureModuleRelationships(modules, viewer) {
    // Connect UI callbacks
    modules.uiManager.triggerRerender = () => viewer.rerenderDisplay();
    modules.uiManager.triggerFieldExpansion = (field, expand) => viewer.handleFieldExpansion(field, expand);
    
    // Configure JSON renderer for inline loading
    modules.jsonRenderer.setDocumentLoader(modules.documentLoader);
    
    // Configure auto-substitution manager with depth from UI
    const depthInput = document.getElementById('depth');
    const maxDepth = parseInt(depthInput?.value) || 2;
    modules.autoSubstitutionManager.setMaxDepth(maxDepth);
    
    // Set up inline loading callback (keeping for backward compatibility)
    const inlineLoadCallback = async (url, container, depth) => {
      const followLinks = document.getElementById('followLinks')?.checked || false;
      const insertContext = document.getElementById('insertContext')?.checked || false;
      const isExpanded = modules.stateManager.getExpanded();
      
      await modules.inlineDocumentManager.loadDocumentInline(
        url, container, depth, followLinks, insertContext, isExpanded
      );
    };
    
    modules.jsonRenderer.setInlineLoadCallback(inlineLoadCallback);
    
    // Add enhanced link styles
    modules.jsonRenderer.addEnhancedLinkStyles();
  }
}
