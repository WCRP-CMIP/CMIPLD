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
    const depthInput = document.getElementById('depth');
    const followLinksInput = document.getElementById('followLinks');
    const insertContextInput = document.getElementById('insertContext');
    
    if (settings.uri && uriInput) {
      uriInput.value = settings.uri;
    }
    
    if (depthInput) {
      depthInput.value = settings.depth || CONFIG.defaults.depth;
    }
    
    if (followLinksInput) {
      followLinksInput.checked = settings.followLinks !== undefined ? 
        settings.followLinks : CONFIG.defaults.followLinks;
    }
    
    if (insertContextInput) {
      insertContextInput.checked = settings.insertContext !== undefined ? 
        settings.insertContext : CONFIG.defaults.insertContext;
    }
  }

  // Apply view state (expanded/compacted toggle)
  applyViewState(settings) {
    const isExpanded = settings.isExpanded || false;
    this.stateManager.setExpanded(isExpanded);
    
    const viewToggle = document.getElementById('viewToggle');
    if (viewToggle) {
      viewToggle.checked = isExpanded;
    }
  }

  // Apply panel state (minimized/expanded)
  applyPanelState(settings) {
    if (settings.panelMinimized) {
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
    }
  }

  // Check if auto-load should be triggered
  shouldAutoLoad(settings) {
    return settings.uri && settings.uri.trim() !== '';
  }
}
