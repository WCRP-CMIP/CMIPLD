/**
<<<<<<< HEAD
 * Embed.js - Streamlined embedded view system focused on tables
=======
 * Embed.js - Complete embedded view system
 * Only floating button in bottom-right corner
>>>>>>> e43c076 (expand correction)
 * 
 * USAGE:
 * 1. Add ?embed=true to any page URL for embed mode
 * 2. Click floating expand button (⤢) in bottom-right corner  
 * 3. Use F11 or ESC keyboard shortcuts
<<<<<<< HEAD
 * 4. Tables automatically get search/filter functionality in expanded view only
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Embed.js v7 loaded and initializing...');
    
    // CRITICAL: Clean up any old button systems first
    cleanupOldButtons();
    
    // Check for embed parameter in URL (handle various formats)
=======
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Embed.js v3 loaded and initializing...');
    
    // Check for embed parameter in URL
>>>>>>> e43c076 (expand correction)
    const urlParams = new URLSearchParams(window.location.search);
    const embedMode = urlParams.get('embed') === 'true' || 
                     urlParams.get('embed') === '1' ||
                     urlParams.get('fullscreen') === 'true' ||
                     urlParams.has('embed');
    
    console.log('Embed mode:', embedMode);
<<<<<<< HEAD
    console.log('URL params:', window.location.search);
=======
    
    // Add floating expand button to all pages
    addFloatingExpandButton();
>>>>>>> e43c076 (expand correction)
    
    // Initialize functionality
    addFloatingExpandButton();
    addKeyboardShortcuts();
<<<<<<< HEAD
    enhanceTables();
    addResizeHandler(); // Handle mobile/desktop transitions
    
    // Auto-enter embed mode if parameter is present
    if (embedMode) {
        console.log('Auto-entering embed mode due to URL parameter');
=======
    
    // Auto-enter embed mode if parameter is present
    if (embedMode) {
>>>>>>> e43c076 (expand correction)
        setTimeout(() => {
            enterEmbedMode();
        }, 500);
    }
});

/**
<<<<<<< HEAD
 * Clean up any old button systems that might conflict
 */
function cleanupOldButtons() {
    console.log('Cleaning up old button systems...');
    
    // Remove old minimize-maximize buttons
    const oldButtons = document.querySelectorAll('.minimize-maximize-btn, .fullscreen-btn, .table-maximize-btn, .page-maximize-btn');
    oldButtons.forEach(button => {
        console.log('Removing old button:', button.className);
        button.remove();
    });
    
    // Remove old wrappers
    const oldWrappers = document.querySelectorAll('.fullscreen-wrapper');
    oldWrappers.forEach(wrapper => {
        // Move children out of wrapper and remove wrapper
        while (wrapper.firstChild) {
            wrapper.parentNode.insertBefore(wrapper.firstChild, wrapper);
        }
        wrapper.remove();
    });
    
    // Clean up old CSS classes
    document.body.classList.remove('fullscreen-mode');
    const elementsWithOldClasses = document.querySelectorAll('.fullscreen-active');
    elementsWithOldClasses.forEach(el => {
        el.classList.remove('fullscreen-active');
    });
    
    console.log('Old button cleanup complete');
}

/**
 * Handle window resize to ensure mobile compatibility
 */
function addResizeHandler() {
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(() => {
            // If we're in embed mode and resize crosses mobile breakpoint, refresh embed mode
            if (document.body.classList.contains('embed-mode')) {
                console.log('Resize detected in embed mode, refreshing...');
                exitEmbedMode();
                setTimeout(() => {
                    enterEmbedMode();
                }, 100);
            }
        }, 250);
=======
 * Add floating expand button (bottom-right corner, always visible)
 */
function addFloatingExpandButton() {
    // Remove any old buttons first
    const oldButtons = document.querySelectorAll('.minimize-maximize-btn, .page-maximize-btn, .fullscreen-btn');
    oldButtons.forEach(btn => {
        console.log('Removing old button:', btn.className);
        btn.remove();
>>>>>>> e43c076 (expand correction)
    });
    
    // Only add if not already present
    if (document.querySelector('.floating-expand-btn')) {
        return;
    }
    
    console.log('Adding floating expand button...');
    
    const button = document.createElement('button');
    button.className = 'floating-expand-btn';
    button.innerHTML = '⤢'; // Two arrows expanding
    button.title = 'Toggle Fullscreen (F11)';
    button.setAttribute('aria-label', 'Toggle fullscreen');
    
    // Style the button directly to ensure it appears
    button.style.cssText = `
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
    `;
    
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
 * Enter embed mode
 */
function enterEmbedMode() {
    console.log('Entering embed mode');
    
    // Remove any lingering old buttons
    const oldButtons = document.querySelectorAll('.minimize-maximize-btn, .page-maximize-btn, .fullscreen-btn');
    oldButtons.forEach(btn => {
        console.log('Cleaning up old button in embed mode:', btn.className);
        btn.remove();
    });
    
    // Add embed-mode class to body
    document.body.classList.add('embed-mode');
    
    // Hide all MkDocs navigation and chrome
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
    
    // Convert floating button to close button (top of screen, small and slick)
    const floatingBtn = document.querySelector('.floating-expand-btn');
    if (floatingBtn) {
        floatingBtn.innerHTML = '×'; // Clear × close symbol
        floatingBtn.title = 'Close (ESC)';
        floatingBtn.setAttribute('aria-label', 'Close fullscreen');
        
        // Move to top and make small and slick
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
        `;
    }
    
    console.log('Embed mode activated');
}

/**
<<<<<<< HEAD
 * Add floating expand button (bottom-right corner, always visible)
 */
function addFloatingExpandButton() {
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
 * Enter embed mode - SAFE FOR MOBILE MKDOCS
 */
function enterEmbedMode() {
    console.log('Entering embed mode');
    
    // Clean up any old buttons that might have been added after page load
    cleanupOldButtons();
    
    // Add embed-mode class to body
    document.body.classList.add('embed-mode');
    
    // Update URL to include embed parameter (for sharing)
    const url = new URL(window.location);
    url.searchParams.set('embed', 'true');
    window.history.replaceState({}, '', url);
    
    // Check if we're on mobile (MkDocs mobile breakpoint)
    const isMobile = window.innerWidth <= 1219; // 76.1875em in px
    
    // Hide MkDocs navigation - be careful on mobile
    if (isMobile) {
        // On mobile, only hide specific elements that won't break nav functionality
        const mobileElementsToHide = ['.md-header', '.md-tabs', '.md-footer'];
        mobileElementsToHide.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
            });
        });
        
        // For mobile nav, let CSS handle the hiding to preserve functionality
        // Don't manually hide .md-nav or .md-sidebar via JS on mobile
        
    } else {
        // On desktop, safe to hide all navigation elements
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
    }
    
    // Adjust content to fill viewport - safe approach
    const container = document.querySelector('.md-container');
    const main = document.querySelector('.md-main');
    const content = document.querySelector('.md-content');
    
    // Only modify layout if elements exist and we won't break mobile
    if (container && !isMobile) {
        container.style.cssText = 'max-width: none !important; margin: 0 !important; padding: 0 !important; width: 100% !important;';
    }
    if (main && !isMobile) {
        main.style.cssText = 'max-width: none !important; margin: 0 !important; padding: 0 !important; width: 100% !important;';
    }
    if (content) {
        // Safe content modification for both mobile and desktop
        const padding = isMobile ? '0.5rem' : '1rem';
        content.style.cssText = `max-width: none !important; margin: 0 !important; padding: ${padding} !important; width: 100% !important; min-height: 100vh !important;`;
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
    
    // Show table search boxes in expanded view
    updateTableControlsVisibility();
    
    console.log('Embed mode activated');
}

/**
 * Exit embed mode - SAFE FOR MOBILE MKDOCS
 */
=======
 * Exit embed mode
 */
>>>>>>> e43c076 (expand correction)
function exitEmbedMode() {
    console.log('Exiting embed mode');
    
    // Remove embed-mode class from body
    document.body.classList.remove('embed-mode');
    
<<<<<<< HEAD
    // Remove embed parameter from URL
    const url = new URL(window.location);
    url.searchParams.delete('embed');
    url.searchParams.delete('fullscreen');
    window.history.replaceState({}, '', url);
    
    // Check if we're on mobile
    const isMobile = window.innerWidth <= 1219; // MkDocs mobile breakpoint
    
    // Show MkDocs navigation - different approach for mobile vs desktop
    if (isMobile) {
        // On mobile, only restore elements we explicitly hid
        const mobileElementsToShow = ['.md-header', '.md-tabs', '.md-footer'];
        mobileElementsToShow.forEach(selector => {
            const elements = document.querySelectorAll(selector);
            elements.forEach(el => {
                el.style.display = '';
                el.style.visibility = '';
            });
        });
        
        // Let MkDocs CSS handle nav/sidebar restoration on mobile
        
    } else {
        // On desktop, restore all navigation elements
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
    }
    
    // Reset content styling - safe approach
    const container = document.querySelector('.md-container');
    const main = document.querySelector('.md-main');
    const content = document.querySelector('.md-content');
    
    // Reset layout modifications
    if (container) container.style.cssText = '';
    if (main) main.style.cssText = '';
    if (content) content.style.cssText = '';
    
    // Convert close button back to floating expand button
    const floatingBtn = document.querySelector('.floating-expand-btn');
    if (floatingBtn) {
        floatingBtn.innerHTML = '⤢';
        floatingBtn.title = 'Toggle Fullscreen (F11)';
        floatingBtn.setAttribute('aria-label', 'Toggle fullscreen');
        
=======
    // Show all MkDocs navigation and chrome
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
    
    if (container) {
        container.style.cssText = '';
    }
    if (main) {
        main.style.cssText = '';
    }
    if (content) {
        content.style.cssText = '';
    }
    
    // Convert close button back to floating expand button (bottom-right, round)
    const floatingBtn = document.querySelector('.floating-expand-btn');
    if (floatingBtn) {
        floatingBtn.innerHTML = '⤢'; // Expand symbol
        floatingBtn.title = 'Toggle Fullscreen (F11)';
        floatingBtn.setAttribute('aria-label', 'Toggle fullscreen');
        
        // Reset to original floating button style (moved up to avoid footer)
>>>>>>> e43c076 (expand correction)
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
<<<<<<< HEAD
            font-family: inherit !important;
            line-height: 1 !important;
            touch-action: manipulation !important;
        `;
    }
    
    // Hide table search boxes in normal view
    updateTableControlsVisibility();
    
=======
        `;
    }
    
>>>>>>> e43c076 (expand correction)
    console.log('Embed mode deactivated');
}

/**
 * Add keyboard shortcuts
 */
function addKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
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

<<<<<<< HEAD
/**
 * Enhance tables with sorting and filtering
 */
function enhanceTables() {
    const tables = document.querySelectorAll('table');
    
    tables.forEach(table => {
        addTableControls(table);
        makeTableResponsive(table);
        addTableSorting(table);
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
 * Add sorting to table headers
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
 * Update table controls visibility based on embed mode
 */
function updateTableControlsVisibility() {
    const tableControls = document.querySelectorAll('.table-controls');
    const isEmbedMode = document.body.classList.contains('embed-mode');
    
    tableControls.forEach(controls => {
        if (isEmbedMode) {
            // Show search box in expanded view
            controls.style.display = 'block';
            controls.style.opacity = '1';
        } else {
            // Hide search box in normal view
            controls.style.display = 'none';
            controls.style.opacity = '0';
        }
    });
}

=======
>>>>>>> e43c076 (expand correction)
// Export functions for external use
window.embedUtils = {
    enterEmbedMode,
    exitEmbedMode,
<<<<<<< HEAD
    addFloatingExpandButton,
    enhanceTables,
    filterTable,
    sortTable,
    updateTableControlsVisibility,
    cleanupOldButtons
};
=======
    addFloatingExpandButton
};
>>>>>>> e43c076 (expand correction)
