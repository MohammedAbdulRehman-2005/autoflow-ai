import { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  GitBranch, CheckCircle2, Activity, Percent, Play, RotateCw,
  Sparkles, ArrowRight, Brain, ArrowUpRight, Zap, CheckSquare,
  Mic, MicOff, AlertCircle, RefreshCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import SummaryCard from '../components/SummaryCard';
import { workflowApi } from '../services/workflowApi';

// ── Helpers ───────────────────────────────────────────────────────────────────
const STATUS_COLORS = {
  success:  'bg-emerald-500/10 text-emerald-400',
  running:  'bg-blue-500/10 text-blue-400',
  failed:   'bg-rose-500/10 text-rose-400',
  pending:  'bg-amber-500/10 text-amber-400',
  cancelled:'bg-slate-500/10 text-slate-400',
};
const DOT_COLORS = {
  success:  'bg-emerald-400',
  running:  'bg-blue-400 animate-pulse',
  failed:   'bg-rose-400',
  pending:  'bg-amber-400 animate-pulse',
  cancelled:'bg-slate-400',
};

export default function DashboardPage() {
  const navigate = useNavigate();

  // Data state
  const [workflows, setWorkflows]     = useState([]);
  const [recentRuns, setRecentRuns]   = useState([]);
  const [metrics, setMetrics]         = useState({ total: 0, active: 0, totalRuns: 0, successRate: 0 });
  const [isLoading, setIsLoading]     = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError]             = useState(null);

  // AI prompt
  const [promptValue, setPromptValue]   = useState('');

  // Voice
  const [isListening, setIsListening]         = useState(false);
  const [speechInstance, setSpeechInstance]   = useState(null);

  // Per-workflow run state
  const [firingId, setFiringId] = useState(null);
  const [fireResult, setFireResult] = useState({});   // { [wf_id]: 'ok' | 'error' }

  // ── Load dashboard data ───────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    try {
      setError(null);

      // 1. Workflows list
      const wfData = await workflowApi.list({ limit: 10 });
      const wfList = wfData?.workflows || wfData?.items || [];
      setWorkflows(wfList);

      // 2. Recent runs — collect runs from last 5 workflows
      let allRuns = [];
      const sample = wfList.slice(0, 5);
      await Promise.all(
        sample.map(async (wf) => {
          try {
            const runsData = await workflowApi.listRuns(wf.id, { limit: 5 });
            const runs = runsData?.runs || [];
            runs.forEach(r => allRuns.push({ ...r, workflow_name: wf.name }));
          } catch (_) {}
        })
      );
      allRuns.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
      setRecentRuns(allRuns.slice(0, 8));

      // 3. Compute metrics
      const active = wfList.filter(w => w.status === 'active').length;
      const totalRuns = allRuns.length;
      const successes = allRuns.filter(r => r.status === 'success').length;
      const successRate = totalRuns > 0 ? ((successes / totalRuns) * 100).toFixed(1) : 0;

      setMetrics({
        total: wfData?.total || wfList.length,
        active,
        totalRuns,
        successRate: parseFloat(successRate),
      });

    } catch (err) {
      setError(err.message || 'Failed to load dashboard data.');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 15000);   // Poll every 15s
    return () => clearInterval(interval);
  }, [loadData]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    loadData();
  };

  // ── Fire a workflow manually ───────────────────────────────────────────────
  const handleFireWorkflow = async (wfId) => {
    setFiringId(wfId);
    setFireResult(prev => ({ ...prev, [wfId]: null }));
    try {
      await workflowApi.run(wfId);
      setFireResult(prev => ({ ...prev, [wfId]: 'ok' }));
      setTimeout(() => loadData(), 1500);  // Refresh after run starts
    } catch (err) {
      setFireResult(prev => ({ ...prev, [wfId]: 'error' }));
      console.error('Run failed:', err.message);
    } finally {
      setFiringId(null);
    }
  };

  // ── AI Prompt → hand off to workflow builder ─────────────────────────────────────────────
  const handleGenerateWorkflow = () => {
    if(! promptValue.trim()) return ;
    const prompt =promptValue.trim();
    navigate('/workflow-builder', {state : {initialPrompt : prompt}});
  };
    
  // ── Voice dictation ───────────────────────────────────────────────────────
  const toggleVoice = () => {
    const SpeechAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechAPI) { alert('Voice input is not supported in this browser.'); return; }
    if (isListening && speechInstance) { speechInstance.stop(); setIsListening(false); return; }
    const rec = new SpeechAPI();
    rec.lang = 'en-US'; rec.continuous = false; rec.interimResults = false;
    rec.onstart  = () => setIsListening(true);
    rec.onend    = () => setIsListening(false);
    rec.onerror  = () => setIsListening(false);
    rec.onresult = (e) => {
      const t = e.results[0][0].transcript;
      setPromptValue(prev => (prev ? prev + ' ' : '') + t);
    };
    setSpeechInstance(rec);
    rec.start();
  };

  useEffect(() => () => { if (speechInstance) speechInstance.stop(); }, [speechInstance]);

  // ─────────────────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-3">
          <RotateCw className="h-8 w-8 text-cyan-400 animate-spin mx-auto" />
          <p className="text-slate-400 text-sm font-medium">Loading workspace...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center space-y-4 max-w-md">
          <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
          <p className="text-white font-bold text-lg">Failed to load dashboard</p>
          <p className="text-slate-400 text-sm">{error}</p>
          <p className="text-slate-500 text-xs">Make sure the backend is running at <code className="text-cyan-400">{import.meta.env.VITE_API_URL || 'http://localhost:8000'}</code></p>
          <button
            onClick={() => { setIsLoading(true); loadData(); }}
            className="px-5 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 text-white text-xs font-bold"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 select-none text-left">

      {/* Title Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-white font-display">
            Workspace Overview
          </h1>
          <p className="text-sm text-slate-400 mt-1 font-sans">
            Monitor and manage your live automation pipelines.
          </p>
        </div>
        <div className="flex items-center space-x-3 self-start sm:self-auto">
          <button
            onClick={handleRefresh}
            className="flex items-center space-x-2 px-3.5 py-2 border border-white/5 rounded-xl bg-slate-900/55 hover:bg-slate-900 text-slate-300 hover:text-white transition-all text-xs font-semibold cursor-pointer"
          >
            <RotateCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            <span>Sync Stats</span>
          </button>
          <Link
            to="/workflow-builder"
            className="inline-flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white shadow-lg shadow-blue-500/10 rounded-xl text-xs font-bold transition-all"
          >
            <Zap className="h-4 w-4" />
            <span>New Workflow</span>
          </Link>
        </div>
      </div>

      {/* AI Prompt Panel */}
      <div className="border border-cyan-500/15 rounded-3xl bg-gradient-to-br from-slate-940/90 via-[#070b19]/95 to-cyan-950/20 p-6 md:p-8 backdrop-blur-xl relative overflow-hidden shadow-xl">
        <div className="absolute top-0 right-0 h-40 w-40 rounded-full bg-cyan-500/10 blur-3xl pointer-events-none" />
        <div className="flex flex-col md:flex-row gap-6 md:items-start justify-between relative z-10">
          <div className="space-y-2 flex-1">
            <div className="flex items-center space-x-2 text-cyan-400">
              <Sparkles className="h-5 w-5 animate-pulse" />
              <span className="text-2xs font-extrabold tracking-widest uppercase font-mono">Create Workflow using AI</span>
            </div>
            <h2 className="text-xl md:text-2xl font-black text-white font-display tracking-tight">
              Describe your automation
            </h2>
            <p className="text-xs text-slate-450 max-w-xl leading-relaxed">
              Tell the AI what you want to automate. It will generate a full workflow DSL, validate it, and save it — ready to run.
            </p>
          </div>

          <div className="w-full md:max-w-md flex flex-col space-y-3">
            <div className="relative">
              <textarea
                value={promptValue}
                onChange={(e) => setPromptValue(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleGenerateWorkflow(); }}
                placeholder="e.g. Send appointment reminders to patients every Monday at 9am..."
                rows={3}
                className="w-full text-xs text-slate-200 placeholder-slate-500 bg-slate-950/50 border border-white/10 rounded-xl p-3 pr-10 outline-none resize-none hover:border-white/20 focus:border-cyan-500/55 transition-all font-sans"
              />
              <button
                onClick={toggleVoice}
                className={`absolute right-3 top-3 p-1.5 rounded-lg transition-all cursor-pointer ${isListening ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse' : 'text-slate-400 hover:text-white hover:bg-white/10'}`}
              >
                {isListening ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
              </button>
            </div>

            <button
              onClick={handleGenerateWorkflow}
              disabled={!promptValue.trim()}
              className="py-2.5 px-5 rounded-xl font-bold text-xs text-center bg-gradient-to-r from-blue-600 to-cyan-500 hover:from-blue-500 hover:to-cyan-400 text-white cursor-pointer active:scale-98 transition-all shadow-md flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
             <Sparkles className="h-3.5 w-3.5 text-cyan-200" /><span>Generate Workflow</span></>
              
            </button>
            <p className="text-[10px] text-slate-500 text-center">Tip: Ctrl+Enter to submit quickly</p>
          </div>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <SummaryCard title="TOTAL WORKFLOWS" value={metrics.total} icon={GitBranch} glowColor="blue"
          trend={{ value: 'All time', isPositive: true }} description="Workflows in your workspace" />
        <SummaryCard title="TOTAL RUNS" value={metrics.totalRuns} icon={CheckSquare} glowColor="emerald"
          trend={{ value: 'Live data', isPositive: true }} description="Executions tracked" />
        <SummaryCard title="ACTIVE WORKFLOWS" value={metrics.active} icon={Activity} glowColor="cyan"
          trend={{ value: 'Running now', isPositive: true }} description="Currently enabled" />
        <SummaryCard title="SUCCESS RATE" value={`${metrics.successRate}%`} icon={Percent} glowColor="emerald"
          trend={{ value: 'All runs', isPositive: metrics.successRate >= 80 }} description="Successful completions" />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">

        {/* Left: Recent Runs table */}
        <div className="lg:col-span-2 space-y-8">
          <div className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg shadow-md">
            <div className="flex justify-between items-center mb-5">
              <div>
                <h3 className="text-lg font-bold text-white font-display">Recent Execution History</h3>
                <p className="text-xs text-slate-400 mt-1 font-sans">Live status from the backend</p>
              </div>
              <Link to="/logs" className="flex items-center space-x-1.5 text-xs font-bold text-cyan-400 hover:text-cyan-300 transition-colors font-display">
                <span>Full Audit Logs</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            {recentRuns.length === 0 ? (
              <div className="text-center py-12 text-slate-500">
                <Activity className="h-8 w-8 mx-auto mb-3 text-slate-600" />
                <p className="text-sm">No runs yet. Fire a workflow to see logs here.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/10 text-slate-500 font-display uppercase tracking-wider text-[10px]">
                      <th className="pb-3 pt-1 font-semibold">WORKFLOW</th>
                      <th className="pb-3 pt-1 font-semibold">STATUS</th>
                      <th className="pb-3 pt-1 font-semibold">TRIGGER</th>
                      <th className="pb-3 pt-1 font-semibold text-right">TIME</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/10 text-slate-350">
                    {recentRuns.map((run) => (
                      <tr key={run.id} className="hover:bg-white/5 transition-colors">
                        <td className="py-3.5 pr-2">
                          <div className="flex flex-col">
                            <span className="font-semibold text-slate-200">{run.workflow_name || '—'}</span>
                            <span className="text-[10px] text-slate-500 mt-0.5 font-mono">{run.id?.slice(0, 8)}...</span>
                          </div>
                        </td>
                        <td className="py-3.5">
                          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${STATUS_COLORS[run.status] || STATUS_COLORS.pending}`}>
                            <span className={`h-1.5 w-1.5 rounded-full mr-1.5 ${DOT_COLORS[run.status] || DOT_COLORS.pending}`} />
                            {run.status?.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-3.5 font-mono text-[10px] text-slate-400">{run.trigger_type || 'manual'}</td>
                        <td className="py-3.5 font-mono text-[10px] text-slate-500 text-right">
                          {run.started_at ? new Date(run.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right: Quick Actions + Trigger Sandbox */}
        <div className="space-y-8">

          {/* Quick Shortcuts */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg shadow-md">
            <h3 className="text-lg font-bold text-white mb-4 font-display">Quick Shortcuts</h3>
            <div className="flex flex-col space-y-3">
              <Link to="/workflow-builder" className="flex items-center justify-between p-4 rounded-xl border border-white/10 bg-slate-950/30 hover:border-blue-500/40 hover:bg-white/5 transition-all group">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg"><Brain className="h-4 w-4" /></div>
                  <div className="flex flex-col text-left">
                    <span className="text-xs font-bold text-slate-200">Build Workflow</span>
                    <span className="text-[10px] text-slate-500 mt-0.5">Visual Studio + AI Planner</span>
                  </div>
                </div>
                <ArrowUpRight className="h-4 w-4 text-slate-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </Link>
              <Link to="/marketplace" className="flex items-center justify-between p-4 rounded-xl border border-white/10 bg-slate-950/30 hover:border-cyan-500/40 hover:bg-white/5 transition-all group">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg border border-cyan-500/20"><Sparkles className="h-4 w-4" /></div>
                  <div className="flex flex-col text-left">
                    <span className="text-xs font-bold text-slate-200">Template Marketplace</span>
                    <span className="text-[10px] text-slate-500 mt-0.5">Deploy 1-click industry presets</span>
                  </div>
                </div>
                <ArrowUpRight className="h-4 w-4 text-slate-500 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </Link>
            </div>
          </div>

          {/* Trigger Sandbox */}
          <div className="border border-white/10 rounded-3xl bg-white/5 p-6 backdrop-blur-lg shadow-md">
            <h3 className="text-sm font-bold text-white mb-1 font-display">Trigger Sandbox</h3>
            <p className="text-xs text-slate-400 mb-4 font-sans">Click FIRE to manually run a workflow.</p>

            {workflows.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-4">No workflows yet.</p>
            ) : (
              <div className="flex flex-col space-y-2">
                {workflows.slice(0, 6).map((wf) => (
                  <div key={wf.id} className="flex justify-between items-center p-2.5 rounded-lg hover:bg-white/5 border border-transparent hover:border-white/10 transition-all">
                    <div className="flex flex-col flex-1 min-w-0 mr-2">
                      <span className="text-xs text-slate-200 truncate font-medium">{wf.name}</span>
                      <span className="text-[10px] text-slate-500">{wf.status}</span>
                    </div>
                    <button
                      onClick={() => handleFireWorkflow(wf.id)}
                      disabled={firingId === wf.id}
                      className="flex items-center space-x-1 border border-cyan-500/30 bg-cyan-500/10 text-cyan-400 hover:bg-cyan-500 hover:text-slate-950 px-2 py-1 rounded-md text-[10px] font-bold transition-all cursor-pointer disabled:opacity-50 shrink-0"
                    >
                      {firingId === wf.id ? (
                        <RotateCw className="h-2.5 w-2.5 animate-spin" />
                      ) : fireResult[wf.id] === 'ok' ? (
                        <CheckCircle2 className="h-2.5 w-2.5 text-emerald-400" />
                      ) : fireResult[wf.id] === 'error' ? (
                        <AlertCircle className="h-2.5 w-2.5 text-rose-400" />
                      ) : (
                        <Play className="h-2.5 w-2.5 fill-current" />
                      )}
                      <span>{fireResult[wf.id] === 'ok' ? 'FIRED' : fireResult[wf.id] === 'error' ? 'ERROR' : 'FIRE'}</span>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}
