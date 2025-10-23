// Display Manager - handles rendering and display of results
import { Utils } from './utils.js';

export class DisplayManager {
  constructor(jsonRenderer, uiManager) {
    this.jsonRenderer = jsonRenderer;
    this.uiManager = uiManager;
  }

  // Display the result with statistics and rendering
  async displayResult(data, isExpanded, documents, mergedContext) {
    const resultSection = document.getElementById('resultSection');
    const statsElement = document.getElementById('resultStats');
    const jsonViewer = document.getElementById('jsonViewer');
    const viewToggle = document.getElementById('viewToggle');
    const depthInput = document.getElementById('depth');
    
    if (!resultSection || !jsonViewer) {
      console.error('Required DOM elements not found');
      return;
    }
    
    if (viewToggle) {
      viewToggle.checked = isExpanded;
    }
    
    // Get depth setting for inline loading
    const maxDepth = parseInt(depthInput?.value) || 2;
    
    // Configure JSON renderer for depth and inline loading
    this.jsonRenderer.setMaxDepth(maxDepth);
    this.jsonRenderer.setCurrentDepth(0);
    
    // Calculate statistics
    const displayData = this.jsonRenderer.filterHiddenFields(data);
    const jsonString = JSON.stringify(displayData, null, 2);
    const lines = jsonString.split('\n').length;
    const size = new Blob([jsonString]).size;
    const loadedDocs = documents.size;
    const contextTerms = Object.keys(mergedContext).length;
    
    const viewMode = isExpanded ? 
      '🔄 EXPANDED VIEW: jsonld.expand output (absolute URIs)' : 
      '📄 COMPACTED VIEW: jsonld.compact output (human-readable)';
    
    if (statsElement) {
      statsElement.textContent = `${viewMode} • ${lines} lines • ${Utils.formatBytes(size)} • ${loadedDocs} documents loaded • ${contextTerms} context terms`;
    }
    
    // Get the main document context for field toggles
    const mainDoc = documents.values().next().value; // Get first document (main)
    const contextForToggles = mainDoc ? mainDoc.resolvedContext || {} : {};
    
    // Create field toggles
    this.uiManager.createFieldToggles(data, contextForToggles);
    
    // Render JSON with depth tracking
    this.jsonRenderer.renderJson(displayData, jsonViewer, 0, 0);
    
    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
  }

  // Re-render the current display
  rerenderDisplay(currentViewData) {
    if (currentViewData) {
      const jsonViewer = document.getElementById('jsonViewer');
      const depthInput = document.getElementById('depth');
      
      if (jsonViewer) {
        // Get depth setting for inline loading
        const maxDepth = parseInt(depthInput?.value) || 2;
        
        // Configure JSON renderer for depth and inline loading
        this.jsonRenderer.setMaxDepth(maxDepth);
        this.jsonRenderer.setCurrentDepth(0);
        
        const displayData = this.jsonRenderer.filterHiddenFields(currentViewData);
        this.jsonRenderer.renderJson(displayData, jsonViewer, 0, 0);
      }
    }
  }
}
