/**
 * Main JavaScript file for Safe Campus Platform
 * Handles common functionality across the application
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    initializeTooltips();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize auto-save functionality
    initializeAutoSave();
    
    // Initialize accessibility features
    initializeAccessibility();
  
    // Setup navbar behaviour and active state
    setupNavbar();

    // Add fade-in animation to main content
    document.querySelector('main')?.classList.add('fade-in');

    // Setup back-to-top button
    setupBackToTop();
});

/**
 * Initialize Bootstrap tooltips
 */
function initializeTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

/**
 * Initialize form validation
 */
function initializeFormValidation() {
    // Real-time validation for forms
    const forms = document.querySelectorAll('.needs-validation');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
                
                // Focus on first invalid field
                const firstInvalid = form.querySelector(':invalid');
                if (firstInvalid) {
                    firstInvalid.focus();
                }
            }
            
            form.classList.add('was-validated');
        });
        
        // Real-time validation on input
        const inputs = form.querySelectorAll('input, textarea, select');
        inputs.forEach(function(input) {
            input.addEventListener('blur', function() {
                validateField(input);
            });
            
            input.addEventListener('input', function() {
                if (input.classList.contains('is-invalid')) {
                    validateField(input);
                }
            });
        });
    });
}

/**
 * Validate individual form field
 * @param {HTMLElement} field - The form field to validate
 */
function validateField(field) {
    const isValid = field.checkValidity();
    
    field.classList.remove('is-valid', 'is-invalid');
    field.classList.add(isValid ? 'is-valid' : 'is-invalid');
    
    // Show/hide custom error messages
    const errorDiv = field.parentNode.querySelector('.invalid-feedback');
    if (errorDiv && !isValid) {
        errorDiv.textContent = field.validationMessage;
    }
}

/**
 * Initialize auto-save functionality for forms
 */
function initializeAutoSave() {
    const autoSaveForms = document.querySelectorAll('[data-auto-save]');
    
    autoSaveForms.forEach(function(form) {
        const formId = form.id || 'auto-save-form';
        
        // Load saved data
        loadFormData(form, formId);
        
        // Save data on input change
        form.addEventListener('input', debounce(function() {
            saveFormData(form, formId);
        }, 1000));
    });
}

/**
 * Save form data to localStorage
 * @param {HTMLFormElement} form - The form to save
 * @param {string} formId - Unique identifier for the form
 */
function saveFormData(form, formId) {
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        if (key !== 'csrf_token') { // Don't save CSRF tokens
            data[key] = value;
        }
    }
    
    localStorage.setItem(`form_${formId}`, JSON.stringify(data));
    
    // Show save indicator
    showSaveIndicator();
}

/**
 * Load form data from localStorage
 * @param {HTMLFormElement} form - The form to populate
 * @param {string} formId - Unique identifier for the form
 */
function loadFormData(form, formId) {
    const savedData = localStorage.getItem(`form_${formId}`);
    
    if (savedData) {
        try {
            const data = JSON.parse(savedData);
            
            Object.keys(data).forEach(function(key) {
                const field = form.querySelector(`[name="${key}"]`);
                if (field && field.type !== 'hidden') {
                    if (field.type === 'checkbox' || field.type === 'radio') {
                        field.checked = data[key] === 'on' || data[key] === field.value;
                    } else {
                        field.value = data[key];
                    }
                }
            });
        } catch (e) {
            console.warn('Failed to load saved form data:', e);
        }
    }
}

/**
 * Clear saved form data
 * @param {string} formId - Unique identifier for the form
 */
function clearSavedFormData(formId) {
    localStorage.removeItem(`form_${formId}`);
}

/**
 * Show save indicator
 */
function showSaveIndicator() {
    // Create or update save indicator
    let indicator = document.querySelector('.save-indicator');
    
    if (!indicator) {
        indicator = document.createElement('div');
        indicator.className = 'save-indicator position-fixed top-0 end-0 m-3 p-2 bg-success text-white rounded';
        indicator.style.zIndex = '9999';
        indicator.innerHTML = '<i class="fas fa-check me-1"></i>Saved';
        document.body.appendChild(indicator);
    }
    
    indicator.style.display = 'block';
    
    // Hide after 2 seconds
    setTimeout(function() {
        indicator.style.display = 'none';
    }, 2000);
}

/**
 * Handle navbar interactions: highlight current page and
 * collapse the menu after a selection on mobile devices.
 */
function setupNavbar() {
    const navbar = document.getElementById('navbarNav');
    if (!navbar) {
        return;
    }

    const links = navbar.querySelectorAll('.nav-link');

    // If no link is marked active server-side, highlight based on URL path
    if (!navbar.querySelector('.nav-link.active')) {
        const currentPath = window.location.pathname;
        for (const link of links) {
            const linkPath = link.getAttribute('href');
            if (linkPath && linkPath.split('#')[0] === currentPath) {
                link.classList.add('active');
                break;
            }
        }
    }

    // Collapse navbar when a link is clicked (useful on mobile)
    links.forEach(function(link) {
        link.addEventListener('click', function() {
            if (navbar.classList.contains('show')) {
                new bootstrap.Collapse(navbar, { toggle: false }).hide();
            }
        });
    });
}


/**
 * Initialize accessibility features
 */
function initializeAccessibility() {
    // Add keyboard navigation for custom components
    addKeyboardNavigation();
    
    // Announce dynamic content changes
    setupLiveRegions();
    
    // Focus management for modals
    setupModalFocus();
}

/**
 * Back to top button functionality
 */
function setupBackToTop() {
    const btn = document.getElementById('back-to-top');
    if (!btn) return;

    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            btn.style.display = 'flex';
        } else {
            btn.style.display = 'none';
        }
    });

    btn.addEventListener('click', function() {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

/**
 * Add keyboard navigation support
 */
function addKeyboardNavigation() {
    // Handle Enter key on clickable elements
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Enter') {
            const target = event.target;
            
            if (target.classList.contains('clickable') || target.getAttribute('role') === 'button') {
                target.click();
            }
        }
    });
}

/**
 * Setup live regions for screen readers
 */
function setupLiveRegions() {
    // Create live region for announcements
    const liveRegion = document.createElement('div');
    liveRegion.setAttribute('aria-live', 'polite');
    liveRegion.setAttribute('aria-atomic', 'true');
    liveRegion.className = 'sr-only';
    liveRegion.id = 'live-region';
    document.body.appendChild(liveRegion);
    
    // Function to announce messages
    window.announceToScreenReader = function(message) {
        liveRegion.textContent = message;
        
        // Clear after announcement
        setTimeout(function() {
            liveRegion.textContent = '';
        }, 1000);
    };
}

/**
 * Setup focus management for modals
 */
function setupModalFocus() {
    document.addEventListener('shown.bs.modal', function(event) {
        const modal = event.target;
        const focusableElements = modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        if (focusableElements.length > 0) {
            focusableElements[0].focus();
        }
    });
}

/**
 * Utility function to debounce function calls
 * @param {Function} func - Function to debounce
 * @param {number} wait - Wait time in milliseconds
 * @returns {Function} Debounced function
 */
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = function() {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

/**
 * Show loading state on elements
 * @param {HTMLElement} element - Element to show loading state
 */
function showLoading(element) {
    element.classList.add('loading');
    element.setAttribute('aria-busy', 'true');
    
    const originalText = element.textContent;
    element.setAttribute('data-original-text', originalText);
    
    if (element.tagName === 'BUTTON') {
        element.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Loading...';
        element.disabled = true;
    }
}

/**
 * Hide loading state on elements
 * @param {HTMLElement} element - Element to hide loading state
 */
function hideLoading(element) {
    element.classList.remove('loading');
    element.removeAttribute('aria-busy');
    
    const originalText = element.getAttribute('data-original-text');
    if (originalText && element.tagName === 'BUTTON') {
        element.textContent = originalText;
        element.disabled = false;
    }
}

/**
 * Display notification messages
 * @param {string} message - Message to display
 * @param {string} type - Type of notification (success, error, info, warning)
 * @param {number} duration - Duration to show notification (default: 5000ms)
 */
function showNotification(message, type = 'info', duration = 5000) {
    const alertClass = type === 'error' ? 'danger' : type;
    const iconClass = {
        'success': 'fas fa-check-circle',
        'error': 'fas fa-exclamation-circle',
        'warning': 'fas fa-exclamation-triangle',
        'info': 'fas fa-info-circle'
    }[type] || 'fas fa-info-circle';
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${alertClass} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        <i class="${iconClass} me-2"></i>${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto-dismiss after duration
    setTimeout(function() {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
    
    // Announce to screen readers
    if (window.announceToScreenReader) {
        window.announceToScreenReader(message);
    }
}

/**
 * Confirm dialog with custom styling
 * @param {string} message - Confirmation message
 * @param {Function} onConfirm - Callback for confirmation
 * @param {Function} onCancel - Callback for cancellation
 */
function showConfirmDialog(message, onConfirm, onCancel) {
    const modal = document.createElement('div');
    modal.className = 'modal fade';
    modal.innerHTML = `
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Confirm Action</h5>
                </div>
                <div class="modal-body">
                    <p>${message}</p>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" id="confirmBtn">Confirm</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    const bsModal = new bootstrap.Modal(modal);
    
    modal.querySelector('#confirmBtn').addEventListener('click', function() {
        bsModal.hide();
        if (onConfirm) onConfirm();
    });
    
    modal.addEventListener('hidden.bs.modal', function() {
        modal.remove();
        if (onCancel) onCancel();
    });
    
    bsModal.show();
}

// Export functions for use in other scripts
window.SafeCampus = {
    showLoading,
    hideLoading,
    showNotification,
    showConfirmDialog,
    announceToScreenReader: window.announceToScreenReader,
    debounce,
    validateField,
    saveFormData,
    loadFormData,
    clearSavedFormData
};
