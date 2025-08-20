/**
 * Embed.js - Mobile-safe embedded view system with NUCLEAR old button cleanup
 * 
 * USAGE (DESKTOP ONLY):
 * 1. Add ?embed=true to any page URL for embed mode
 * 2. Click floating expand button (⤢) in bottom-right corner  
 * 3. Use F11 or ESC keyboard shortcuts
 * 4. Tables automatically get search/filter functionality in expanded view only
 * 
 * MOBILE: All functionality is disabled to prevent conflicts with MkDocs
 */

// NUCLEAR CLEANUP - Run IMMEDIATELY before anything else
(function nuclearCleanup() {
    'use strict';
    console.log('🧹 NUCLEAR CLEANUP: Eliminating ALL old button traces...');
    
    function destroyOldButtons() {
        let removedCount = 0;
        
        // Remove ALL old button classes (comprehensive list)
        const oldButtonSelectors = [
            '.minimize-maximize-btn',
            '.fullscreen-btn', 
            '.table-maximize-btn',
            '.page-maximize-btn',
            '.header-maximize-btn',
            '.sidebar-maximize-btn',
            'button[title="Maximize Page"]',
            'button[title="Toggle Fullscreen"]',
            'button[title="Maximize"]',
            'button[title="Minimize"]',
            'button[aria-label="Maximize"]',
            'button[aria-label="Minimize"]'
        ];
        
        oldButtonSelectors.forEach(selector => {
            const buttons = document.querySelectorAll(selector);
            buttons.forEach(button => {
                console.log(`🗑️  DESTROYED old button: ${selector}`, button);
                button.remove();
                removedCount++;
            });
        });
        
        // Remove ALL old wrapper elements
        const wrappers = document.querySelectorAll('.fullscreen-wrapper, .maximize-wrapper');
        wrappers.forEach(wrapper => {
            while (wrapper.firstChild) {
                wrapper.parentNode.insertBefore(wrapper.firstChild, wrapper);
            }
            wrapper.remove();
            removedCount++;
        });
        
        // Clean up ALL old CSS classes
        const oldClasses = ['fullscreen-mode', 'fullscreen-active', 'maximize-mode'];
        oldClasses.forEach(className => {
            document.body.classList.remove(className);
            document.querySelectorAll(`.${className}`).forEach(el => {
                el.classList.remove(className);
            });
        });
        
        return removedCount;
    }
    
    // Run cleanup immediately
    const removed = destroyOldButtons();
    console.log(`🧹 NUCLEAR CLEANUP: Destroyed ${removed} old elements`);
    
    // Set up mutation observer to prevent ANY old buttons from being created
    if (typeof MutationObserver !== 'undefined') {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) {
                        // Kill any old buttons immediately
                        const isOldButton = node.classList && (
                            node.classList.contains('minimize-maximize-btn') ||
                            node.title === 'Maximize Page'
                        );
                        
                        if (isOldButton) {
                            console.log('🚫 INTERCEPTED: Old button blocked', node);
                            node.remove();
                            return;
                        }
                        
                        // Kill old buttons in children
                        if (node.querySelectorAll) {
                            const oldButtons = node.querySelectorAll('.minimize-maximize-btn, button[title="Maximize Page"]');
                            oldButtons.forEach(btn => {
                                console.log('🚫 INTERCEPTED: Old button in children blocked', btn);
                                btn.remove();
                            });
                        }
                    }
                });
            });
        });
        
        observer.observe(document.documentElement, {
            childList: true,
            subtree: true
        });
        
        console.log('🛡️  Mutation observer active - blocking all old buttons');
    }
    
    // Clean up again after delays
    setTimeout(destroyOldButtons, 100);
    setTimeout(destroyOldButtons, 500);
    setTimeout(destroyOldButtons, 1000);
})();

document.addEventListener('DOMContentLoaded', function() {
    console.log('Embed.js v9 loaded and initializing...');
    
    // Run one more nuclear cleanup after DOM is ready
    setTimeout(() => {
        const oldButtons = document.querySelectorAll('.minimize-maximize-btn, button[title="Maximize Page"]');
        oldButtons.forEach(btn => {
            console.log('🗑️  Post-DOM cleanup: Removing old button', btn);
            btn.remove();
        });
    }, 10);
    
    // CRITICAL: Check if we're on mobile - if so, disable all custom functionality
    if (isMobileDevice()) {
        console.log('Mobile device detected - disabling all custom functionality');
        return; // Exit early on mobile
    }
    
    console.log('Desktop device detected - enabling full functionality');
    
    // Check for embed parameter in URL (handle various formats)
    const urlParams = new URLSearchParams(window.location.search);
    const embedMode = urlParams.get('embed') === 'true' || 
                     urlParams.get('embed') === '1' ||
                     urlParams.get('fullscreen') === 'true' ||
                     urlParams.has('embed');
    
    console.log('Embed mode:', embedMode);
    console.log('URL params:', window.location.search);
    
    // Initialize functionality (desktop only)
    addFloatingExpandButton();
    addKeyboardShortcuts();
    enhanceTables();
    addResizeHandler();
    
    // Auto-enter embed mode if parameter is present
    if (embedMode) {
        console.log('Auto-entering embed mode due to URL parameter');
        setTimeout(() => {
            enterEmbedMode();
        }, 500);
    }
});

/**
 * Detect if device is mobile using MkDocs breakpoint
 */
function isMobileDevice() {
    // Use MkDocs mobile breakpoint (76.1875em = 1219px)
    return window.innerWidth <= 1219;
}

/**
 * Handle window resize - disable on mobile, enable on desktop
 */
function addResizeHandler() {
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            const wasMobile = document.body.hasAttribute('data-mobile-mode');
            const isMobile = isMobileDevice();
            
            if (isMobile && !wasMobile) {
                // Switched to mobile - disable everything
                console.log('Switched to mobile - disabling functionality');
                document.body.setAttribute('data-mobile-mode', 'true');
                if (document.body.classList.contains('embed-mode')) {
                    exitEmbedMode();
                }
                // Remove floating button
                const btn = document.querySelector('.floating-expand-btn');
                if (btn) btn.remove();
                
            } else if (!isMobile && wasMobile) {
                // Switched to desktop - enable functionality
                console.log('Switched to desktop - enabling functionality');
                document.body.removeAttribute('data-mobile-mode');
                addFloatingExpandButton();
                
            } else if (!isMobile && document.body.classList.contains('embed-mode')) {
                // Desktop resize in embed mode - refresh
                console.log('Desktop resize in embed mode - refreshing');
                exitEmbedMode();
                setTimeout(() => {
                    enterEmbedMode();
                }, 100);
            }
        }, 250);
    });
}

/**
 * Add floating expand button (desktop only)
 */
function addFloatingExpandButton() {
    // Safety check - don't add on mobile
    if (isMobileDevice()) {
        console.log('Skipping floating button - mobile device');
        return;
    }
    
    // Only add if not already present
    if (document.querySelector('.floating-expand-btn')) {
        return;
    }
    
    console.log('Adding floating expand button...');
    
    const button = document.createElement('button');
    button.className = 'floating-expand-btn';
    button.innerHTML = '⤢';
    button.title = 'Toggle Fullscreen (F11)';
    button.setAttribute('aria-label', 'Toggle fullscreen');
    
    // Add to body
    document.body.appendChild(button);
    
    // Add click handler
    button.addEventListener('click', () => {
        if (document.body.classList.contains('embed-mode')) {
            exitEmbedMode();
        } else {
            enterEmbedMode();
        }
    });
    
    console.log('Floating expand button added');
}

/**
 * Enter embed mode - DESKTOP ONLY
 */
function enterEmbedMode() {
    // Safety check - don't enter embed mode on mobile
    if (isMobileDevice()) {
        console.log('Cannot enter embed mode - mobile device');
        return;
    }
    
    console.log('Entering embed mode');
    
    // Add embed-mode class to body
    document.body.classList.add('embed-mode');
    
    // Update URL to include embed parameter
    const url = new URL(window.location);
    url.searchParams.set('embed', 'true');
    window.history.replaceState({}, '', url);
    
    // Hide all navigation elements (safe on desktop)
    const elementsToHide = [
        '.md-header', '.md-tabs', '.md-footer', '.md-sidebar',
        '.md-sidebar--primary', '.md-sidebar--secondary', '.md-nav', '.md-search'
    ];
    
    elementsToHide.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.style.display = 'none';
            el.style.visibility = 'hidden';
        });
    });
    
    // Adjust content to fill viewport
    const container = document.querySelector('.md-container');
    const main = document.querySelector('.md-main');
    const content = document.querySelector('.md-content');
    
    if (container) {
        container.style.cssText = 'max-width: none !important; margin: 0 !important; padding: 0 !important; width: 100% !important;';
    }
    if (main) {
        main.style.cssText = 'max-width: none !important; margin: 0 !important; padding: 0 !important; width: 100% !important;';
    }
    if (content) {
        content.style.cssText = 'max-width: none !important; margin: 0 !important; padding: 1rem !important; width: 100% !important; min-height: 100vh !important;';
    }
    
    // Convert floating button to close button
    const floatingBtn = document.querySelector('.floating-expand-btn');
    if (floatingBtn) {
        floatingBtn.innerHTML = '×';
        floatingBtn.title = 'Close (ESC)';
        floatingBtn.setAttribute('aria-label', 'Close fullscreen');
        
        floatingBtn.style.cssText = `
            position: fixed !important;
            top: 15px !important;
            right: 15px !important;
            width: 32px !important;
            height: 32px !important;
            background: rgba(0, 0, 0, 0.7) !important;
            color: white !important;
            border: none !important;
            border-radius: 0.25rem !important;
            font-size: 16px !important;
            font-weight: bold !important;
            cursor: pointer !important;
            z-index: 10000 !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4) !important;
            transition: all 0.2s ease !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-family: inherit !important;
            line-height: 1 !important;
        `;
    }
    
    // Show table search boxes
    updateTableControlsVisibility();
    
    console.log('Embed mode activated');
}

/**
 * Exit embed mode - DESKTOP ONLY
 */
function exitEmbedMode() {
    console.log('Exiting embed mode');
    
    // Remove embed-mode class from body
    document.body.classList.remove('embed-mode');
    
    // Remove embed parameter from URL
    const url = new URL(window.location);
    url.searchParams.delete('embed');
    url.searchParams.delete('fullscreen');
    window.history.replaceState({}, '', url);
    
    // Show all navigation elements
    const elementsToShow = [
        '.md-header', '.md-tabs', '.md-footer', '.md-sidebar',
        '.md-sidebar--primary', '.md-sidebar--secondary', '.md-nav', '.md-search'
    ];
    
    elementsToShow.forEach(selector => {
        const elements = document.querySelectorAll(selector);
        elements.forEach(el => {
            el.style.display = '';
            el.style.visibility = '';
        });
    });
    
    // Reset content styling
    const container = document.querySelector('.md-container');
    const main = document.querySelector('.md-main');
    const content = document.querySelector('.md-content');
    
    if (container) container.style.cssText = '';
    if (main) main.style.cssText = '';
    if (content) content.style.cssText = '';
    
    // Convert close button back to floating expand button
    const floatingBtn = document.querySelector('.floating-expand-btn');
    if (floatingBtn) {
        floatingBtn.innerHTML = '⤢';
        floatingBtn.title = 'Toggle Fullscreen (F11)';
        floatingBtn.setAttribute('aria-label', 'Toggle fullscreen');
        
        floatingBtn.style.cssText = `
            position: fixed !important;
            bottom: 80px !important;
            right: 20px !important;
            width: 50px !important;
            height: 50px !important;
            background: var(--md-primary-fg-color, #1976d2) !important;
            color: white !important;
            border: none !important;
            border-radius: 50% !important;
            font-size: 1.5rem !important;
            cursor: pointer !important;
            z-index: 1000 !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.3s ease !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            font-family: inherit !important;
            line-height: 1 !important;
            touch-action: manipulation !important;
        `;
    }
    
    // Hide table search boxes
    updateTableControlsVisibility();
    
    console.log('Embed mode deactivated');
}

/**
 * Add keyboard shortcuts (desktop only)
 */
function addKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Safety check - don't handle shortcuts on mobile
        if (isMobileDevice()) return;
        
        // ESC to exit embed mode
        if (e.key === 'Escape') {
            if (document.body.classList.contains('embed-mode')) {
                exitEmbedMode();
                e.preventDefault();
            }
        }
        
        // F11 to toggle embed mode
        if (e.key === 'F11') {
            e.preventDefault();
            if (document.body.classList.contains('embed-mode')) {
                exitEmbedMode();
            } else {
                enterEmbedMode();
            }
        }
    });
}

/**
 * Enhance tables with sorting and filtering (desktop only)
 */
function enhanceTables() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
        addTableControls(table);
        makeTableResponsive(table);
        
        // Only add sorting on desktop
        if (!isMobileDevice()) {
            addTableSorting(table);
        }
    });
}

/**
 * Add controls to tables
 */
function addTableControls(table) {
    // Check if controls already exist
    if (table.previousElementSibling && table.previousElementSibling.classList.contains('table-controls')) {
        return;
    }
    
    // Create controls container
    const controls = document.createElement('div');
    controls.className = 'table-controls';
    
    // Add search input
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = 'Search table...';
    searchInput.className = 'table-search';
    
    searchInput.addEventListener('input', () => filterTable(table, searchInput.value));
    
    controls.appendChild(searchInput);
    table.parentNode.insertBefore(controls, table);
    
    // Hide search box by default (only show in expanded view)
    updateTableControlsVisibility();
}

/**
 * Make table responsive
 */
function makeTableResponsive(table) {
    // Add responsive wrapper if not already present
    if (!table.parentElement.classList.contains('table-responsive')) {
        const wrapper = document.createElement('div');
        wrapper.className = 'table-responsive';
        table.parentNode.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    }
}

/**
 * Add sorting to table headers (desktop only)
 */
function addTableSorting(table) {
    const headers = table.querySelectorAll('th');
    
    headers.forEach((header, index) => {
        header.title = 'Click to sort';
        header.style.cursor = 'pointer';
        
        header.addEventListener('click', () => {
            sortTable(table, index);
        });
    });
}

/**
 * Sort table by column
 */
function sortTable(table, columnIndex) {
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const header = table.querySelectorAll('th')[columnIndex];
    
    // Determine sort direction
    const currentSort = header.getAttribute('data-sort') || 'asc';
    const newSort = currentSort === 'asc' ? 'desc' : 'asc';
    
    // Clear all sort indicators
    table.querySelectorAll('th').forEach(th => {
        th.removeAttribute('data-sort');
        th.classList.remove('sort-asc', 'sort-desc');
    });
    
    // Set new sort
    header.setAttribute('data-sort', newSort);
    header.classList.add(`sort-${newSort}`);
    
    // Sort rows
    rows.sort((a, b) => {
        const aText = a.cells[columnIndex]?.textContent.trim() || '';
        const bText = b.cells[columnIndex]?.textContent.trim() || '';
        
        // Try to parse as numbers
        const aNum = parseFloat(aText);
        const bNum = parseFloat(bText);
        
        if (!isNaN(aNum) && !isNaN(bNum)) {
            return newSort === 'asc' ? aNum - bNum : bNum - aNum;
        } else {
            return newSort === 'asc' ? 
                aText.localeCompare(bText) : 
                bText.localeCompare(aText);
        }
    });
    
    // Reorder rows
    rows.forEach(row => tbody.appendChild(row));
}

/**
 * Filter table rows based on search term
 */
function filterTable(table, searchTerm) {
    const tbody = table.querySelector('tbody');
    if (!tbody) return;
    
    const rows = tbody.querySelectorAll('tr');
    const term = searchTerm.toLowerCase();
    
    rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(term) ? '' : 'none';
    });
}

/**
 * Update table controls visibility
 */
function updateTableControlsVisibility() {
    const tableControls = document.querySelectorAll('.table-controls');
    const isEmbedMode = document.body.classList.contains('embed-mode');
    const isMobile = isMobileDevice();
    
    tableControls.forEach(controls => {
        if (!isMobile && isEmbedMode) {
            // Show search box in expanded view (desktop only)
            controls.style.display = 'block';
            controls.style.opacity = '1';
        } else {
            // Hide search box in normal view or on mobile
            controls.style.display = 'none';
            controls.style.opacity = '0';
        }
    });
}

// Export functions for external use
window.embedUtils = {
    version: 9,
    enterEmbedMode,
    exitEmbedMode,
    addFloatingExpandButton,
    enhanceTables,
    filterTable,
    sortTable,
    updateTableControlsVisibility,
    isMobileDevice
};