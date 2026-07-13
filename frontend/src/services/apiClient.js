/**
 * AutoFlow AI X — API Client
 * Central HTTP client that connects the frontend to the FastAPI backend.
 *
 * Base URL reads from VITE_API_URL env var (set in .env files).
 * Falls back to localhost:8000 for local dev.
 *
 * Token strategy:
 *   - Access token  → stored in memory (window.__af_token) — never in localStorage
 *   - Refresh token → stored in localStorage (safe for 7-day sessions)
 *   - On 401: auto-refresh using refresh token, then retry the original request once
 */

const rawBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const BASE_URL = rawBaseUrl.endsWith('/') ? rawBaseUrl.slice(0, -1) : rawBaseUrl;

// ─────────────────────────────────────────────────────────────────────────────
// In-memory access token (XSS-safe — not exposed to localStorage)
// ─────────────────────────────────────────────────────────────────────────────
let _accessToken = null;

export const tokenStore = {
  get: () => _accessToken,
  set: (token) => { _accessToken = token; },
  clear: () => { _accessToken = null; },
};

// ─────────────────────────────────────────────────────────────────────────────
// Core fetch wrapper
// ─────────────────────────────────────────────────────────────────────────────
async function request(path, options = {}, retry = true) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (_accessToken) {
    headers['Authorization'] = `Bearer ${_accessToken}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  });

  // Auto-refresh on 401
  if (res.status === 401 && retry) {
    const refreshed = await _tryRefresh();
    if (refreshed) {
      return request(path, options, false); // Retry once with new token
    } else {
      tokenStore.clear();
      localStorage.removeItem('af_refresh_token');
      // Redirect to login
      window.location.href = '/login';
      throw new Error('Session expired. Please log in again.');
    }
  }

  if (!res.ok) {
    let errMsg = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (Array.isArray(body.detail)) {
        errMsg = body.detail.map(err => err.msg || JSON.stringify(err)).join(', ');
      } else {
        errMsg = body.detail?.message || body.detail || JSON.stringify(body);
      }
    } catch (_) {
      errMsg = await res.text();
    }
    throw new Error(errMsg);
  }

  // 204 No Content
  if (res.status === 204) return null;

  return res.json();
}

async function _tryRefresh() {
  const refreshToken = localStorage.getItem('af_refresh_token');
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    tokenStore.set(data.tokens.access_token);
    if (data.tokens.refresh_token) {
      localStorage.setItem('af_refresh_token', data.tokens.refresh_token);
    }
    return true;
  } catch {
    return false;
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Convenience methods
// ─────────────────────────────────────────────────────────────────────────────
export const api = {
  get:    (path, opts)   => request(path, { method: 'GET',    ...opts }),
  post:   (path, body, opts) => request(path, { method: 'POST',  body: JSON.stringify(body), ...opts }),
  put:    (path, body, opts) => request(path, { method: 'PUT',   body: JSON.stringify(body), ...opts }),
  patch:  (path, body, opts) => request(path, { method: 'PATCH', body: JSON.stringify(body), ...opts }),
  delete: (path, opts)   => request(path, { method: 'DELETE', ...opts }),
};
