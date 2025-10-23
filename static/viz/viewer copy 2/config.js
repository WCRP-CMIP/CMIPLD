/**
 * CMIP-LD Viewer Configuration
 * External configuration for prefixes, API endpoints, and other settings
 */

window.CMIPLD_CONFIG = {
  // Available prefixes for the viewer
  prefixes: {
    'universal': 'https://wcrp-cmip.github.io/WCRP-universe/',
    'variables': 'https://wcrp-cmip.github.io/MIP-variables/',
    'cmip6plus': 'https://wcrp-cmip.github.io/CMIP6Plus_CVs/',
    'cmip7': 'https://wcrp-cmip.github.io/CMIP7-CVs/',
    'cf': 'https://wcrp-cmip.github.io/CF/',
    'obs4mips': 'https://wolfiex.github.io/obs4MIPs-cmor-tables-ld/'
  },

  // CORS proxy services (in order of preference)
  corsProxies: [
    '', // Try direct fetch first
    'https://api.allorigins.win/raw?url=',
    'https://corsproxy.io/?',
    'https://cors-anywhere.herokuapp.com/'
  ],

  // Default settings
  defaults: {
    depth: 2,
    followLinks: true,
    insertContext: false,
    expanded: false
  },

  // UI settings
  ui: {
    maxJsonHeight: '600px',
    animationDuration: '0.3s'
  }
};
