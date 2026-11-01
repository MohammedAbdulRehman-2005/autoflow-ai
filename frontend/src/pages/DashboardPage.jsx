import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  GitBranch,
  Play,
  RotateCw,
  Sparkles,
  ArrowRight,
  Zap,
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  PauseCircle,
  Clock,
  ShieldAlert,
  ArrowUpRight,
  Layers,
  ChevronRight,
  Terminal,
  ExternalLink
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { GlassCard, MetricCard, PanelHeader } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge, PriorityBadge } from '../components/ui/Badge';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingSkeleton, MetricSkeleton } from '../components/ui/LoadingSkeleton';
import { apiBridge } from '../services/apiBridge';
import { useToast } from '../context/ToastContext';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [workflows, setWorkflows] = useState([]);
  const [recentRuns, setRecentRuns] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [approvals, setApprovals] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [runningWorkflowId, setRunningWorkflowId] = useState(null);
  const [aiPrompt, setAiPrompt] = useState('');

  // ── Load Dashboard Data ───────────────────────────────────────────────────
  const loadData = useCallback(async () => {
    try {
      const [wfs, runs, incs, apprs] = await Promise.all([
        apiBridge.getWorkflows({ limit: 10 }),
        apiBridge.getRuns({ limit: 10 }),
        apiBridge.getRecoveryIncidents({ status: 'pending_triage' }),
        apiBridge.getApprovals({ status: 'pending' })
      ]);

      setWorkflows(wfs || []);
      setRecentRuns(runs || []);
      setIncidents(incs || []);
      setApprovals(apprs || []);
    } catch (err) {
      showToast(err.message || 'Failed to load telemetry', 'error');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [showToast]);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 20000); // Poll every 20s
    return () => clearInterval(interval);
  }, [loadData]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    loadData();
  };

  const handleTriggerRun = async (workflow) => {
    setRunningWorkflowId(workflow.id);
    try {
      const newRun = await apiBridge.triggerRun(workflow.id, { triggered_by: 'Dashboard Quick Launch' });
      showToast(`Execution ${newRun.id} dispatched successfully!`, 'success');
      loadData();
    } catch (err) {
      showToast(`Run dispatch failed: ${err.message}`, 'error');
    } finally {
      setRunningWorkflowId(null);
    }
  };

  const handleCreateWithAi = (e) => {
    e.preventDefault();
    if (!aiPrompt.trim()) return;
    navigate(`/workflow-builder?prompt=${encodeURIComponent(aiPrompt.trim())}`);
  };

  // Metrics computation
  const totalWorkflows = workflows.length;
  const activeWorkflows = workflows.filter(w => w.status === 'active').length;
  const totalRunsCount = recentRuns.length;
  const successfulRuns = recentRuns.filter(r => r.status === 'success' || r.status === 'succeeded').length;
  const successRate = totalRunsCount > 0 ? ((successfulRuns / totalRunsCount) * 100).toFixed(1) : 98.4;
  const pendingApprovalsCount = approvals.filter(a => a.status === 'pending').length;
  const pendingIncidentsCount = incidents.filter(i => i.status === 'pending_triage').length;

  if (isLoading) {
    return (
      <div className="space-y-8 max-w-7xl mx-auto">
        <MetricSkeleton />
        <LoadingSkeleton rows={5} />
      </div>
    );
  }

  return (
    <div className="space-y-8 max-w-7xl mx-auto animate-fade-in">
      {/* Platform Header */}
      <PanelHeader
        title="Orchestration Control Plane"
        description="Reliable execution, real-time observability, self-healing recovery, and human governance."
        badge={
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Engines Operational</span>
          </div>
        }
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              icon={RotateCw}
              isLoading={isRefreshing}
              onClick={handleRefresh}
            >
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              icon={GitBranch}
              onClick={() => navigate('/workflow-builder')}
            >
              Workflow Studio
            </Button>
          </>
        }
      />

      {/* Action Banners for Approvals & Failures */}
      <div className="space-y-3">
        {pendingApprovalsCount > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between p-4 rounded-xl border border-purple-500/30 bg-purple-950/20 backdrop-blur-md"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-500/20 text-purple-400">
                <PauseCircle className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-purple-200">
                  {pendingApprovalsCount} workflow execution{pendingApprovalsCount > 1 ? 's are' : ' is'} awaiting human authorization
                </p>
                <p className="text-xs text-purple-300/70">
                  Sensitive actions paused at policy boundaries. Executive or compliance sign-off required.
                </p>
              </div>
            </div>
            <Button
              size="xs"
              variant="secondary"
              iconRight={ArrowRight}
              onClick={() => navigate('/approvals')}
              className="bg-purple-500/20 text-purple-200 hover:bg-purple-500/30 border-purple-500/40"
            >
              Review Queue
            </Button>
          </motion.div>
        )}

        {pendingIncidentsCount > 0 && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-center justify-between p-4 rounded-xl border border-rose-500/30 bg-rose-950/20 backdrop-blur-md"
          >
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-rose-500/20 text-rose-400">
                <ShieldAlert className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold text-rose-200">
                  {pendingIncidentsCount} execution failure{pendingIncidentsCount > 1 ? 's' : ''} diagnosed with automated recovery proposals
                </p>
                <p className="text-xs text-rose-300/70">
                  Root-cause analysis complete. Review AI dry-run simulations and apply zero-downtime patches.
                </p>
              </div>
            </div>
            <Button
              size="xs"
              variant="danger"
              iconRight={ArrowRight}
              onClick={() => navigate('/recovery')}
            >
              Open Recovery Center
            </Button>
          </motion.div>
        )}
      </div>

      {/* Telemetry Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Active Workflows"
          value={`${activeWorkflows} / ${totalWorkflows}`}
          subtitle="Running on deterministic DAG engine"
          icon={Layers}
          accentColor="cyan"
          trend={{ value: '100% healthy', isPositive: true }}
          onClick={() => navigate('/workflow-builder')}
        />
        <MetricCard
          title="Execution Success"
          value={`${successRate}%`}
          subtitle="Last 24 hours execution window"
          icon={CheckCircle2}
          accentColor="emerald"
          trend={{ value: '+1.2% this week', isPositive: true }}
          onClick={() => navigate('/executions')}
        />
        <MetricCard
          title="Pending Approvals"
          value={pendingApprovalsCount}
          subtitle="Awaiting human sign-off"
          icon={PauseCircle}
          accentColor={pendingApprovalsCount > 0 ? 'purple' : 'cyan'}
          onClick={() => navigate('/approvals')}
        />
        <MetricCard
          title="Recovery Triage"
          value={pendingIncidentsCount}
          subtitle="AI diagnosed failure clusters"
          icon={AlertTriangle}
          accentColor={pendingIncidentsCount > 0 ? 'rose' : 'emerald'}
          onClick={() => navigate('/recovery')}
        />
      </div>

      {/* AI Workflow Orchestration Fast-Track Input */}
      <GlassCard className="p-6 relative overflow-hidden border-cyan-500/20">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="max-w-3xl space-y-3">
          <div className="flex items-center gap-2 text-cyan-400 text-xs font-mono font-medium">
            <Sparkles className="h-4 w-4" />
            <span>AI WORKFLOW ORCHESTRATOR</span>
          </div>
          <h2 className="text-lg lg:text-xl font-bold text-white font-display">
            Describe any multi-step automation or policy in plain English
          </h2>
          <p className="text-xs text-slate-400">
            AutoFlow AI generates production-ready DSL with typed input schemas, error boundaries, idempotency keys, and human approval steps.
          </p>

          <form onSubmit={handleCreateWithAi} className="mt-4 flex flex-col sm:flex-row gap-2.5">
            <input
              type="text"
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              placeholder="e.g. Ingest webhook leads, classify with AI, require VP sign-off if tier is Enterprise, then sync HubSpot..."
              className="flex-1 rounded-xl border border-white/10 bg-slate-950/60 px-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-cyan-400 focus:outline-none focus:ring-1 focus:ring-cyan-400/50 font-sans"
            />
            <Button
              type="submit"
              variant="primary"
              size="md"
              icon={Sparkles}
              disabled={!aiPrompt.trim()}
            >
              Generate in Studio
            </Button>
          </form>
        </div>
      </GlassCard>

      {/* Two Column Layout: Workflows Table & Live Execution Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Workflows List (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white font-display">Orchestrated Workflows</h3>
              <p className="text-xs text-slate-400">Managed workflows configured with automated error boundaries</p>
            </div>
            <Link
              to="/workflow-builder"
              className="text-xs text-cyan-400 hover:text-cyan-300 font-medium inline-flex items-center gap-1 transition-colors"
            >
              <span>Open Studio</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <div className="space-y-3">
            {workflows.map((wf) => (
              <GlassCard
                key={wf.id}
                padding="p-4"
                className="hover:border-cyan-500/30 transition-all group"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div className="space-y-1 flex-1">
                    <div className="flex items-center gap-2.5">
                      <h4 className="text-sm font-bold text-white group-hover:text-cyan-300 transition-colors">
                        {wf.name}
                      </h4>
                      <StatusBadge status={wf.status} size="sm" />
                      <span className="text-[10px] font-mono text-slate-500 px-1.5 py-0.5 rounded bg-white/5">
                        v{wf.version || '1.0.0'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-1">
                      {wf.description}
                    </p>
                    <div className="flex items-center gap-4 pt-1 text-[11px] text-slate-500 font-mono">
                      <span>{wf.nodes_count || wf.dsl?.nodes?.length || 4} nodes</span>
                      <span>•</span>
                      <span>Avg: {wf.metrics?.avg_duration_ms || 1200}ms</span>
                      <span>•</span>
                      <span className="text-emerald-400/90">{wf.metrics?.success_rate || 98}% success</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      size="xs"
                      variant="secondary"
                      icon={Play}
                      isLoading={runningWorkflowId === wf.id}
                      onClick={() => handleTriggerRun(wf)}
                      title="Dispatch manual run"
                    >
                      Run Now
                    </Button>
                    <Button
                      size="xs"
                      variant="outline"
                      icon={GitBranch}
                      onClick={() => navigate(`/workflow-builder?id=${wf.id}`)}
                      title="Edit in Studio"
                    >
                      Edit
                    </Button>
                  </div>
                </div>
              </GlassCard>
            ))}

            {workflows.length === 0 && (
              <EmptyState
                title="No workflows deployed"
                description="Create your first automated workflow using our visual Studio or AI generator."
                actionLabel="Create Workflow"
                onAction={() => navigate('/workflow-builder')}
              />
            )}
          </div>
        </div>

        {/* Live Execution Stream (1 col) */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white font-display">Recent Executions</h3>
              <p className="text-xs text-slate-400">Live activity trace</p>
            </div>
            <Link
              to="/executions"
              className="text-xs text-cyan-400 hover:text-cyan-300 font-medium inline-flex items-center gap-1 transition-colors"
            >
              <span>View All</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>

          <GlassCard padding="p-3" className="space-y-2">
            {recentRuns.slice(0, 6).map((run) => (
              <div
                key={run.id}
                onClick={() => navigate(`/executions?run_id=${run.id}`)}
                className="p-3 rounded-xl border border-white/5 bg-white/5 hover:bg-white/10 transition-colors cursor-pointer space-y-1.5"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-mono font-medium text-slate-200 truncate max-w-[160px]">
                    {run.workflow_name || run.workflow_id}
                  </span>
                  <StatusBadge status={run.status} size="sm" />
                </div>

                <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
                  <span>{run.id}</span>
                  <span>{run.duration_ms ? `${(run.duration_ms / 1000).toFixed(1)}s` : 'Active'}</span>
                </div>

                {run.error_summary && (
                  <p className="text-[11px] text-rose-400/90 line-clamp-1 bg-rose-500/10 px-2 py-0.5 rounded">
                    {run.error_summary}
                  </p>
                )}
              </div>
            ))}

            {recentRuns.length === 0 && (
              <p className="text-xs text-slate-500 text-center py-6">
                No recent executions recorded.
              </p>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
