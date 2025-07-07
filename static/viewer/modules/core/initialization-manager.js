// Initialization Manager - handles viewer initialization and setup
import { CONFIG } from '../config.js';
import { URLManager } from '../url-manager.js';

export class InitializationManager {
  constructor(stateManager) {
    this.stateManager = stateManager;
  }

  // Initialize from URL parameters and apply to DOM
  initializeFromUrl() {
    const settings = URLManager.initializeFromUrl();
    
    // Apply settings to DOM elements
    this.applySettingsToDOM(settings);
    
    // Apply view state
    this.applyViewState(settings);
    
    // Apply panel state
    this.applyPanelState(settings);
    
    return settings;
  }

  // Apply URL settings to DOM form elements
  applySettingsToDOM(settings) {
    const uriInput = document.getElementById('uri');
    const substituteLinkedFilesInput = document.getElementById('substituteLinkedFiles');
    const insertContextInput = document.getElementById('insertContext');
    
    if (settings.uri && uriInput) {
      uriInput.value = settings.uri;
    }
    
    if (substituteLinkedFilesInput) {
      // FIXED: Ensure consistent handling of substituteLinkedFiles parameter
      // Use explicit boolean check instead of undefined check
      const shouldSubstitute = settings.substituteLinkedFiles !== false; // Default to true unless explicitly false
      substituteLinkedFilesInput.checked = shouldSubstitute;
      console.log(`🔧 Applied substituteLinkedFiles from URL: ${shouldSubstitute} (original value: ${settings.substituteLinkedFiles})`);
    }
    
    if (insertContextInput) {
      // FIXED: Ensure consistent handling of insertContext parameter
      const shouldInsertContext = settings.insertContext === true; // Default to false unless explicitly true
      insertContextInput.checked = shouldInsertContext;
      console.log(`🔧 Applied insertContext from URL: ${shouldInsertContext} (original value: ${settings.insertContext})`);
    }
  }

  // Apply view state (expanded/compacted toggle)
  applyViewState(settings) {
    // FIXED: Consistent handling of isExpanded parameter
    const isExpanded = settings.isExpanded === true; // Default to false unless explicitly true
    this.stateManager.setExpanded(isExpanded);
    
    const viewToggle = document.getElementById('viewToggle');
    if (viewToggle) {
      viewToggle.checked = isExpanded;
      console.log(`🔧 Applied view state from URL: ${isExpanded ? 'EXPANDED' : 'COMPACTED'} (original value: ${settings.isExpanded})`);
    }
  }

  // Apply panel state (minimized/expanded)
  applyPanelState(settings) {
    // FIXED: Consistent handling of panelMinimized parameter
    const shouldMinimize = settings.panelMinimized === true; // Default to false unless explicitly true
    
    if (shouldMinimize) {
      const inputSection = document.getElementById('inputSection');
      const minimizeIcon = document.querySelector('.minimize-icon');
      const minimizeBtn = document.getElementById('minimizeBtn');
      
      if (inputSection) {
        inputSection.classList.add('minimized');
      }
      
      if (minimizeIcon) {
        minimizeIcon.textContent = '+';
      }
      
      if (minimizeBtn) {
        minimizeBtn.title = 'Expand';
      }
      
      console.log(`🔧 Applied panel state from URL: MINIMIZED`);
    } else {
      console.log(`🔧 Applied panel state from URL: EXPANDED (original value: ${settings.panelMinimized})`);
    }
  }

  // Check if auto-load should be triggered
  shouldAutoLoad(settings) {
    const hasUri = settings.uri && settings.uri.trim() !== '';
    console.log(`🔧 Auto-load check: hasUri=${hasUri}, uri="${settings.uri}"`);
    return hasUri;
  }
}