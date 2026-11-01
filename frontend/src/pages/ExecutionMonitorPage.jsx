import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  RotateCw,
  Search,
  Filter,
  Play,
  RotateCcw,
  Terminal,
  ExternalLink,
  ChevronRight,
  ShieldAlert,
  PauseCircle,
  Copy,
  Check,
  AlertTriangle,
  Download
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { PanelHeader, GlassCard } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge } from '../components/ui/Badge';
import { Drawer } from '../components/ui/Drawer';
import { CodePayloadViewer } from '../components/ui/CodePayloadViewer';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingSkeleton } from '../components/ui/LoadingSkeleton';
import { apiBridge } from '../services/apiBridge';
import { useToast } from '../context/ToastContext';

export default function ExecutionMonitorPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [runs, setRuns] = useState([]);
  const [selectedRun, setSelectedRun] = useState(null);
  const [selectedStep, setSelectedStep] = useState(null);
  const [isStepDrawerOpen, setIsStepDrawerOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [isReplaying, setIsReplaying] = useState(false);

  const queryRunId = searchParams.get('run_id');
  const queryWorkflowId = searchParams.get('workflow_id');

  // ── Load Runs Data ────────────────────────────────────────────────────────
  const loadRuns = useCallback(async () => {
    try {
      const data = await apiBridge.getRuns({
        workflow_id: queryWorkflowId || undefined
      });
      setRuns(data || []);

      if (data && data.length > 0) {
        if (queryRunId) {
          const match = data.find((r) => r.id === queryRunId);
          setSelectedRun(match || data[0]);
        } else if (!selectedRun) {
          setSelectedRun(data[0]);
        }
      }
    } catch (err) {
      showToast(err.message || 'Failed to load execution runs', 'error');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [queryRunId, queryWorkflowId, selectedRun, showToast]);

  useEffect(() => {
    loadRuns();
    const interval = setInterval(loadRuns, 15000);
    return () => clearInterval(interval);
  }, [loadRuns]);

  const handleRefresh = () => {
    setIsRefreshing(true);
    loadRuns();
  };

  const handleSelectRun = (run) => {
    setSelectedRun(run);
    setSearchParams({ run_id: run.id });
  };

  const handleStepClick = (step) => {
    setSelectedStep(step);
    setIsStepDrawerOpen(true);
  };

  const handleReplayRun = async () => {
    if (!selectedRun) return;
    setIsReplaying(true);
    try {
      const newRun = await apiBridge.triggerRun(selectedRun.workflow_id, {
        replayed_from_run_id: selectedRun.id
      });
      showToast(`Replay run ${newRun.id} dispatched!`, 'success');
      loadRuns();
      setSelectedRun(newRun);
    } catch (err) {
      showToast(`Replay failed: ${err.message}`, 'error');
    } finally {
      setIsReplaying(false);
    }
  };

  const handleExportTrace = () => {
    if (!selectedRun) return;
    const jsonStr = JSON.stringify(selectedRun, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedRun.id}-trace.json`;
    a.click();
    showToast('Execution trace exported', 'info');
  };

  // Filtered runs list
  const filteredRuns = runs.filter((run) => {
    const matchesSearch =
      (run.workflow_name || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
      run.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (run.trigger_type || '').toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === 'all' ||
      (run.status || '').toLowerCase() === statusFilter.toLowerCase();

    return matchesSearch && matchesStatus;
  });

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <PanelHeader
          title="Execution Monitor"
          description="Observability timeline, step traces, and replay controls."
        />
        <LoadingSkeleton rows={6} />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-fade-in">
      <PanelHeader
        title="Execution Monitor"
        description="End-to-end execution observability, step duration breakdowns, input/output inspection, and idempotency guarantees."
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
            {selectedRun && (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={Download}
                  onClick={handleExportTrace}
                >
                  Export Trace
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  icon={RotateCcw}
                  isLoading={isReplaying}
                  onClick={handleReplayRun}
                >
                  Replay Run
                </Button>
              </>
            )}
          </>
        }
      />

      {/* Main Split-Screen Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Runs List (5 cols) */}
        <div className="lg:col-span-5 space-y-3">
          {/* Filters Bar */}
          <GlassCard padding="p-3" className="space-y-2.5">
            <div className="relative">
              <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
              <input
                type="text"
                placeholder="Search run ID, workflow, trigger..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full rounded-lg border border-white/10 bg-slate-950/60 py-1.5 pl-9 pr-3 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400/50 font-mono"
              />
            </div>

            <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs font-mono">
              {['all', 'running', 'success', 'failed', 'awaiting_approval'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`px-2.5 py-1 rounded-md text-[11px] uppercase transition-all whitespace-nowrap cursor-pointer ${
                    statusFilter === st
                      ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-semibold'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/5 border border-transparent'
                  }`}
                >
                  {st.replace('_', ' ')}
                </button>
              ))}
            </div>
          </GlassCard>

          {/* Runs Queue */}
          <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
            {filteredRuns.map((run) => {
              const isSelected = selectedRun?.id === run.id;
              return (
                <div
                  key={run.id}
                  onClick={() => handleSelectRun(run)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'border-cyan-400/50 bg-slate-900/90 shadow-lg shadow-cyan-500/5'
                      : 'border-white/10 bg-slate-900/40 hover:border-white/20 hover:bg-slate-900/60'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="space-y-1 flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-slate-200">
                          {run.id}
                        </span>
                        <StatusBadge status={run.status} size="sm" />
                      </div>
                      <p className="text-xs font-medium text-white truncate">
                        {run.workflow_name}
                      </p>
                    </div>

                    <div className="text-right shrink-0 font-mono text-[11px] text-slate-400">
                      <span>{run.duration_ms ? `${(run.duration_ms / 1000).toFixed(1)}s` : 'Active'}</span>
                    </div>
                  </div>

                  <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500 font-mono border-t border-white/5 pt-2">
                    <span className="capitalize">{run.trigger_type || 'manual'} trigger</span>
                    <span>{run.started_at ? new Date(run.started_at).toLocaleTimeString() : 'Pending'}</span>
                  </div>

                  {run.error_summary && (
                    <div className="mt-2 text-[11px] text-rose-300 bg-rose-500/10 border border-rose-500/20 px-2.5 py-1 rounded-md line-clamp-1">
                      {run.error_summary}
                    </div>
                  )}
                </div>
              );
            })}

            {filteredRuns.length === 0 && (
              <EmptyState
                title="No executions found"
                description="No execution runs match your selected filter criteria."
              />
            )}
          </div>
        </div>

        {/* Right: Selected Run Detail & Step Timeline (7 cols) */}
        <div className="lg:col-span-7">
          {selectedRun ? (
            <div className="space-y-6">
              {/* Run Header Card */}
              <GlassCard padding="p-5" className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-white/10 pb-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h2 className="text-lg font-bold text-white font-display">
                        {selectedRun.workflow_name}
                      </h2>
                      <StatusBadge status={selectedRun.status} size="md" />
                    </div>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">
                      Execution ID: <span className="text-cyan-400">{selectedRun.id}</span>
                    </p>
                  </div>

                  {selectedRun.status === 'failed' && (
                    <Button
                      size="xs"
                      variant="danger"
                      icon={ShieldAlert}
                      onClick={() => navigate(`/recovery?run_id=${selectedRun.id}`)}
                    >
                      Diagnose with AI
                    </Button>
                  )}

                  {selectedRun.status === 'awaiting_approval' && (
                    <Button
                      size="xs"
                      variant="secondary"
                      icon={PauseCircle}
                      className="bg-purple-500/20 text-purple-200 border-purple-500/30"
                      onClick={() => navigate('/approvals')}
                    >
                      Review Approval
                    </Button>
                  )}
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
                  <div className="p-2.5 rounded-lg bg-white/5 border border-white/5">
                    <span className="text-slate-500 text-[10px] uppercase block">Started At</span>
                    <span className="text-slate-200 font-medium truncate block">
                      {new Date(selectedRun.started_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-white/5 border border-white/5">
                    <span className="text-slate-500 text-[10px] uppercase block">Duration</span>
                    <span className="text-slate-200 font-medium block">
                      {selectedRun.duration_ms ? `${selectedRun.duration_ms}ms` : 'In progress'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-white/5 border border-white/5">
                    <span className="text-slate-500 text-[10px] uppercase block">Version</span>
                    <span className="text-slate-200 font-medium block">
                      v{selectedRun.workflow_version || '1.0.0'}
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-white/5 border border-white/5">
                    <span className="text-slate-500 text-[10px] uppercase block">Idempotency Key</span>
                    <span className="text-slate-200 font-medium truncate block" title={selectedRun.idempotency_key}>
                      {selectedRun.idempotency_key || 'N/A'}
                    </span>
                  </div>
                </div>

                {selectedRun.error_summary && (
                  <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-950/20 text-xs text-rose-300 space-y-1">
                    <span className="font-bold flex items-center gap-1.5 text-rose-400">
                      <AlertTriangle className="h-4 w-4" />
                      Execution Failed at Step {selectedRun.step_logs?.findIndex(s => s.status === 'failed') + 1}
                    </span>
                    <p className="font-mono text-[11px] leading-relaxed">
                      {selectedRun.error_summary}
                    </p>
                  </div>
                )}
              </GlassCard>

              {/* Execution Step Timeline */}
              <GlassCard padding="p-5" className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-white font-display flex items-center gap-2">
                    <Activity className="h-4 w-4 text-cyan-400" />
                    <span>Step Execution Trace ({selectedRun.step_logs?.length || 0} steps)</span>
                  </h3>
                  <span className="text-xs text-slate-500 font-mono">
                    Click step to inspect JSON payloads
                  </span>
                </div>

                <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-white/10">
                  {(selectedRun.step_logs || []).map((step, idx) => {
                    const isSuccess = step.status === 'success';
                    const isFailed = step.status === 'failed';
                    const isRunning = step.status === 'running';
                    const isPaused = step.status === 'paused';

                    const dotStyles = isSuccess
                      ? 'bg-emerald-500 text-slate-950 shadow-emerald-500/20'
                      : isFailed
                      ? 'bg-rose-500 text-white shadow-rose-500/20'
                      : isRunning
                      ? 'bg-blue-500 text-white animate-pulse'
                      : 'bg-purple-500 text-white';

                    return (
                      <div
                        key={step.step_id || idx}
                        onClick={() => handleStepClick(step)}
                        className="relative group cursor-pointer"
                      >
                        {/* Step Timeline Indicator Node */}
                        <div
                          className={`absolute -left-6 top-1 flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold shadow-md transition-transform group-hover:scale-125 ${dotStyles}`}
                        >
                          {isSuccess ? '✓' : isFailed ? '✕' : isRunning ? '⟳' : '⏸'}
                        </div>

                        {/* Step Card */}
                        <div className="p-3.5 rounded-xl border border-white/10 bg-slate-950/40 hover:border-cyan-400/40 hover:bg-slate-900/60 transition-all space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-bold text-white group-hover:text-cyan-300 transition-colors">
                              {step.node_title || step.node_id}
                            </span>
                            <div className="flex items-center gap-2 font-mono text-[11px]">
                              <span className="text-slate-400">
                                {step.duration_ms ? `${step.duration_ms}ms` : '0ms'}
                              </span>
                              <StatusBadge status={step.status} size="sm" />
                            </div>
                          </div>

                          <div className="flex items-center justify-between text-[11px] text-slate-500 font-mono">
                            <span>Node ID: {step.node_id}</span>
                            <span className="text-cyan-400/80 group-hover:text-cyan-400 inline-flex items-center gap-0.5">
                              Inspect <ChevronRight className="h-3 w-3" />
                            </span>
                          </div>

                          {step.error && (
                            <div className="text-[11px] text-rose-400 font-mono bg-rose-500/10 p-2 rounded border border-rose-500/20">
                              {step.error.message || 'Node execution failed'}
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </GlassCard>
            </div>
          ) : (
            <EmptyState
              title="No run selected"
              description="Select an execution run from the left panel to inspect step traces and payload data."
            />
          )}
        </div>
      </div>

      {/* Slide-over Step Inspector Drawer */}
      <Drawer
        isOpen={isStepDrawerOpen}
        onClose={() => setIsStepDrawerOpen(false)}
        title={selectedStep?.node_title || 'Step Inspector'}
        subtitle={`Node: ${selectedStep?.node_id} • Step ID: ${selectedStep?.step_id}`}
        badge={<StatusBadge status={selectedStep?.status} size="sm" />}
        footer={
          <Button
            size="sm"
            variant="secondary"
            onClick={() => setIsStepDrawerOpen(false)}
          >
            Close Inspector
          </Button>
        }
      >
        {selectedStep && (
          <div className="space-y-6">
            {/* Step Overview */}
            <div className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                <span className="text-slate-500 text-[10px] uppercase block">Duration</span>
                <span className="text-white font-medium text-sm">
                  {selectedStep.duration_ms} ms
                </span>
              </div>
              <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                <span className="text-slate-500 text-[10px] uppercase block">Timestamp</span>
                <span className="text-white font-medium text-sm">
                  {selectedStep.started_at ? new Date(selectedStep.started_at).toLocaleTimeString() : 'N/A'}
                </span>
              </div>
            </div>

            {/* Error Stack Trace if Failed */}
            {selectedStep.error && (
              <div className="space-y-2">
                <h4 className="text-xs font-mono font-bold text-rose-400 uppercase">
                  Failure Stack Trace
                </h4>
                <div className="p-3.5 rounded-xl border border-rose-500/30 bg-rose-950/20 font-mono text-xs text-rose-300 whitespace-pre-wrap leading-relaxed select-text">
                  {selectedStep.error.stack_trace || selectedStep.error.message}
                </div>
              </div>
            )}

            {/* Input Payload */}
            <div className="space-y-2">
              <h4 className="text-xs font-mono font-bold text-slate-300 uppercase">
                Input Payload
              </h4>
              <CodePayloadViewer
                title="Resolved Step Input"
                data={selectedStep.input || {}}
              />
            </div>

            {/* Output Payload */}
            <div className="space-y-2">
              <h4 className="text-xs font-mono font-bold text-slate-300 uppercase">
                Output Payload
              </h4>
              <CodePayloadViewer
                title="Produced Step Output"
                data={selectedStep.output || (selectedStep.status === 'failed' ? { error: selectedStep.error?.message } : {})}
              />
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
}
