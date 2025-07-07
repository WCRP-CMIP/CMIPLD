// Export Manager - handles copying, downloading, and linking to JSON data
import { Utils } from './utils.js';

export class ExportManager {
  constructor(jsonRenderer, stateManager, referenceManager) {
    this.jsonRenderer = jsonRenderer;
    this.stateManager = stateManager;
    this.referenceManager = referenceManager;
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

  // Get the resolved URL for the current file with .json extension if needed
  getResolvedFileUrl() {
    const uriInput = document.getElementById('uri');
    if (!uriInput || !uriInput.value.trim()) {
      console.warn('⚠️ No URI input found or input is empty');
      return null;
    }

    const inputValue = uriInput.value.trim();
    console.log(`🔗 Resolving file URL for input: ${inputValue}`);
    
    let resolvedUrl = null;
    
    // If it's already a full URL, use as-is
    if (inputValue.startsWith('http://') || inputValue.startsWith('https://')) {
      console.log(`✅ Input is already a full URL: ${inputValue}`);
      resolvedUrl = inputValue;
    }
    // If it's a prefixed URI, expand it using the reference manager
    else if (this.referenceManager && inputValue.includes(':')) {
      console.log(`🔗 Attempting to expand prefixed URI: ${inputValue}`);
      console.log(`🔗 Reference manager available:`, !!this.referenceManager);
      console.log(`🔗 Reference manager context:`, this.referenceManager.resolvedContext);
      
      try {
        const expanded = this.referenceManager.expandReference(inputValue);
        console.log(`🔗 Expansion result: ${inputValue} -> ${expanded}`);
        
        if (expanded && expanded !== inputValue && (expanded.startsWith('http://') || expanded.startsWith('https://'))) {
          console.log(`✅ Successfully resolved to: ${expanded}`);
          resolvedUrl = expanded;
        } else {
          console.warn(`⚠️ Expansion failed or didn't produce valid URL: ${expanded}`);
        }
      } catch (error) {
        console.error(`❌ Error expanding reference:`, error);
      }
    }
    
    // Try using the state manager's main document URL as fallback
    if (!resolvedUrl && this.stateManager && this.stateManager.mainDocumentUrl) {
      console.log(`🔗 Using fallback from state manager: ${this.stateManager.mainDocumentUrl}`);
      resolvedUrl = this.stateManager.mainDocumentUrl;
    }
    
    if (!resolvedUrl) {
      console.warn(`⚠️ Unable to resolve URI: ${inputValue}`);
      return null;
    }
    
    // Add .json extension if no extension is present
    const finalUrl = this.addJsonExtensionIfNeeded(resolvedUrl);
    console.log(`🔗 Final URL with extension check: ${resolvedUrl} -> ${finalUrl}`);
    
    return finalUrl;
  }

  // Add .json extension if the URL doesn't have an extension
  addJsonExtensionIfNeeded(url) {
    if (!url || typeof url !== 'string') {
      return url;
    }
    
    // Parse the URL to get the pathname
    let pathname;
    try {
      const urlObj = new URL(url);
      pathname = urlObj.pathname;
    } catch (error) {
      // If URL parsing fails, just work with the string
      console.warn(`⚠️ URL parsing failed for ${url}, using string analysis`);
      pathname = url.split('?')[0].split('#')[0]; // Remove query params and hash
    }
    
    // Check if the pathname already has an extension
    const lastDotIndex = pathname.lastIndexOf('.');
    const lastSlashIndex = pathname.lastIndexOf('/');
    
    // If there's a dot after the last slash, it likely has an extension
    if (lastDotIndex > lastSlashIndex && lastDotIndex !== -1) {
      console.log(`🔗 URL already has extension: ${url}`);
      return url;
    }
    
    // Add .json extension
    const urlWithJson = url + '.json';
    console.log(`🔗 Added .json extension: ${url} -> ${urlWithJson}`);
    return urlWithJson;
  }

  // Copy the resolved file URL to clipboard
  async copyFileUrl() {
    const resolvedUrl = this.getResolvedFileUrl();
    
    if (!resolvedUrl) {
      const inputValue = document.getElementById('uri')?.value?.trim() || 'empty';
      alert(`Unable to resolve the URI "${inputValue}" to a valid URL.\n\nPlease check that:\n1. The URI is correctly formatted\n2. The document has been loaded first\n3. The prefix is properly defined`);
      return;
    }

    console.log(`📋 Copying URL to clipboard: ${resolvedUrl}`);

    try {
      await navigator.clipboard.writeText(resolvedUrl);
      
      const btn = document.getElementById('linkBtn');
      if (btn) {
        const originalText = btn.textContent;
        btn.textContent = 'Copied!';
        btn.style.backgroundColor = 'var(--success-color)';
        
        setTimeout(() => {
          btn.textContent = originalText;
          btn.style.backgroundColor = '';
        }, 2000);
      }
      
      console.log(`✅ Successfully copied URL to clipboard: ${resolvedUrl}`);
    } catch (error) {
      console.warn(`⚠️ Clipboard API failed, trying fallback:`, error);
      // Fallback for older browsers
      this.fallbackCopyUrl(resolvedUrl);
    }
  }

  // Fallback copy method for URLs
  fallbackCopyUrl(url) {
    const textArea = document.createElement('textarea');
    textArea.value = url;
    document.body.appendChild(textArea);
    textArea.select();
    document.execCommand('copy');
    document.body.removeChild(textArea);
    
    const btn = document.getElementById('linkBtn');
    if (btn) {
      const originalText = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => {
        btn.textContent = originalText;
      }, 2000);
    }
  }

  // Convert GitHub Pages URL to GitHub repository URL with src-data folder
  convertGithubPagesToRepo(githubPagesUrl) {
    if (!githubPagesUrl || typeof githubPagesUrl !== 'string') {
      return null;
    }

    // Pattern: https://username.github.io/repository-name/path/to/file
    // Target:  https://github.com/username/repository-name/blob/main/src-data/path/to/file
    
    const githubPagesPattern = /^https:\/\/([^.]+)\.github\.io\/([^\/]+)(\/.*)?$/;
    const match = githubPagesUrl.match(githubPagesPattern);
    
    if (match) {
      const [, username, repository, path] = match;
      let cleanPath = path || '';
      
      // Remove leading slash if present
      cleanPath = cleanPath.startsWith('/') ? cleanPath.substring(1) : cleanPath;
      
      // Add .json extension if no extension is present
      cleanPath = this.addJsonExtensionIfNeeded('dummy/' + cleanPath).substring(6); // Remove 'dummy/' prefix
      
      // Add src-data folder before the file path
      const filePathWithSrcData = cleanPath ? `src-data/${cleanPath}` : 'src-data';
      
      // Construct GitHub repository URL
      const githubUrl = `https://github.com/${username}/${repository}/blob/main/${filePathWithSrcData}`;
      
      console.log(`🔗 Converted GitHub Pages URL: ${githubPagesUrl} -> ${githubUrl}`);
      console.log(`🔗 - Username: ${username}`);
      console.log(`🔗 - Repository: ${repository}`);
      console.log(`🔗 - Original path: ${path || '(none)'}`);
      console.log(`🔗 - Clean path: ${cleanPath}`);
      console.log(`🔗 - Final path with src-data: ${filePathWithSrcData}`);
      
      return githubUrl;
    }
    
    console.warn(`⚠️ URL doesn't match GitHub Pages pattern: ${githubPagesUrl}`);
    return null;
  }

  // Open GitHub repository for the current file
  openGithubRepo() {
    const resolvedUrl = this.getResolvedFileUrl();
    
    if (!resolvedUrl) {
      const inputValue = document.getElementById('uri')?.value?.trim() || 'empty';
      alert(`Unable to resolve the URI "${inputValue}" to a valid URL.\n\nPlease check that:\n1. The URI is correctly formatted\n2. The document has been loaded first\n3. The prefix is properly defined`);
      return;
    }

    console.log(`🐙 Converting GitHub Pages URL to repository: ${resolvedUrl}`);
    const githubUrl = this.convertGithubPagesToRepo(resolvedUrl);
    
    if (!githubUrl) {
      alert(`This file does not appear to be hosted on GitHub Pages.\n\nResolved URL: ${resolvedUrl}\n\nOnly URLs matching the pattern:\nhttps://username.github.io/repository/path/file\n\ncan be converted to GitHub repository URLs.\n\nNote: The GitHub link will:\n- Add src-data/ folder to the path\n- Add .json extension if no extension exists`);
      return;
    }

    console.log(`✅ Opening GitHub repository: ${githubUrl}`);
    // Open in new tab
    window.open(githubUrl, '_blank');
  }
}
