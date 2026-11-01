import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  PauseCircle,
  CheckCircle2,
  XCircle,
  Clock,
  RotateCw,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  FileText,
  UserCheck,
  Send,
  MessageSquare,
  ChevronRight,
  ExternalLink,
  Bot
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

import { PanelHeader, GlassCard } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { StatusBadge, PriorityBadge } from '../components/ui/Badge';
import { CodePayloadViewer } from '../components/ui/CodePayloadViewer';
import { Modal } from '../components/ui/Drawer';
import { EmptyState } from '../components/ui/EmptyState';
import { LoadingSkeleton } from '../components/ui/LoadingSkeleton';
import { apiBridge } from '../services/apiBridge';
import { useToast } from '../context/ToastContext';

export default function ApprovalCenterPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { showToast } = useToast();

  const [approvals, setApprovals] = useState([]);
  const [selectedApproval, setSelectedApproval] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState('pending');

  // Decision Modal
  const [isDecisionLoading, setIsDecisionLoading] = useState(false);
  const [rejectModalOpen, setRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  const queryApprovalId = searchParams.get('approval_id');

  // ── Load Approvals ────────────────────────────────────────────────────────
  const loadApprovals = useCallback(async () => {
    try {
      const data = await apiBridge.getApprovals();
      setApprovals(data || []);

      if (data && data.length > 0) {
        if (queryApprovalId) {
          const match = data.find((a) => a.id === queryApprovalId);
          setSelectedApproval(match || data[0]);
        } else if (!selectedApproval) {
          setSelectedApproval(data[0]);
        }
      }
    } catch (err) {
      showToast(err.message || 'Failed to load approvals queue', 'error');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [queryApprovalId, selectedApproval, showToast]);

  useEffect(() => {
    loadApprovals();
  }, [loadApprovals]);

  const handleSelectApproval = (item) => {
    setSelectedApproval(item);
    setSearchParams({ approval_id: item.id });
  };

  const handleApprove = async () => {
    if (!selectedApproval) return;
    setIsDecisionLoading(true);
    try {
      await apiBridge.reviewApproval(
        selectedApproval.id,
        'APPROVED',
        'Authorized by security operator via Approval Center'
      );
      showToast(`Action approved! Workflow execution resumed.`, 'success');
      loadApprovals();
    } catch (err) {
      showToast(`Approval failed: ${err.message}`, 'error');
    } finally {
      setIsDecisionLoading(false);
    }
  };

  const handleConfirmReject = async () => {
    if (!selectedApproval) return;
    setIsDecisionLoading(true);
    try {
      await apiBridge.reviewApproval(
        selectedApproval.id,
        'REJECTED',
        rejectReason || 'Action rejected by operator'
      );
      setRejectModalOpen(false);
      setRejectReason('');
      showToast(`Action rejected. Workflow paused and flagged.`, 'info');
      loadApprovals();
    } catch (err) {
      showToast(`Rejection failed: ${err.message}`, 'error');
    } finally {
      setIsDecisionLoading(false);
    }
  };

  const filteredApprovals = approvals.filter((a) => {
    if (statusFilter === 'all') return true;
    return (a.status || '').toLowerCase() === statusFilter.toLowerCase();
  });

  if (isLoading) {
    return (
      <div className="space-y-6 max-w-7xl mx-auto">
        <PanelHeader
          title="Approval Center"
          description="Human-in-the-loop authorization queue for sensitive agent actions."
        />
        <LoadingSkeleton rows={5} />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-fade-in">
      <PanelHeader
        title="Approval Center"
        description="Human-in-the-loop governance for AI agent decisions, high-value transactions, and customer-facing outbound actions."
        badge={
          <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-mono">
            <PauseCircle className="h-3.5 w-3.5" />
            <span>Governance Boundary Enforced</span>
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
              loadApprovals();
            }}
          >
            Refresh Queue
          </Button>
        }
      />

      {/* Main Split-Screen */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Approvals Queue (4 cols) */}
        <div className="lg:col-span-4 space-y-3">
          <div className="flex items-center justify-between text-xs font-mono px-1">
            <span className="text-slate-400 font-semibold uppercase">
              Pending Requests ({filteredApprovals.length})
            </span>
            <div className="flex items-center gap-1">
              {['pending', 'approved', 'rejected', 'all'].map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`px-2 py-0.5 rounded text-[10px] uppercase transition-colors cursor-pointer ${
                    statusFilter === s
                      ? 'bg-purple-500/20 text-purple-300 font-bold border border-purple-500/30'
                      : 'text-slate-500 hover:text-slate-300'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-y-auto pr-1">
            {filteredApprovals.map((item) => {
              const isSelected = selectedApproval?.id === item.id;
              return (
                <div
                  key={item.id}
                  onClick={() => handleSelectApproval(item)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer space-y-2.5 ${
                    isSelected
                      ? 'border-purple-400/50 bg-slate-900/90 shadow-lg shadow-purple-500/5'
                      : 'border-white/10 bg-slate-900/40 hover:border-white/20 hover:bg-slate-900/60'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-mono font-bold text-purple-300">
                      {item.id}
                    </span>
                    <PriorityBadge priority={item.urgency} />
                  </div>

                  <div>
                    <h4 className="text-xs font-bold text-white leading-snug">
                      {item.title}
                    </h4>
                    <p className="text-[11px] text-slate-400 font-mono mt-0.5 truncate">
                      {item.workflow_name}
                    </p>
                  </div>

                  <div className="flex items-center justify-between text-[11px] font-mono text-slate-500 border-t border-white/5 pt-2">
                    <span>Target: {item.target_roles?.[0] || 'Operator'}</span>
                    <span className="text-purple-300">
                      <Clock className="h-3 w-3 inline mr-1" />
                      Expires in 23h
                    </span>
                  </div>
                </div>
              );
            })}

            {filteredApprovals.length === 0 && (
              <EmptyState
                title="No approval requests"
                description="The approval queue is empty. Workflows requiring human sign-off will appear here automatically."
              />
            )}
          </div>
        </div>

        {/* Right: Action Details & Decision Stage (8 cols) */}
        <div className="lg:col-span-8">
          {selectedApproval ? (
            <div className="space-y-6">
              {/* Request Header Card */}
              <GlassCard padding="p-5" className="space-y-4 border-purple-500/20">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-white/10 pb-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h2 className="text-lg font-bold text-white font-display">
                        {selectedApproval.title}
                      </h2>
                      <PriorityBadge priority={selectedApproval.urgency} />
                      <StatusBadge status={selectedApproval.status} size="sm" />
                    </div>
                    <p className="text-xs text-slate-400 font-mono mt-0.5">
                      Workflow: <span className="text-white font-semibold">{selectedApproval.workflow_name}</span> • Run: <span className="text-cyan-400">{selectedApproval.run_id}</span>
                    </p>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      size="xs"
                      variant="outline"
                      onClick={() => navigate(`/executions?run_id=${selectedApproval.run_id}`)}
                    >
                      View Live Run
                    </Button>
                  </div>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed font-sans">
                  {selectedApproval.description}
                </p>

                {/* Requester & SLA Metadata */}
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono">
                  <div className="p-3 rounded-xl bg-white/5 border border-white/5 space-y-0.5">
                    <span className="text-slate-500 text-[10px] uppercase block">Requested By</span>
                    <span className="text-cyan-300 font-semibold flex items-center gap-1.5 truncate">
                      <Bot className="h-3.5 w-3.5 text-cyan-400 shrink-0" />
                      {selectedApproval.requester?.name}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-white/5 border border-white/5 space-y-0.5">
                    <span className="text-slate-500 text-[10px] uppercase block">Authorized Roles</span>
                    <span className="text-white font-semibold truncate block">
                      {selectedApproval.target_roles?.join(', ')}
                    </span>
                  </div>
                  <div className="p-3 rounded-xl bg-white/5 border border-white/5 space-y-0.5">
                    <span className="text-slate-500 text-[10px] uppercase block">SLA Expiration</span>
                    <span className="text-purple-300 font-semibold flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5 text-purple-400 shrink-0" />
                      {new Date(selectedApproval.expires_at).toLocaleDateString()} 17:15 UTC
                    </span>
                  </div>
                </div>
              </GlassCard>

              {/* Context Triggering Data */}
              <GlassCard padding="p-5" className="space-y-3">
                <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <FileText className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Evaluation Context & Trigger Parameters</span>
                </h3>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
                  {Object.entries(selectedApproval.context_data || {}).map(([k, v]) => (
                    <div key={k} className="p-2.5 rounded-lg bg-slate-950/60 border border-white/5">
                      <span className="text-[10px] text-slate-500 block truncate">{k}</span>
                      <span className="text-white font-medium truncate block" title={String(v)}>
                        {typeof v === 'number' && k.includes('amount') ? `$${v.toLocaleString()}` : String(v)}
                      </span>
                    </div>
                  ))}
                </div>
              </GlassCard>

              {/* Action Preview */}
              <GlassCard padding="p-5" className="space-y-4">
                <div className="space-y-1">
                  <h3 className="text-sm font-bold text-white font-display flex items-center gap-2">
                    <Send className="h-4 w-4 text-purple-400" />
                    <span>Proposed Outbound Action</span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    {selectedApproval.action_preview?.summary}
                  </p>
                </div>

                {selectedApproval.action_preview?.draft_email ? (
                  <div className="p-4 rounded-xl border border-white/10 bg-slate-950/80 space-y-2 text-xs font-mono">
                    <div className="text-slate-400">
                      <span className="text-slate-500">To:</span> {selectedApproval.action_preview.draft_email.to}
                    </div>
                    <div className="text-slate-400">
                      <span className="text-slate-500">Subject:</span> {selectedApproval.action_preview.draft_email.subject}
                    </div>
                    <div className="pt-2 border-t border-white/5 whitespace-pre-wrap text-slate-200 font-sans leading-relaxed">
                      {selectedApproval.action_preview.draft_email.body}
                    </div>
                  </div>
                ) : (
                  <CodePayloadViewer
                    title="Outbound Action Payload"
                    data={selectedApproval.action_preview?.outbound_payload || {}}
                  />
                )}
              </GlassCard>

              {/* Policy & Compliance Checklist */}
              <GlassCard padding="p-5" className="space-y-3">
                <h3 className="text-xs font-mono font-bold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Governance & Policy Pre-Flight Checks</span>
                </h3>

                <div className="space-y-2">
                  {selectedApproval.policy_checks?.map((check, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl border border-white/5 bg-slate-950/40 flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center gap-2.5">
                        <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                        <div>
                          <span className="font-semibold text-slate-200">{check.name}</span>
                          <p className="text-[11px] text-slate-400 mt-0.5">{check.note}</p>
                        </div>
                      </div>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold uppercase">
                        Passed
                      </span>
                    </div>
                  ))}
                </div>
              </GlassCard>

              {/* Decision Action Bar */}
              {selectedApproval.status === 'pending' ? (
                <div className="flex items-center justify-end gap-3 p-4 rounded-xl border border-white/10 bg-slate-900/60 backdrop-blur-xl">
                  <Button
                    size="sm"
                    variant="danger"
                    icon={XCircle}
                    onClick={() => setRejectModalOpen(true)}
                  >
                    Reject Action
                  </Button>
                  <Button
                    size="sm"
                    variant="success"
                    icon={CheckCircle2}
                    isLoading={isDecisionLoading}
                    onClick={handleApprove}
                    className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold"
                  >
                    Authorize & Resume Workflow
                  </Button>
                </div>
              ) : (
                <div className="p-4 rounded-xl border border-white/10 bg-slate-900/40 text-center text-xs font-mono text-slate-400">
                  This request was {selectedApproval.status} on{' '}
                  {new Date(selectedApproval.decided_at).toLocaleString()} by {selectedApproval.decided_by}.
                </div>
              )}
            </div>
          ) : (
            <EmptyState
              title="No request selected"
              description="Choose an approval request from the queue to review context and authorize execution."
            />
          )}
        </div>
      </div>

      {/* Reject Modal */}
      <Modal
        isOpen={rejectModalOpen}
        onClose={() => setRejectModalOpen(false)}
        title="Reject Proposed Action"
        description="Provide a reason for rejecting this automated step. The execution will pause and flag an exception."
        footer={
          <>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setRejectModalOpen(false)}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              variant="danger"
              isLoading={isDecisionLoading}
              onClick={handleConfirmReject}
            >
              Confirm Rejection
            </Button>
          </>
        }
      >
        <div className="space-y-3">
          <label className="text-xs font-mono text-slate-400 block">
            Rejection Reason / Operator Notes
          </label>
          <textarea
            value={rejectReason}
            onChange={(e) => setRejectReason(e.target.value)}
            placeholder="e.g. Transaction volume violates quarterly compliance guidelines..."
            rows={4}
            className="w-full rounded-xl border border-white/10 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-600 focus:outline-none focus:border-rose-400 font-sans"
          />
        </div>
      </Modal>
    </div>
  );
}
