// Export Manager - handles copying and downloading of JSON data
import { Utils } from './utils.js';

export class ExportManager {
  constructor(jsonRenderer) {
    this.jsonRenderer = jsonRenderer;
  }

  // Copy JSON data to clipboard
  async copyToClipboard(currentViewData) {
    if (!currentViewData) return;
    
    try {
      const displayData = this.jsonRenderer.filterHiddenFields(currentViewData);
      const jsonString = JSON.stringify(displayData, null, 2);
      await navigator.clipboard.writeText(jsonString);
      
      const btn = document.getElementById('copyBtn');
      const originalText = btn.textContent;
      btn.textContent = 'Copied!';
      btn.style.backgroundColor = 'var(--success-color)';
      
      setTimeout(() => {
        btn.textContent = originalText;
        btn.style.backgroundColor = '';
      }, 2000);
    } catch (error) {
      this.fallbackCopy(currentViewData);
    }
  }

  // Fallback copy method for older browsers
  fallbackCopy(currentViewData) {
    const displayData = this.jsonRenderer.filterHiddenFields(currentViewData);
    const jsonString = JSON.stringify(displayData, null, 2);
    const textArea = document.createElement('textarea');
    textArea.value = jsonString;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    
    const btn = document.getElementById('copyBtn');
    const originalText = btn.textContent;
    btn.textContent = 'Copied!';
    setTimeout(() => {
      btn.textContent = originalText;
    }, 2000);
  }

  // Download JSON data as file
  downloadJson(currentViewData, isExpanded) {
    if (!currentViewData) return;
    
    const displayData = this.jsonRenderer.filterHiddenFields(currentViewData);
    const jsonString = JSON.stringify(displayData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = `cmipld-data-${isExpanded ? 'expanded' : 'compacted'}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }
}
