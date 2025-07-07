// URL parameter handling
export class URLManager {
  static initializeFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    const settings = {};
    
    // Get values from URL
    const uri = urlParams.get('uri');
    if (uri) {
      settings.uri = decodeURIComponent(uri);
    }
    
    const depth = urlParams.get('depth');
    if (depth) {
      settings.depth = depth;
    }
    
    const followLinks = urlParams.get('followLinks');
    if (followLinks !== null) {
      settings.followLinks = followLinks === 'true';
    }
    
    const insertContext = urlParams.get('insertContext');
    if (insertContext !== null) {
      settings.insertContext = insertContext === 'true';
    }
    
    const expanded = urlParams.get('expanded');
    settings.isExpanded = expanded === 'true';
    
    // New: Panel state
    const panelMinimized = urlParams.get('panelMinimized');
    if (panelMinimized !== null) {
      settings.panelMinimized = panelMinimized === 'true';
    }
    
    return settings;
  }

  static updateUrl(settings) {
    const params = new URLSearchParams();
    
    if (settings.uri) {
      params.set('uri', encodeURIComponent(settings.uri));
    }
    
    if (settings.depth && settings.depth !== '2') {
      params.set('depth', settings.depth);
    }
    
    if (!settings.followLinks) {
      params.set('followLinks', 'false');
    }
    
    if (settings.insertContext) {
      params.set('insertContext', 'true');
    }
    
    if (settings.isExpanded) {
      params.set('expanded', 'true');
    }
    
    // New: Panel state
    if (settings.panelMinimized) {
      params.set('panelMinimized', 'true');
    }
    
    const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
    window.history.replaceState(null, '', newUrl);
  }
}
