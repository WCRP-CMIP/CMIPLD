// Utility functions
export class Utils {
  // Resolve prefixes like cmipld.locations.resolve_prefix
  static resolvePrefix(query, prefixMapping) {
    if (typeof query !== 'string' || query.startsWith('http')) {
      return query;
    }

    const colonIndex = query.indexOf(':');
    if (colonIndex === -1) {
      return query;
    }

    const prefix = query.substring(0, colonIndex);
    const suffix = query.substring(colonIndex + 1);

    if (prefixMapping[prefix]) {
      if (suffix === '' || suffix === '/') {
        return `${prefixMapping[prefix]}graph.jsonld`;
      }
      return `${prefixMapping[prefix]}${suffix}`;
    }

    return query;
  }

  // Convert relative URLs to absolute
  static resolveUrl(url, baseUrl) {
    if (url.startsWith('http')) {
      return url;
    }
    
    if (url.startsWith('/')) {
      const base = new URL(baseUrl);
      return `${base.protocol}//${base.host}${url}`;
    }
    
    return new URL(url, baseUrl).href;
  }

  // Escape HTML for display
  static escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Format bytes for display
  static formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  // Deep clone object
  static deepClone(obj) {
    return JSON.parse(JSON.stringify(obj));
  }
}
