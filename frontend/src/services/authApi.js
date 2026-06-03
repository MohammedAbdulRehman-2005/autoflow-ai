/**
 * AutoFlow AI X — Auth API Service
 * Replaces the old localStorage-only mock with real FastAPI backend calls.
 *
 * Endpoints used:
 *   POST /api/v1/auth/signup
 *   POST /api/v1/auth/login
 *   POST /api/v1/auth/refresh
 *   GET  /api/v1/auth/me
 *   POST /api/v1/auth/logout
 */

import { api, tokenStore } from './apiClient';

export const authApi = {
  /**
   * Sign up a new user.
   * Returns { user, access_token, refresh_token }
   */
  signup: async (name, email, password) => {
    const data = await api.post('/api/v1/auth/signup', { name, email, password });
    // Store tokens
    tokenStore.set(data.access_token);
    localStorage.setItem('af_refresh_token', data.refresh_token);
    return { user: data.user };
  },

  /**
   * Log in an existing user.
   * Returns { user, access_token, refresh_token }
   */
  login: async (email, password) => {
    const data = await api.post('/api/v1/auth/login', { email, password });
    tokenStore.set(data.access_token);
    localStorage.setItem('af_refresh_token', data.refresh_token);
    return { user: data.user };
  },

  /**
   * Get the currently authenticated user profile.
   * Used on app load to restore the session if a refresh token exists.
   */
  getCurrentUser: async () => {
    // If no refresh token in storage, we're definitely logged out
    const refreshToken = localStorage.getItem('af_refresh_token');
    if (!refreshToken) return null;

    // If we have no access token yet, try to refresh first
    if (!tokenStore.get()) {
      const res = await fetch(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/auth/refresh`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        }
      );
      if (!res.ok) {
        localStorage.removeItem('af_refresh_token');
        return null;
      }
      const tokenData = await res.json();
      tokenStore.set(tokenData.access_token);
      if (tokenData.refresh_token) {
        localStorage.setItem('af_refresh_token', tokenData.refresh_token);
      }
    }

    try {
      const user = await api.get('/api/v1/auth/me');
      return user;
    } catch {
      return null;
    }
  },

  /**
   * Log out: invalidates the refresh token on the server and clears local state.
   */
  logout: async () => {
    const refreshToken = localStorage.getItem('af_refresh_token');
    try {
      if (refreshToken) {
        await api.post('/api/v1/auth/logout', { refresh_token: refreshToken });
      }
    } catch (_) {
      // Best-effort: always clear local state even if server call fails
    } finally {
      tokenStore.clear();
      localStorage.removeItem('af_refresh_token');
    }
  },
};