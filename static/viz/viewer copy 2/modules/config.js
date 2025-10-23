// Configuration and constants
export const CONFIG = {
  // Prefix mappings from locations.py (can be overridden by external config)
  prefixMapping: window.CMIPLD_CONFIG?.prefixes || {
    'universal': 'https://wcrp-cmip.github.io/WCRP-universe/',
    'variables': 'https://wcrp-cmip.github.io/MIP-variables/',
    'cmip6plus': 'https://wcrp-cmip.github.io/CMIP6Plus_CVs/',
    'cmip7': 'https://wcrp-cmip.github.io/CMIP7-CVs/',
    'cf': 'https://wcrp-cmip.github.io/CF/',
    'obs4mips': 'https://wolfiex.github.io/obs4MIPs-cmor-tables-ld/'
  },

  // CORS proxies to try in order (can be overridden by external config)
  corsProxies: window.CMIPLD_CONFIG?.corsProxies || [
    '', // Direct fetch first
    'https://api.allorigins.win/raw?url=',
    'https://corsproxy.io/?',
    'https://cors-anywhere.herokuapp.com/'
  ],

  // JSON-LD fields
  jsonLDFields: ['@id', '@type', '@context', '@graph', '@base', '@vocab', 'id', 'type'],

  // Default settings (can be overridden by external config)
  defaults: window.CMIPLD_CONFIG?.defaults || {
    depth: 2,
    followLinks: true,
    insertContext: false,
    expanded: false
  }
};
