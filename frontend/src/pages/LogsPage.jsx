import React, { useState, useEffect, useCallback } from 'react';
import {
  Search, ListTodo, CheckCircle2, XCircle, AlertTriangle, RotateCw,
  Terminal, Activity, SlidersHorizontal, ChevronRight, ChevronDown, RefreshCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { workflowApi } from '../services/workflowApi';

const STATUS_STYLES = {
  success:  'bg-emerald-500/10 text-emerald-400 border border-emerald-500/15',
  running:  'bg-blue-500/10 text-blue-400 border border-blue-500/15 animate-pulse',
  failed:   'bg-rose-500/10 text-rose-400 border border-rose-500/15',
  pending:  'bg-amber-500/10 text-amber-400 border border-amber-500/15 animate-pulse',
  retrying: 'bg-purple-500/10 text-purple-400 border border-purple-500/15',
};
const STATUS_ICONS = {
  success:  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />,
  running:  <Activity className="h-3.5 w-3.5 text-blue-400 shrink-0 animate-spin" />,
  failed:   <XCircle className="h-3.5 w-3.5 text-rose-400 shrink-0" />,
  pending:  <Activity className="h-3.5 w-3.5 text-amber-400 shrink-0 animate-pulse" />,
  retrying: <RefreshCw className="h-3.5 w-3.5 text-purple-400 shrink-0 animate-spin" />,
};

export default function LogsPage() {
  const [workflows, setWorkflows]       = useState([]);
  const [allRuns, setAllRuns]           = useState([]);   // flat list { run, workflow_name }
  const [isLoading, setIsLoading]       = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError]               = useState(null);
  const [searchTerm, setSearchTerm]     = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [expandedId, setExpandedId]     = useState(null);
  const [stepLogs, setStepLogs]         = useState({});   // { run_id: [steps] }
  const [loadingSteps, setLoadingSteps] = useState({});

  // ── Load all runs ──────────────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    try {
      setError(null);
      const wfData = await workflowApi.list({ limit: 30 });
      const wfList = wfData?.workflows || wfData?.items || [];
      setWorkflows(wfList);

      const flat = [];
      await Promise.all(
        wfList.map(async (wf) => {
          try {
            const runsData = await workflowApi.listRuns(wf.id, { limit: 20 });
            const runs = runsData?.runs || [];
            runs.forEach(r => flat.push({ ...r, workflow_name: wf.name, workflow_id: wf.id }));
          } catch (_) {}
        })
      );
      flat.sort((a, b) => new Date(b.created_at || b.started_at) - new Date(a.created_at || a.started_at));
      setAllRuns(flat);
    } catch (err) {
      setError(err.message || 'Failed to load logs.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleRefresh = () => { setIsRefreshing(true); loadData(); };

  // ── Expand run → load step logs ────────────────────────────────────────────
  const toggleExpand = async (run) => {
    const isOpen = expandedId === run.id;
    setExpandedId(isOpen ? null : run.id);
    if (!isOpen && !stepLogs[run.id]) {
      setLoadingSteps(prev => ({ ...prev, [run.id]: true }));
      try {
        const detail = await workflowApi.getRun(run.workflow_id, run.id);
        setStepLogs(prev => ({ ...prev, [run.id]: detail.step_logs || [] }));
      } catch (_) {
        setStepLogs(prev => ({ ...prev, [run.id]: [] }));
      } finally {
        setLoadingSteps(prev => ({ ...prev, [run.id]: false }));
      }
    }
  };

  // ── Filter ────────────────────────────────────────────────────────────────
  const filtered = allRuns.filter(run => {
    const matchSearch = (run.workflow_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                        (run.trigger_type || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
                        (run.id || '').includes(searchTerm);
    const matchStatus = statusFilter === 'All' || run.status === statusFilter.toLowerCase();
    return matchSearch && matchStatus;
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-3">
          <RotateCw className="h-8 w-8 text-cyan-400 animate-spin mx-auto" />
          <p className="text-slate-400 text-sm">Loading execution logs...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 select-none text-left">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-display flex items-center gap-2">
            <ListTodo className="h-8 w-8 text-cyan-400" />
            <span>Execution Monitoring</span>
          </h1>
          <p className="text-sm text-slate-400 mt-1 font-sans">
            Live run history, step logs, and diagnostics from the backend.
          </p>
        </div>
        <div className="flex items-center space-x-2.5 self-start sm:self-auto">
          <button onClick={handleRefresh}
            className="flex items-center space-x-1.5 px-3.5 py-2 border border-white/10 bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white rounded-xl text-xs font-semibold cursor-pointer shadow-sm transition-all">
            <RotateCw className={`h-4.5 w-4.5 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Force Sync</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-xl px-4 py-3">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center">
        <div className="flex items-center space-x-1.5 flex-wrap gap-1.5">
          {['All', 'Success', 'Running', 'Failed', 'Pending'].map(s => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-bold cursor-pointer transition-all ${statusFilter === s ? 'bg-gradient-to-r from-blue-600 to-cyan-500 text-white' : 'bg-white/5 border border-white/10 text-slate-400 hover:text-white hover:border-white/20'}`}>
              {s.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="relative w-full md:w-80">
          <Search className="absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input type="text" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search workflow, trigger, or run ID..."
            className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pr-4 pl-10 text-xs text-white placeholder-slate-500 outline-none hover:border-white/20 focus:border-cyan-500/50" />
        </div>
      </div>

      {/* Stats summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Runs',  value: allRuns.length,                              color: 'text-white' },
          { label: 'Successful',  value: allRuns.filter(r => r.status === 'success').length, color: 'text-emerald-400' },
          { label: 'Failed',      value: allRuns.filter(r => r.status === 'failed').length,  color: 'text-rose-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="border border-white/10 rounded-2xl bg-white/5 p-4 text-center backdrop-blur-lg">
            <span className={`text-2xl font-black font-display ${color}`}>{value}</span>
            <p className="text-xs text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      {/* Logs table */}
      <div className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg shadow-md">
        {filtered.length === 0 ? (
          <div className="text-center py-20 text-slate-500 flex flex-col items-center justify-center space-y-3">
            <SlidersHorizontal className="h-8 w-8 text-slate-600 animate-pulse" />
            <span className="text-sm">No runs match the current filters.</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/10 text-slate-500 font-display uppercase tracking-wider text-[10px]">
                  <th className="pb-3 pt-1 w-8" />
                  <th className="pb-3 pt-1 font-semibold">WORKFLOW</th>
                  <th className="pb-3 pt-1 font-semibold">STATUS</th>
                  <th className="pb-3 pt-1 font-semibold">TRIGGER</th>
                  <th className="pb-3 pt-1 font-semibold text-right">STARTED</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {filtered.map((run) => {
                  const isExpanded = expandedId === run.id;
                  const steps = stepLogs[run.id] || [];
                  const isLoadingStep = loadingSteps[run.id];
                  const statusStyle = STATUS_STYLES[run.status] || STATUS_STYLES.pending;
                  const statusIcon  = STATUS_ICONS[run.status]  || STATUS_ICONS.pending;

                  return (
                    <React.Fragment key={run.id}>
                      <tr className={`hover:bg-white/5 transition-colors cursor-pointer ${isExpanded ? 'bg-white/5' : ''}`}
                          onClick={() => toggleExpand(run)}>
                        <td className="py-4 text-center">
                          {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-500" />}
                        </td>
                        <td className="py-4 pr-3">
                          <div className="flex flex-col">
                            <span className="font-bold text-slate-200 text-sm">{run.workflow_name || '—'}</span>
                            <span className="text-2xs text-slate-500 mt-0.5 font-mono">{run.id?.slice(0, 12)}...</span>
                          </div>
                        </td>
                        <td className="py-4">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-semibold gap-1.5 ${statusStyle}`}>
                            {statusIcon}
                            {run.status?.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-4 font-mono text-[10px] text-slate-400">{run.trigger_type || 'manual'}</td>
                        <td className="py-4 font-mono text-2xs text-slate-500 text-right">
                          {run.started_at ? new Date(run.started_at).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr className="bg-slate-950/20">
                          <td colSpan={5} className="p-4 border-b border-white/10">
                            <div className="rounded-xl border border-white/10 bg-slate-900/80 p-4 font-mono text-[11px] text-slate-350 space-y-3.5">
                              <div className="flex justify-between items-center border-b border-white/10 pb-2">
                                <span className="font-bold text-3xs text-cyan-400">RUN DETAILS</span>
                                <span>ID: {run.id}</span>
                              </div>

                              {/* Metadata grid */}
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-slate-400">
                                <div className="space-y-1.5">
                                  <p><span className="text-slate-500">Workflow:</span> {run.workflow_name}</p>
                                  <p><span className="text-slate-500">Trigger:</span> {run.trigger_type}</p>
                                  <p><span className="text-slate-500">Status:</span> <span className={run.status === 'success' ? 'text-emerald-400' : run.status === 'failed' ? 'text-rose-400' : 'text-amber-400'}>{run.status}</span></p>
                                </div>
                                <div className="space-y-1.5">
                                  <p><span className="text-slate-500">Started:</span> {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}</p>
                                  <p><span className="text-slate-500">Finished:</span> {run.finished_at ? new Date(run.finished_at).toLocaleString() : 'In progress'}</p>
                                  <p><span className="text-slate-500">Attempt:</span> {run.attempt_number || 1} / {run.max_attempts || 3}</p>
                                </div>
                              </div>

                              {/* Error */}
                              {run.error_message && (
                                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/15 text-rose-400 flex items-start gap-2">
                                  <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
                                  <div>
                                    <p className="font-bold">Error:</p>
                                    <p className="mt-1 text-rose-300/80">{run.error_message}</p>
                                  </div>
                                </div>
                              )}

                              {/* Step logs */}
                              <div>
                                <p className="text-slate-500 text-3xs font-bold tracking-wider mb-2">STEP LOGS ({isLoadingStep ? '...' : steps.length})</p>
                                {isLoadingStep ? (
                                  <div className="flex items-center gap-2 text-slate-500"><RotateCw className="h-3.5 w-3.5 animate-spin" /> Loading step logs...</div>
                                ) : steps.length === 0 ? (
                                  <p className="text-slate-600">No step logs recorded.</p>
                                ) : (
                                  <div className="space-y-2">
                                    {steps.map((step, i) => (
                                      <div key={i} className={`p-2.5 rounded-lg border ${step.status === 'success' ? 'border-emerald-500/10 bg-emerald-500/5' : 'border-rose-500/10 bg-rose-500/5'}`}>
                                        <div className="flex justify-between text-[10px]">
                                          <span className="font-bold text-slate-300">{step.node_id}</span>
                                          <span className={step.status === 'success' ? 'text-emerald-400' : 'text-rose-400'}>{step.status}</span>
                                        </div>
                                        {step.error && <p className="text-rose-400/80 mt-1 text-[10px]">{step.error}</p>}
                                        {step.duration_ms && <p className="text-slate-600 mt-0.5 text-[10px]">{step.duration_ms}ms</p>}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
