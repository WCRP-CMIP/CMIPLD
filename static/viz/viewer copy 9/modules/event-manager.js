// Event Manager - handles all DOM event listeners and interactions
export class EventManager {
  constructor(viewer) {
    this.viewer = viewer;
  }

  // Initialize all event listeners
  initializeEventListeners() {
    // Basic controls
    document.getElementById('loadBtn').addEventListener('click', () => this.viewer.loadData());
    document.getElementById('uri').addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.viewer.loadData();
    });
    
    // Minimize button
    this.initializeMinimizeButton();
    
    // Settings changes
    document.getElementById('uri').addEventListener('input', () => this.viewer.updateUrl());
    document.getElementById('depth').addEventListener('change', () => this.viewer.updateUrl());
    document.getElementById('followLinks').addEventListener('change', () => {
      this.viewer.updateUrl();
      if (this.viewer.mainDocumentUrl) this.viewer.updateView();
    });
    document.getElementById('insertContext').addEventListener('change', () => {
      this.viewer.updateUrl();
      if (this.viewer.mainDocumentUrl) this.viewer.updateView();
    });
    
    // Export functions
    document.getElementById('copyBtn').addEventListener('click', () => this.viewer.copyToClipboard());
    document.getElementById('downloadBtn').addEventListener('click', () => this.viewer.downloadJson());
    
    // View toggle
    this.initializeViewToggle();
  }

  // Initialize minimize button functionality
  initializeMinimizeButton() {
    const minimizeBtn = document.getElementById('minimizeBtn');
    const inputSection = document.getElementById('inputSection');
    const minimizeIcon = minimizeBtn.querySelector('.minimize-icon');
    
    minimizeBtn.addEventListener('click', () => {
      inputSection.classList.toggle('minimized');
      
      if (inputSection.classList.contains('minimized')) {
        minimizeIcon.textContent = '+';
        minimizeBtn.title = 'Expand';
      } else {
        minimizeIcon.textContent = '−';
        minimizeBtn.title = 'Minimize';
      }
      
      this.viewer.updateUrl();
    });
  }

  // Initialize view toggle functionality
  initializeViewToggle() {
    const viewToggle = document.getElementById('viewToggle');
    
    viewToggle.addEventListener('change', (e) => {
      this.viewer.isExpanded = e.target.checked;
      this.viewer.updateUrl();
      if (this.viewer.mainDocumentUrl) this.viewer.updateView();
    });
  }
}
