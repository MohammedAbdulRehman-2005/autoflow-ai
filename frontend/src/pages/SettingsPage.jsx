/**
 * AutoFlow AI — Settings & Integrations Page
 *
 * Displays connection cards for all supported integrations.
 * OAuth providers redirect to the backend which redirects back here with ?status=connected.
 * Stripe uses a modal to enter API keys directly.
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSearchParams } from 'react-router-dom';
import {
  CheckCircle2, XCircle, Plug, Unplug, ExternalLink, Key,
  AlertCircle, Loader2, X, Eye, EyeOff, RefreshCw,
} from 'lucide-react';
import { workflowApi } from '../services/workflowApi';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Integration catalogue ────────────────────────────────────────────────────
const INTEGRATIONS = [
  {
    id: 'google',
    label: 'Google Suite',
    description: 'Gmail, Google Sheets & Google Calendar — all in one connection.',
    icon: '🔴',
    gradient: 'from-red-500/20 to-yellow-500/10',
    border: 'border-red-500/20',
    glow: 'shadow-red-500/10',
    services: ['gmail', 'google_sheets', 'google_calendar'],
    type: 'oauth',
    badge: 'Most Used',
  },
  {
    id: 'slack',
    label: 'Slack',
    description: 'Post messages to channels, notify teams on workflow events.',
    icon: '💜',
    gradient: 'from-purple-500/20 to-purple-900/10',
    border: 'border-purple-500/20',
    glow: 'shadow-purple-500/10',
    services: ['slack'],
    type: 'oauth',
  },
  {
    id: 'notion',
    label: 'Notion',
    description: 'Read and write Notion databases and pages automatically.',
    icon: '⬛',
    gradient: 'from-slate-500/20 to-slate-900/10',
    border: 'border-slate-500/20',
    glow: 'shadow-slate-500/10',
    services: ['notion'],
    type: 'oauth',
  },
  {
    id: 'hubspot',
    label: 'HubSpot CRM',
    description: 'Create contacts, update deals, trigger sequences from workflows.',
    icon: '🟠',
    gradient: 'from-orange-500/20 to-orange-900/10',
    border: 'border-orange-500/20',
    glow: 'shadow-orange-500/10',
    services: ['hubspot'],
    type: 'oauth',
  },
  {
    id: 'salesforce',
    label: 'Salesforce',
    description: 'Sync leads, update records, and trigger Salesforce automations.',
    icon: '🔵',
    gradient: 'from-blue-500/20 to-blue-900/10',
    border: 'border-blue-500/20',
    glow: 'shadow-blue-500/10',
    services: ['salesforce'],
    type: 'oauth',
  },
  {
    id: 'stripe',
    label: 'Stripe',
    description: 'React to payments, subscriptions, and failed charges in real time.',
    icon: '💳',
    gradient: 'from-violet-500/20 to-violet-900/10',
    border: 'border-violet-500/20',
    glow: 'shadow-violet-500/10',
    services: ['stripe'],
    type: 'apikey',
  },
];

// ── Stripe API Key Modal ─────────────────────────────────────────────────────
function StripeModal({ onClose, onSuccess }) {
  const [secretKey, setSecretKey] = useState('');
  const [webhookSecret, setWebhookSecret] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!secretKey.startsWith('sk_')) {
      setError('Secret key must start with sk_live_ or sk_test_');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${API_BASE}/api/v1/integrations/stripe/connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ secret_key: secretKey, webhook_secret: webhookSecret }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Failed');
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        onClick={e => e.stopPropagation()}
        className="bg-slate-900 border border-white/10 rounded-2xl p-6 w-full max-w-md shadow-2xl"
      >
        <div className="flex justify-between items-center mb-5">
          <div className="flex items-center gap-2">
            <span className="text-xl">💳</span>
            <h3 className="text-white font-bold text-sm">Connect Stripe</h3>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white cursor-pointer"><X size={16} /></button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-slate-400 font-medium mb-1.5 block">
              Secret Key <span className="text-rose-400">*</span>
            </label>
            <div className="relative">
              <input
                type={showKey ? 'text' : 'password'}
                value={secretKey}
                onChange={e => setSecretKey(e.target.value)}
                placeholder="sk_live_... or sk_test_..."
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-xs text-white placeholder-slate-600 outline-none focus:border-violet-500/50 pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowKey(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white cursor-pointer"
              >
                {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
            <p className="text-[10px] text-slate-600 mt-1">Find this in Stripe Dashboard → Developers → API Keys</p>
          </div>

          <div>
            <label className="text-xs text-slate-400 font-medium mb-1.5 block">
              Webhook Signing Secret <span className="text-slate-600">(optional)</span>
            </label>
            <input
              type="password"
              value={webhookSecret}
              onChange={e => setWebhookSecret(e.target.value)}
              placeholder="whsec_..."
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-xs text-white placeholder-slate-600 outline-none focus:border-violet-500/50"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-xl px-3 py-2">
              <AlertCircle size={12} />
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 text-white text-xs font-bold cursor-pointer disabled:opacity-50 transition-all flex items-center justify-center gap-2"
          >
            {loading ? <><Loader2 size={13} className="animate-spin" /> Connecting...</> : <><Key size={13} /> Connect Stripe</>}
          </button>
        </form>
      </motion.div>
    </motion.div>
  );
}

// ── Integration Card ─────────────────────────────────────────────────────────
function IntegrationCard({ integration, connectedServices, onConnect, onDisconnect, isLoading }) {
  const isConnected = integration.services.some(s => connectedServices.has(s));
  const connectedInfo = connectedServices.has(integration.id)
    ? `Connected`
    : integration.services.find(s => connectedServices.has(s))
    ? `Connected`
    : null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className={`relative rounded-2xl border bg-gradient-to-br ${integration.gradient} ${integration.border} p-5 shadow-lg ${integration.glow} overflow-hidden transition-all hover:shadow-xl`}
    >
      {/* Badge */}
      {integration.badge && (
        <span className="absolute top-3 right-3 text-[9px] font-bold tracking-wider text-cyan-400 bg-cyan-500/10 border border-cyan-500/20 rounded-full px-2 py-0.5 uppercase">
          {integration.badge}
        </span>
      )}

      <div className="flex items-start gap-3 mb-4">
        <span className="text-2xl">{integration.icon}</span>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-bold text-white">{integration.label}</h3>
          <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">{integration.description}</p>
        </div>
      </div>

      {/* Services covered */}
      <div className="flex flex-wrap gap-1 mb-4">
        {integration.services.map(s => (
          <span key={s} className="text-[9px] font-mono text-slate-500 bg-white/5 rounded px-1.5 py-0.5">
            {s.replace('_', ' ')}
          </span>
        ))}
      </div>

      {/* Status + Button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          {isConnected ? (
            <>
              <CheckCircle2 size={12} className="text-emerald-400" />
              <span className="text-[11px] text-emerald-400 font-semibold">Connected</span>
            </>
          ) : (
            <>
              <XCircle size={12} className="text-slate-600" />
              <span className="text-[11px] text-slate-500">Not connected</span>
            </>
          )}
        </div>

        {isConnected ? (
          <button
            onClick={() => onDisconnect(integration.services[0])}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-[11px] font-semibold text-rose-400 hover:text-rose-300 border border-rose-500/20 hover:border-rose-500/40 rounded-lg px-3 py-1.5 cursor-pointer transition-all disabled:opacity-50"
          >
            {isLoading ? <Loader2 size={11} className="animate-spin" /> : <Unplug size={11} />}
            Disconnect
          </button>
        ) : (
          <button
            onClick={() => onConnect(integration)}
            disabled={isLoading}
            className="flex items-center gap-1.5 text-[11px] font-bold text-white bg-white/10 hover:bg-white/15 border border-white/10 hover:border-white/20 rounded-lg px-3 py-1.5 cursor-pointer transition-all disabled:opacity-50"
          >
            {isLoading ? <Loader2 size={11} className="animate-spin" /> : <Plug size={11} />}
            Connect
          </button>
        )}
      </div>
    </motion.div>
  );
}

// ── Main Settings Page ───────────────────────────────────────────────────────
export default function SettingsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [connectedServices, setConnectedServices] = useState(new Set());
  const [loadingId, setLoadingId] = useState(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [toast, setToast] = useState(null);
  const [showStripeModal, setShowStripeModal] = useState(false);

  // Show toast from URL param (after OAuth redirect)
  useEffect(() => {
    const integration = searchParams.get('integration');
    const status = searchParams.get('status');
    const msg = searchParams.get('msg');
    if (status === 'connected') {
      showToast(`✅ ${integration?.charAt(0).toUpperCase() + integration?.slice(1)} connected successfully!`, 'success');
      loadIntegrations();
    } else if (status === 'error') {
      showToast(`❌ Failed to connect ${integration}: ${msg || 'Unknown error'}`, 'error');
    }
    // Clean the URL
    if (status) setSearchParams({});
  }, []);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const loadIntegrations = async () => {
    setIsRefreshing(true);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${API_BASE}/api/v1/integrations/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        const services = new Set(data.map(i => i.service));
        // Google OAuth covers all Google services
        if (services.has('gmail')) {
          services.add('google_sheets');
          services.add('google_calendar');
          services.add('google');
        }
        setConnectedServices(services);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => { loadIntegrations(); }, []);

  const handleConnect = async (integration) => {
    if (integration.type === 'apikey') {
      if (integration.id === 'stripe') setShowStripeModal(true);
      return;
    }

    // OAuth — redirect to backend
    setLoadingId(integration.id);
    const token = localStorage.getItem('access_token');
    window.location.href = `${API_BASE}/api/v1/integrations/${integration.id}/connect?token=${token}`;
  };

  const handleDisconnect = async (service) => {
    setLoadingId(service);
    try {
      const token = localStorage.getItem('access_token');
      const res = await fetch(`${API_BASE}/api/v1/integrations/${service}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        showToast(`Disconnected ${service} successfully.`, 'success');
        await loadIntegrations();
      }
    } catch (e) {
      showToast(`Failed to disconnect: ${e.message}`, 'error');
    } finally {
      setLoadingId(null);
    }
  };

  const connectedCount = INTEGRATIONS.filter(i =>
    i.services.some(s => connectedServices.has(s))
  ).length;

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-display">Settings</h1>
          <p className="text-sm text-slate-400 mt-1">Manage your connected apps and integrations.</p>
        </div>
        <button
          onClick={loadIntegrations}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-4 py-2 border border-white/10 rounded-xl bg-white/5 hover:bg-white/8 text-slate-300 hover:text-white text-xs font-semibold cursor-pointer transition-all"
        >
          <RefreshCw size={13} className={isRefreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Stats bar */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Integrations', value: INTEGRATIONS.length },
          { label: 'Connected', value: connectedCount, color: 'text-emerald-400' },
          { label: 'Available', value: INTEGRATIONS.length - connectedCount, color: 'text-slate-400' },
        ].map(stat => (
          <div key={stat.label} className="rounded-2xl border border-white/5 bg-white/3 px-5 py-4 backdrop-blur-sm">
            <p className="text-xs text-slate-500 font-medium">{stat.label}</p>
            <p className={`text-2xl font-black mt-1 ${stat.color || 'text-white'}`}>{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Integrations Grid */}
      <div>
        <h2 className="text-sm font-bold text-slate-300 mb-4 flex items-center gap-2">
          <Plug size={14} className="text-cyan-400" />
          App Integrations
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {INTEGRATIONS.map(integration => (
            <IntegrationCard
              key={integration.id}
              integration={integration}
              connectedServices={connectedServices}
              onConnect={handleConnect}
              onDisconnect={handleDisconnect}
              isLoading={loadingId === integration.id || loadingId === integration.services[0]}
            />
          ))}
        </div>
      </div>

      {/* Help section */}
      <div className="rounded-2xl border border-cyan-500/15 bg-cyan-500/5 p-5">
        <div className="flex items-start gap-3">
          <AlertCircle size={16} className="text-cyan-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-bold text-cyan-300 mb-1">How OAuth connections work</p>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Clicking <strong className="text-white">Connect</strong> will open the provider's official login page.
              After you authorize AutoFlow AI, you'll be redirected back here automatically.
              Your credentials are encrypted with AES-256 and never stored in plain text.
            </p>
          </div>
        </div>
      </div>

      {/* Stripe Modal */}
      <AnimatePresence>
        {showStripeModal && (
          <StripeModal
            onClose={() => setShowStripeModal(false)}
            onSuccess={() => {
              setShowStripeModal(false);
              showToast('✅ Stripe connected successfully!', 'success');
              loadIntegrations();
            }}
          />
        )}
      </AnimatePresence>

      {/* Toast notification */}
      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 20, x: '-50%' }}
            animate={{ opacity: 1, y: 0, x: '-50%' }}
            exit={{ opacity: 0, y: 20, x: '-50%' }}
            className={`fixed bottom-6 left-1/2 z-50 flex items-center gap-2 px-4 py-3 rounded-2xl text-xs font-semibold shadow-2xl border
              ${toast.type === 'success'
                ? 'bg-emerald-950 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-950 border-rose-500/30 text-rose-300'
              }`}
          >
            {toast.type === 'success' ? <CheckCircle2 size={13} /> : <XCircle size={13} />}
            {toast.message}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
