/**
 * Shared utility functions for Vybra frontend
 */

let __vybraPendingRequests = 0;
let __vybraLoadingStartedAt = 0;
const __vybraMinLoadingVisibleMs = 900;
let __vybraRefreshPromise = null;
const __vybraAuthMarkerCookie = 'vybra_logged_in=1';

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
 * @returns {Object} Headers object
 */
function getAuthHeaders(extraHeaders = {}) {
    return {
        'Content-Type': 'application/json',
        ...extraHeaders,
    };
}

function hasAuthMarker() {
    return document.cookie
        .split(';')
        .map((chunk) => chunk.trim())
        .includes(__vybraAuthMarkerCookie);
}

/**
 * Check if user is authenticated and redirect if not
 * @returns {boolean} True if authenticated, false otherwise
 */
function requireAuth() {
    if (!hasAuthMarker()) {
        window.location.href = '/login/';
        return false;
    }
    return true;
}

/**
 * Handle 401 Unauthorized response by clearing tokens and redirecting
 */
function handleUnauthorized() {
    fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
        },
        body: '{}',
    }).catch(() => {});
    document.cookie = 'vybra_logged_in=; Max-Age=0; Path=/; SameSite=Lax';
    window.location.href = '/login/';
}

async function refreshAccessToken() {
    if (__vybraRefreshPromise) {
        return __vybraRefreshPromise;
    }

    __vybraRefreshPromise = fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
        },
        body: '{}',
    })
        .then((response) => response.ok)
        .catch(() => false)
        .finally(() => {
            __vybraRefreshPromise = null;
        });

    return __vybraRefreshPromise;
}

/**
 * Make an authenticated API request with automatic 401 handling
 * @param {string} url - API endpoint URL
 * @param {Object} options - Fetch options (method, body, etc.)
 * @returns {Promise<Response>} Fetch response
 */
async function authFetch(url, options = {}) {
    beginGlobalLoading();
    try {
        let response = await fetch(url, {
            ...options,
            credentials: 'same-origin',
            headers: {
                ...getAuthHeaders(options.headers || {}),
            },
        });

        if (response.status === 401) {
            const refreshed = await refreshAccessToken();
            if (refreshed) {
                response = await fetch(url, {
                    ...options,
                    credentials: 'same-origin',
                    headers: {
                        ...getAuthHeaders(options.headers || {}),
                    },
                });
            }
        }

        if (response.status === 401) {
            handleUnauthorized();
            throw new Error('Unauthorized');
        }

        return response;
    } finally {
        endGlobalLoading();
    }
}
