// URL parameter handling
export class URLManager {
  static initializeFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    const settings = {};
    
    console.log('🔧 === INITIALIZING FROM URL ===');
    console.log('🔧 URL search params:', window.location.search);
    
    // Get values from URL
    const uri = urlParams.get('uri');
    if (uri) {
      settings.uri = decodeURIComponent(uri);
      console.log(`🔧 Found URI parameter: "${settings.uri}"`);
    }
    
    // FIXED: Consistent boolean parameter handling
    // substituteLinkedFiles - default TRUE unless explicitly set to false
    const substituteLinkedFiles = urlParams.get('substituteLinkedFiles');
    if (substituteLinkedFiles !== null) {
      settings.substituteLinkedFiles = substituteLinkedFiles === 'true';
      console.log(`🔧 Found substituteLinkedFiles parameter: ${settings.substituteLinkedFiles} (from "${substituteLinkedFiles}")`);
    } else {
      // Default to true when not specified in URL (matches config default)
      settings.substituteLinkedFiles = true;
      console.log(`🔧 No substituteLinkedFiles parameter, defaulting to: true`);
    }
    
    // insertContext - default FALSE unless explicitly set to true
    const insertContext = urlParams.get('insertContext');
    if (insertContext !== null) {
      settings.insertContext = insertContext === 'true';
      console.log(`🔧 Found insertContext parameter: ${settings.insertContext} (from "${insertContext}")`);
    } else {
      // Default to false when not specified in URL
      settings.insertContext = false;
      console.log(`🔧 No insertContext parameter, defaulting to: false`);
    }
    
    // expanded/isExpanded - default FALSE unless explicitly set to true
    const expanded = urlParams.get('expanded');
    if (expanded !== null) {
      settings.isExpanded = expanded === 'true';
      console.log(`🔧 Found expanded parameter: ${settings.isExpanded} (from "${expanded}")`);
    } else {
      // Default to false when not specified in URL
      settings.isExpanded = false;
      console.log(`🔧 No expanded parameter, defaulting to: false`);
    }
    
    // panelMinimized - default FALSE unless explicitly set to true
    const panelMinimized = urlParams.get('panelMinimized');
    if (panelMinimized !== null) {
      settings.panelMinimized = panelMinimized === 'true';
      console.log(`🔧 Found panelMinimized parameter: ${settings.panelMinimized} (from "${panelMinimized}")`);
    } else {
      // Default to false when not specified in URL
      settings.panelMinimized = false;
      console.log(`🔧 No panelMinimized parameter, defaulting to: false`);
    }
    
    console.log('🔧 Final settings from URL:', settings);
    return settings;
  }

  static updateUrl(settings) {
    const params = new URLSearchParams();
    
    console.log('🔧 === UPDATING URL ===');
    console.log('🔧 Settings to encode:', settings);
    
    if (settings.uri) {
      params.set('uri', encodeURIComponent(settings.uri));
      console.log(`🔧 Added URI parameter: "${settings.uri}"`);
    }
    
    // FIXED: Only add parameter to URL if it differs from default
    // substituteLinkedFiles - only add if FALSE (since default is TRUE)
    if (settings.substituteLinkedFiles === false) {
      params.set('substituteLinkedFiles', 'false');
      console.log(`🔧 Added substituteLinkedFiles parameter: false`);
    } else {
      console.log(`🔧 Skipping substituteLinkedFiles parameter (using default: true)`);
    }
    
    // insertContext - only add if TRUE (since default is FALSE)
    if (settings.insertContext === true) {
      params.set('insertContext', 'true');
      console.log(`🔧 Added insertContext parameter: true`);
    } else {
      console.log(`🔧 Skipping insertContext parameter (using default: false)`);
    }
    
    // isExpanded - only add if TRUE (since default is FALSE)
    if (settings.isExpanded === true) {
      params.set('expanded', 'true');
      console.log(`🔧 Added expanded parameter: true`);
    } else {
      console.log(`🔧 Skipping expanded parameter (using default: false)`);
    }
    
    // panelMinimized - only add if TRUE (since default is FALSE)  
    if (settings.panelMinimized === true) {
      params.set('panelMinimized', 'true');
      console.log(`🔧 Added panelMinimized parameter: true`);
    } else {
      console.log(`🔧 Skipping panelMinimized parameter (using default: false)`);
    }
    
    const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
    console.log(`🔧 New URL: ${newUrl}`);
    window.history.replaceState(null, '', newUrl);
  }
}