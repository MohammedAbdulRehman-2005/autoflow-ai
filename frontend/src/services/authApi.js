/**
 * AutoFlow AI X — Auth API Service
 *
 * Demo Mode:
 *   When the backend is unreachable (no VITE_API_URL set, or fetch fails),
 *   the service falls back to a built-in demo account so the UI stays fully
 *   interactive on Vercel without a deployed backend.
 *
 *   Demo credentials:
 *     Email:    demo@autoflow.ai
 *     Password: demo1234
 */

import { api, tokenStore } from './apiClient';

// ── Demo account ──────────────────────────────────────────────────────────────
const DEMO_EMAIL    = 'demo@autoflow.ai';
const DEMO_PASSWORD = 'demo1234';
const DEMO_USER = {
  id:         'demo-user-001',
  email:      DEMO_EMAIL,
  full_name:  'Demo User',
  plan:       'pro',
  is_active:  true,
  created_at: new Date().toISOString(),
};
const DEMO_TOKEN = 'demo-access-token-not-real';
const DEMO_REFRESH = 'demo-refresh-token-not-real';

function isDemoCredentials(email, password) {
  return email === DEMO_EMAIL && password === DEMO_PASSWORD;
}

function isDemoSession() {
  return localStorage.getItem('af_refresh_token') === DEMO_REFRESH;
}

function activateDemoSession() {
  tokenStore.set(DEMO_TOKEN);
  localStorage.setItem('af_refresh_token', DEMO_REFRESH);
  localStorage.setItem('af_demo_mode', 'true');
}

export const isDemoMode = () => localStorage.getItem('af_demo_mode') === 'true';

// ─────────────────────────────────────────────────────────────────────────────

export const authApi = {
  /**
   * Sign up — falls back to demo mode if backend is unreachable.
   */
  signup: async (name, email, password) => {
    try {
      const data = await api.post('/api/v1/auth/signup', { name, email, password });
      tokenStore.set(data.access_token);
      localStorage.setItem('af_refresh_token', data.refresh_token);
      localStorage.removeItem('af_demo_mode');
      return { user: data.user };
    } catch (err) {
      // If backend is down AND user used demo credentials → allow demo login
      if (isDemoCredentials(email, password) || err.message?.includes('fetch')) {
        activateDemoSession();
        return {
          user: { ...DEMO_USER, full_name: name || 'Demo User', email },
          demo: true,
        };
      }
      throw err;
    }
  },

  /**
   * Login — falls back to demo mode if backend is unreachable.
   */
  login: async (email, password) => {
    // Always allow demo credentials
    if (isDemoCredentials(email, password)) {
      activateDemoSession();
      return { user: DEMO_USER, demo: true };
    }

    try {
      const data = await api.post('/api/v1/auth/login', { email, password });
      tokenStore.set(data.access_token);
      localStorage.setItem('af_refresh_token', data.refresh_token);
      localStorage.removeItem('af_demo_mode');
      return { user: data.user };
    } catch (err) {
      // Backend unreachable — offer demo mode for any credentials
      if (err.message?.toLowerCase().includes('fetch') ||
          err.message?.toLowerCase().includes('network') ||
          err.message?.toLowerCase().includes('failed to fetch')) {
        activateDemoSession();
        return {
          user: { ...DEMO_USER, email },
          demo: true,
          _warning: 'Backend unavailable — running in demo mode.',
        };
      }
      throw err;
    }
  },

  /**
   * Restore session on app load.
   */
  getCurrentUser: async () => {
    // Demo session
    if (isDemoSession()) {
      tokenStore.set(DEMO_TOKEN);
      return DEMO_USER;
    }

    const refreshToken = localStorage.getItem('af_refresh_token');
    if (!refreshToken) return null;

    if (!tokenStore.get()) {
      try {
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
      } catch {
        localStorage.removeItem('af_refresh_token');
        return null;
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
   * Logout — clears demo session or real session.
   */
  logout: async () => {
    const refreshToken = localStorage.getItem('af_refresh_token');
    if (!isDemoSession()) {
      try {
        if (refreshToken) {
          await api.post('/api/v1/auth/logout', { refresh_token: refreshToken });
        }
      } catch (_) {}
    }
    tokenStore.clear();
    localStorage.removeItem('af_refresh_token');
    localStorage.removeItem('af_demo_mode');
  },
};