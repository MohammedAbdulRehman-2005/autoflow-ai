import { api, tokenStore } from './apiClient';

export const isDemoMode = () => false;

// ─────────────────────────────────────────────────────────────────────────────


export const authApi = {
  signup: async (name, email, password) => {
    const data = await api.post('/api/v1/auth/signup', { full_name: name, email, password });
    tokenStore.set(data.tokens.access_token);
    localStorage.setItem('af_refresh_token', data.tokens.refresh_token);
    return { user: data.user };
  },

  login: async (email, password) => {
    const data = await api.post('/api/v1/auth/login', { email, password });
    tokenStore.set(data.tokens.access_token);
    localStorage.setItem('af_refresh_token', data.tokens.refresh_token);
    return { user: data.user };
  },

  getCurrentUser: async () => {
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
        tokenStore.set(tokenData.tokens.access_token);
        if (tokenData.tokens.refresh_token) {
          localStorage.setItem('af_refresh_token', tokenData.tokens.refresh_token);
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

  logout: async () => {
    const refreshToken = localStorage.getItem('af_refresh_token');
    try {
      if (refreshToken) {
        await api.post('/api/v1/auth/logout', { refresh_token: refreshToken });
      }
    } catch (_) {}
    tokenStore.clear();
    localStorage.removeItem('af_refresh_token');
  },
};