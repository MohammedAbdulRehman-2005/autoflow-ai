import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  ShieldAlert,
  ShieldCheck,
  RotateCw,
  Sparkles,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Terminal,
  FileCode,
  Edit3,
  Archive,
  ArrowRight,
  Zap,
  ExternalLink
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { PanelHeader, GlassCard } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge, PriorityBadge, PolicyBadge } from '../components/ui/Badge';
import { DiffViewer, CodePayloadViewer } from '../components/ui/CodePayloadViewer';
import { Modal } from '../components/ui/Drawer';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingSkeleton } from '../components/ui/LoadingSkeleton';
import { apiBridge } from '../services/apiBridge';
import { useToast } from '../context/ToastContext';

export default function RecoveryCenterPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [incidents, setIncidents] = useState([]);
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');

  // Actions state
  const [isDryRunning, setIsDryRunning] = useState(false);
  const [dryRunResult, setDryRunResult] = useState(null);
  const [isApplying, setIsApplying] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editedPatchJson, setEditedPatchJson] = useState('');
  const [isReasoningExpanded, setIsReasoningExpanded] = useState(false);

  const queryIncidentId = searchParams.get('incident_id');
  const queryRunId = searchParams.get('run_id');

  // ── Load Incidents ────────────────────────────────────────────────────────
  const loadIncidents = useCallback(async () => {
    try {
      const data = await apiBridge.getRecoveryIncidents();
      setIncidents(data || []);

      if (data && data.length > 0) {
        if (queryIncidentId) {
          const match = data.find((i) => i.id === queryIncidentId);
          setSelectedIncident(match || data[0]);
        } else if (queryRunId) {
          const match = data.find((i) => i.run_id === queryRunId);
          setSelectedIncident(match || data[0]);
        } else if (!selectedIncident) {
          setSelectedIncident(data[0]);
        }
      }
    } catch (err) {
      showToast(err.message || 'Failed to load recovery incidents', 'error');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [queryIncidentId, queryRunId, selectedIncident, showToast]);

  useEffect(() => {
    loadIncidents();
  }, [loadIncidents]);

  const handleSelectIncident = (inc) => {
    setSelectedIncident(inc);
    setDryRunResult(null);
    setSearchParams({ incident_id: inc.id });
  };

  const handleDryRun = async () => {
    if (!selectedIncident) return;
    setIsDryRunning(true);
    try {
      const res = await apiBridge.dryRunRecoveryPatch(selectedIncident.id);
      setDryRunResult(res);
      showToast('Dry-run simulation completed successfully', 'success');
    } catch (err) {
      showToast(`Dry-run failed: ${err.message}`, 'error');
    } finally {
      setIsDryRunning(false);
    }
  };

  const handleApplyPatch = async () => {
    if (!selectedIncident) return;
    setIsApplying(true);
    try {
      await apiBridge.applyRecoveryPatch(selectedIncident.id);
      showToast('Recovery patch applied! Workflow execution resumed.', 'success');
      loadIncidents();
    } catch (err) {
      showToast(`Failed to apply patch: ${err.message}`, 'error');
    } finally {
      setIsApplying(false);
    }
  };

  const handleOpenEditPatch = () => {
    if (!selectedIncident) return;
    setEditedPatchJson(
      JSON.stringify(selectedIncident.proposed_action?.patched_payload || {}, null, 2)
    );
    setShowEditModal(true);
  };

  const handleSaveEditedPatch = async () => {
    try {
      const parsed = JSON.parse(editedPatchJson);
      setIsApplying(true);
      await apiBridge.applyRecoveryPatch(selectedIncident.id, parsed);
      setShowEditModal(false);
      showToast('Custom patch applied & pipeline resumed!', 'success');
      loadIncidents();
    } catch (err) {
      showToast(`Invalid JSON: ${err.message}`, 'error');
    } finally {
      setIsApplying(false);
    }
  };

  const handleDismiss = async () => {
    if (!selectedIncident) return;
    try {
      await apiBridge.dismissRecoveryIncident(selectedIncident.id, 'Dismissed by operator');
      showToast('Incident marked as dismissed', 'info');
      loadIncidents();
    } catch (err) {
      showToast(`Dismissal failed: ${err.message}`, 'error');
    }
  };

  const filteredIncidents = incidents.filter((inc) => {
    if (statusFilter === 'all') return true;
    return (inc.status || '').toLowerCase() === statusFilter.toLowerCase();
  });

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <PanelHeader
          title="Recovery Center"
          description="AI-assisted failure diagnosis and policy-checked recovery."
        />
        <LoadingSkeleton rows={5} />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-fade-in">
      <PanelHeader
        title="Recovery Center"
        description="AI-assisted root cause analysis, automated patch proposals, sandboxed dry-runs, and policy verification."
        badge={
          <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs font-mono">
            <ShieldAlert className="h-3.5 w-3.5" />
            <span>Self-Healing Engine Active</span>
          </div>
        }
        actions={
          <Button
            variant="outline"
            size="sm"
            icon={RotateCw}
            isLoading={isRefreshing}
            onClick={() => {
              setIsRefreshing(true);
              loadIncidents();
            }}
          >
            Refresh Queue
          </Button>
        }
      />

      {/* Main Split Screen */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Triage Queue (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between text-xs font-mono px-1">
            <span className="text-slate-400 font-semibold uppercase">
              Failure Incidents ({filteredIncidents.length})
            </span>
            <div className="flex items-center gap-1">
              {['all', 'pending_triage', 'resolved'].map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-2 py-0.5 rounded text-[10px] uppercase transition-colors cursor-pointer ${
                    statusFilter === s
                      ? 'bg-rose-500/20 text-rose-300 font-bold border border-rose-500/30'
                      : 'text-slate-500 hover:text-slate-300'
                  }`}
                >
                  {s.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
            {filteredIncidents.map((inc) => {
              const isSelected = selectedIncident?.id === inc.id;
              return (
                <div
                  key={inc.id}
                  onClick={() => handleSelectIncident(inc)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer space-y-2.5 ${
                    isSelected
                      ? 'border-rose-400/50 bg-slate-900/90 shadow-lg shadow-rose-500/5'
                      : 'border-white/10 bg-slate-900/40 hover:border-white/20 hover:bg-slate-900/60'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-mono font-bold text-rose-300">
                      {inc.id}
                    </span>
                    <PriorityBadge priority={inc.severity} />
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-white leading-snug">
                      {inc.cluster_name}
                    </h4>
                    <p className="text-[11px] text-slate-400 font-mono mt-0.5 truncate">
                      {inc.workflow_name}
                    </p>
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 border-t border-white/5 pt-2">
                    <span>Node: {inc.failed_node_id}</span>
                    <span className="text-cyan-400">
                      {Math.round(inc.diagnosis.confidence * 100)}% Confidence
                    </span>
                  </div>
                </div>
              );
            })}

            {filteredIncidents.length === 0 && (
              <EmptyState
                title="Zero active incidents"
                description="All workflows are operating within healthy parameters. No triage required."
              />
            )}
          </div>
        </div>

        {/* Right: AI Diagnosis & Recovery Stage (8 cols) */}
        <div className="lg:col-span-8">
          {selectedIncident ? (
            <div className="space-y-6">
              {/* Incident Header Card */}
              <GlassCard padding="p-5" className="space-y-4 border-rose-500/20">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-white/10 pb-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h2 className="text-lg font-bold text-white font-display">
                        {selectedIncident.cluster_name}
                      </h2>
                      <PriorityBadge priority={selectedIncident.severity} />
                      <StatusBadge status={selectedIncident.status} size="sm" />
                    </div>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">
                      Workflow: <span className="text-white font-semibold">{selectedIncident.workflow_name}</span> • Run ID: <span className="text-cyan-400">{selectedIncident.run_id}</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      size="xs"
                      variant="outline"
                      onClick={() => navigate(`/executions?run_id=${selectedIncident.run_id}`)}
                    >
                      View Run Trace
                    </Button>
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={handleDismiss}
                      className="text-slate-400 hover:text-slate-200"
                    >
                      Dismiss
                    </Button>
                  </div>
                </div>

                {/* Blast Radius & Impact Badges */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
                  <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                    <span className="text-slate-500 text-[10px] uppercase block">Blast Radius</span>
                    <span className="text-white font-semibold">
                      {selectedIncident.blast_radius?.affected_runs_count || 1} Run(s) Blocked
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                    <span className="text-slate-500 text-[10px] uppercase block">Failed Node</span>
                    <span className="text-rose-400 font-semibold truncate block">
                      {selectedIncident.failed_node_title}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-white/5 border border-white/5">
                    <span className="text-slate-500 text-[10px] uppercase block">AI Confidence</span>
                    <span className="text-emerald-400 font-semibold">
                      {Math.round(selectedIncident.diagnosis.confidence * 100)}% Certainty
                    </span>
                  </div>
                </div>
              </GlassCard>

              {/* AI Diagnosis Card */}
              <GlassCard padding="p-5" className="space-y-4">
                <div className="flex items-center gap-2 text-cyan-400 text-xs font-mono font-bold">
                  <Sparkles className="h-4 w-4" />
                  <span>AI ROOT CAUSE DIAGNOSIS</span>
                </div>

                <div className="p-4 rounded-xl border border-cyan-500/20 bg-cyan-950/10 space-y-2">
                  <p className="text-sm font-semibold text-slate-100 leading-relaxed">
                    {selectedIncident.diagnosis.summary}
                  </p>
                  <p className="text-xs text-slate-400 leading-relaxed font-sans">
                    <span className="text-cyan-400 font-mono font-semibold">Underlying Root Cause: </span>
                    {selectedIncident.diagnosis.root_cause}
                  </p>
                </div>

                {/* Explainable Reasoning Accordion */}
                <div className="border border-white/10 rounded-xl overflow-hidden">
                  <button
                    onClick={() => setIsReasoningExpanded(!isReasoningExpanded)}
                    className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-900/60 hover:bg-slate-900 text-xs font-mono text-slate-300 transition-colors cursor-pointer"
                  >
                    <span>Inspect AI Reasoning Trace & Evidence</span>
                    {isReasoningExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                  </button>

                  {isReasoningExpanded && (
                    <div className="p-4 bg-slate-950/80 space-y-2 text-xs font-mono text-slate-400 border-t border-white/10">
                      {selectedIncident.diagnosis.reasoning_steps?.map((step, idx) => (
                        <div key={idx} className="flex items-start gap-2">
                          <span className="text-cyan-400 font-bold shrink-0">{idx + 1}.</span>
                          <span>{step}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </GlassCard>

              {/* Proposed Recovery Action & Policy Status */}
              <GlassCard padding="p-5" className="space-y-5">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                  <div>
                    <h3 className="text-sm font-bold text-white font-display flex items-center gap-2">
                      <Zap className="h-4 w-4 text-cyan-400" />
                      <span>{selectedIncident.proposed_action?.title}</span>
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {selectedIncident.proposed_action?.description}
                    </p>
                  </div>

                  <PolicyBadge status={selectedIncident.policy?.status} />
                </div>

                {/* Policy Governance Explainer */}
                <div className="p-3 rounded-xl bg-white/5 border border-white/10 text-xs text-slate-400 flex items-center justify-between">
                  <div>
                    <span className="font-mono text-slate-300 font-semibold">{selectedIncident.policy?.name}</span>
                    <span className="mx-2 text-slate-600">•</span>
                    <span>{selectedIncident.policy?.description}</span>
                  </div>
                </div>

                {/* Side-by-side Payload Diff */}
                <DiffViewer
                  before={selectedIncident.proposed_action?.original_payload}
                  after={selectedIncident.proposed_action?.patched_payload}
                  titleBefore="Original Failing Payload"
                  titleAfter="AI Generated Recovery Patch"
                />

                {/* Dry Run Simulation Result */}
                {dryRunResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-950/20 text-xs font-mono text-emerald-300 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                      <span>{dryRunResult.message}</span>
                    </div>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">
                      HTTP {dryRunResult.simulated_status_code} OK
                    </span>
                  </motion.div>
                )}

                {/* Remediation Action Controls */}
                <div className="flex flex-wrap items-center justify-end gap-3 pt-3 border-t border-white/10">
                  <Button
                    size="sm"
                    variant="secondary"
                    icon={Edit3}
                    onClick={handleOpenEditPatch}
                  >
                    Edit Patch Inline
                  </Button>

                  <Button
                    size="sm"
                    variant="outline"
                    icon={Play}
                    isLoading={isDryRunning}
                    onClick={handleDryRun}
                  >
                    Dry-Run Simulation
                  </Button>

                  <Button
                    size="sm"
                    variant="primary"
                    icon={CheckCircle2}
                    isLoading={isApplying}
                    disabled={selectedIncident.status === 'resolved'}
                    onClick={handleApplyPatch}
                  >
                    {selectedIncident.status === 'resolved'
                      ? 'Patch Already Applied'
                      : 'Approve & Resume Pipeline'}
                  </Button>
                </div>
              </GlassCard>
            </div>
          ) : (
            <EmptyState
              title="No incident selected"
              description="Choose a failure incident from the triage queue to inspect diagnosis and recovery patches."
            />
          )}
        </div>
      </div>

      {/* Edit Patch Modal */}
      <Modal
        isOpen={showEditModal}
        onClose={() => setShowEditModal(false)}
        title="Inline Patch Editor"
        description="Fine-tune the proposed JSON payload patch before resuming execution."
        footer={
          <>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setShowEditModal(false)}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              variant="primary"
              onClick={handleSaveEditedPatch}
              isLoading={isApplying}
            >
              Save & Apply
            </Button>
          </>
        }
      >
        <div className="space-y-2">
          <textarea
            value={editedPatchJson}
            onChange={(e) => setEditedPatchJson(e.target.value)}
            rows={12}
            className="w-full rounded-xl border border-white/15 bg-slate-950 p-3 text-xs font-mono text-cyan-300 focus:outline-none focus:border-cyan-400 font-mono leading-relaxed"
          />
        </div>
      </Modal>
    </div>
  );
}
