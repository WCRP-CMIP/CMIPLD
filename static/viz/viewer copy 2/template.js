/**
 * Simple template updater for dynamic content
 */
document.addEventListener('DOMContentLoaded', () => {
  // Update prefix examples if external config is available
  if (window.CMIPLD_CONFIG?.prefixes) {
    const prefixExamples = document.querySelector('.prefix-examples');
    if (prefixExamples) {
      const prefixes = Object.keys(window.CMIPLD_CONFIG.prefixes);
      const prefixElements = prefixes.map(prefix => `<code>${prefix}:</code>`).join(' ');
      prefixExamples.innerHTML = `<strong>Available prefixes:</strong> ${prefixElements}`;
    }
  }

  // Update default values from config
  if (window.CMIPLD_CONFIG?.defaults) {
    const defaults = window.CMIPLD_CONFIG.defaults;
    
    // Update depth if not already set
    const depthInput = document.getElementById('depth');
    if (depthInput && depthInput.value === '2') {
      depthInput.value = defaults.depth || 2;
    }
    
    // Update checkboxes if not already set by URL
    const followLinksCheckbox = document.getElementById('followLinks');
    if (followLinksCheckbox && !window.location.search.includes('followLinks')) {
      followLinksCheckbox.checked = defaults.followLinks !== undefined ? defaults.followLinks : true;
    }
    
    const insertContextCheckbox = document.getElementById('insertContext');
    if (insertContextCheckbox && !window.location.search.includes('insertContext')) {
      insertContextCheckbox.checked = defaults.insertContext !== undefined ? defaults.insertContext : false;
    }
  }
});
