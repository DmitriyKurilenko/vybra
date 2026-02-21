/**
 * Shared utility functions for Vybra frontend
 */

let __vybraPendingRequests = 0;
let __vybraLoadingStartedAt = 0;
const __vybraMinLoadingVisibleMs = 900;

function setGlobalLoading(isLoading) {
    window.dispatchEvent(new CustomEvent('vybra:loading', {
        detail: {
            loading: isLoading,
            pending: __vybraPendingRequests,
        }
    }));
}

function beginGlobalLoading() {
    __vybraPendingRequests += 1;
    if (__vybraPendingRequests === 1) {
        __vybraLoadingStartedAt = Date.now();
        setGlobalLoading(true);
    }
}

function endGlobalLoading() {
    __vybraPendingRequests = Math.max(0, __vybraPendingRequests - 1);
    if (__vybraPendingRequests === 0) {
        const elapsed = Date.now() - __vybraLoadingStartedAt;
        const delay = Math.max(0, __vybraMinLoadingVisibleMs - elapsed);
        setTimeout(() => {
            if (__vybraPendingRequests === 0) {
                setGlobalLoading(false);
            }
        }, delay);
    }
}

window.beginGlobalLoading = beginGlobalLoading;
window.endGlobalLoading = endGlobalLoading;

/**
 * Get authentication headers for API requests
 * @returns {Object} Headers object with Authorization and Content-Type
 */
function getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

/**
 * Check if user is authenticated and redirect if not
 * @returns {boolean} True if authenticated, false otherwise
 */
function requireAuth() {
    const token = localStorage.getItem('access_token');
    if (!token) {
        window.location.href = '/login/';
        return false;
    }
    return true;
}

/**
 * Handle 401 Unauthorized response by clearing tokens and redirecting
 */
function handleUnauthorized() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login/';
}

/**
 * Make an authenticated API request with automatic 401 handling
 * @param {string} url - API endpoint URL
 * @param {Object} options - Fetch options (method, body, etc.)
 * @returns {Promise<Response>} Fetch response
 */
async function authFetch(url, options = {}) {
    beginGlobalLoading();
    let response;
    try {
        response = await fetch(url, {
            ...options,
            headers: {
                ...getAuthHeaders(),
                ...(options.headers || {})
            }
        });
    } finally {
        endGlobalLoading();
    }

    if (response.status === 401) {
        handleUnauthorized();
        throw new Error('Unauthorized');
    }

    return response;
}
