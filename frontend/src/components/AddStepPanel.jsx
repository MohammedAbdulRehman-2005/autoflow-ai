/**
 * AutoFlow AI X — AddStepPanel  (Sprint 3, RFC-001 §1, §4)
 * ==========================================================
 * A sliding right-side panel for adding nodes to the workflow.
 *
 * Layout:
 *   - AI input (hero — full-width, prominent)
 *   - DiffPreview (appears after AI responds)
 *   - "Browse steps" grouped by app (secondary, collapsed by default)
 *
 * Trigger:
 *   - + button in the Left Toolbar
 *   - Per-node + handle that appears on hover
 *   (Ctrl/Cmd+K is reserved for the future global Command Palette)
 *
 * Responsibilities:
 *   - Calls workflowApi.addStep() to get the delta from the backend
 *   - Calls mutationService.addStep() to apply the delta (the ONLY place)
 *   - Never applies DSL changes directly
 *
 * RFC-000 §3: Every AI patch produces a diff before it is applied.
 * RFC-000 §4: 150–250ms animations; 12px panels, 8px buttons; 8-point grid.
 */

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronDown, ChevronRight, Loader2, Plus, Sparkles, X } from 'lucide-react';
import DiffPreview from './DiffPreview';
import { workflowApi } from '../services/workflowApi';
import { mutationService } from '../services/mutationService';
import {
  buildInsertionPositions,
  getLastNodePosition,
  getNodePosition,
} from '../utils/layoutHelpers';
import './AddStepPanel.css';

/**
 * @param {object}    props
 * @param {boolean}   props.open                — Panel visibility
 * @param {Function}  props.onClose             — Called when the panel is closed
 * @param {object}    props.currentDsl          — Current WorkflowDSL state
 * @param {Function}  props.applyDsl            — Callback to push a new DSL into canvas
 * @param {string|null} props.insertAfterNodeId — Node ID for contextual + handle; null = append
 * @param {import('@xyflow/react').Node[]} props.rfNodes — React Flow nodes for layout
 */
export default function AddStepPanel({
  open,
  onClose,
  currentDsl,
  applyDsl,
  insertAfterNodeId = null,
  rfNodes = [],
}) {
  const [intent, setIntent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [pendingResponse, setPendingResponse] = useState(null);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState(null);
  const [capabilities, setCapabilities] = useState([]);
  const [nodeTypes, setNodeTypes] = useState([]);
  const [browseOpen, setBrowseOpen] = useState(false);
  const [groupedNodes, setGroupedNodes] = useState({});

  const inputRef = useRef(null);
  const workflowId = typeof window !== 'undefined'
    ? localStorage.getItem('current_workflow_id')
    : null;

  // ── Focus AI input when panel opens ─────────────────────────────────────
  useEffect(() => {
    if (open) {
      setPendingResponse(null);
      setError(null);
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setIntent('');
      setPendingResponse(null);
      setApplying(false);
    }
  }, [open]);

  // ── Load capability patterns (backend source of truth, cached) ───────────
  useEffect(() => {
    if (!open) return;
    workflowApi.getCapabilities()
      .then(res => setCapabilities(res?.patterns ?? []))
      .catch(err => console.warn('Could not load capabilities:', err));
  }, [open]);

  // ── Load node types for Browse steps (cached) ────────────────────────────
  useEffect(() => {
    if (!open) return;
    workflowApi.getNodeTypes()
      .then(res => {
        const types = res?.node_types ?? [];
        setNodeTypes(types);
        // Group by service, exclude trigger nodes
        const grouped = {};
        types.filter(t => t.node_type !== 'trigger').forEach(t => {
          const service = t.service || 'other';
          if (!grouped[service]) grouped[service] = [];
          grouped[service].push(t);
        });
        setGroupedNodes(grouped);
      })
      .catch(err => console.warn('Could not load node types:', err));
  }, [open]);

  // ── Keyboard: Esc closes panel ───────────────────────────────────────────
  useEffect(() => {
    if (!open) return;
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  // ── Submit AI intent ─────────────────────────────────────────────────────
  const handleSuggest = useCallback(async () => {
    const trimmed = intent.trim();
    if (!trimmed || isLoading || !currentDsl) return;

    setIsLoading(true);
    setError(null);
    setPendingResponse(null);

    try {
      const response = await workflowApi.addStep(workflowId, {
        currentDsl,
        userIntent: trimmed,
        insertAfterNodeId,
      });
      setPendingResponse(response);
    } catch (err) {
      setError(err?.message ?? 'AI request failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  }, [intent, isLoading, currentDsl, workflowId, insertAfterNodeId]);

  const handleKeyDown = (e) => {
    if ((e.key === 'Enter') && !e.shiftKey) {
      e.preventDefault();
      handleSuggest();
    }
  };

  // ── Apply the AI delta ────────────────────────────────────────────────────
  const handleApply = useCallback(async () => {
    if (!pendingResponse || !currentDsl) return;
    setApplying(true);

    try {
      const { delta, explanation, capability_match } = pendingResponse;

      // Assign canvas positions using layoutHelpers (no hardcoded offsets)
      const anchorPosition = insertAfterNodeId
        ? getNodePosition(rfNodes, insertAfterNodeId)
        : getLastNodePosition(rfNodes);

      const newNodeIds = delta.new_nodes.map(n => n.id);
      const positions = buildInsertionPositions(anchorPosition, newNodeIds);

      // Annotate new nodes with their canvas positions
      const positionedNewNodes = delta.new_nodes.map(n => ({
        ...n,
        position: positions[n.id],
      }));

      const reason = capability_match
        ? `Add Step (${capability_match.capability_name})`
        : `Add Step: ${explanation?.slice(0, 50) ?? 'AI suggestion'}`;

      // mutationService.addStep() is the ONLY component that applies the delta
      const newDsl = mutationService.addStep(currentDsl, {
        newNodes: positionedNewNodes,
        newEdges: delta.new_edges,
        removedEdges: delta.removed_edges,
        actor: 'ai',
        reason,
      });

      applyDsl(newDsl);
      onClose();
    } catch (err) {
      setError(err?.message ?? 'Failed to apply change.');
      setApplying(false);
    }
  }, [pendingResponse, currentDsl, insertAfterNodeId, rfNodes, applyDsl, onClose]);

  // ── Discard pending AI response ─────────────────────────────────────────
  const handleDiscard = useCallback(() => {
    setPendingResponse(null);
    setError(null);
    setTimeout(() => inputRef.current?.focus(), 50);
  }, []);

  // ── Manual node pick (Browse steps) ─────────────────────────────────────
  const handleBrowsePick = useCallback((nodeType) => {
    if (!currentDsl) return;
    setError(null);

    try {
      // Build a minimal node from registry data
      const anchorPosition = insertAfterNodeId
        ? getNodePosition(rfNodes, insertAfterNodeId)
        : getLastNodePosition(rfNodes);

      const newId = `${nodeType.service}_${nodeType.operation}_${Date.now().toString(36)}`;
      const newNode = {
        id: newId,
        type: nodeType.node_type,
        service: nodeType.service,
        operation: nodeType.operation,
        label: nodeType.label,
        params: { ...(nodeType.default_params ?? {}) },
        credential_id: null,
        on_success: null,
        on_failure: null,
        error_policy: 'stop',
        notes: null,
        display_note_in_flow: false,
        position: buildInsertionPositions(anchorPosition, [newId])[newId],
      };

      // Determine anchor node (last terminal node or insert_after)
      const existingEdges = currentDsl.edges ?? [];
      const nodesWithOutgoing = new Set(existingEdges.map(e => e.source_id));
      const anchor = insertAfterNodeId
        ?? (currentDsl.nodes ?? []).filter(n => !nodesWithOutgoing.has(n.id)).slice(-1)[0]?.id
        ?? null;

      const newEdge = anchor ? { source_id: anchor, target_id: newId } : null;

      // mutationService.addStep() is the ONLY component that applies the delta
      const newDsl = mutationService.addStep(currentDsl, {
        newNodes: [newNode],
        newEdges: newEdge ? [newEdge] : [],
        removedEdges: [],
        actor: 'user',
        reason: `Browse: added ${nodeType.label}`,
      });

      applyDsl(newDsl);
      onClose();
    } catch (err) {
      setError(err?.message ?? 'Failed to add node.');
    }
  }, [currentDsl, insertAfterNodeId, rfNodes, applyDsl, onClose]);

  if (!open) return null;

  const contextLabel = insertAfterNodeId
    ? `after "${insertAfterNodeId}"`
    : 'to end of workflow';

  return (
    <div
      className="add-step-panel"
      role="dialog"
      aria-modal="true"
      aria-label="Add Step"
    >
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="add-step-panel__header">
        <div className="add-step-panel__header-left">
          <Plus size={15} className="add-step-panel__header-icon" aria-hidden="true" />
          <span className="add-step-panel__header-title">Add Step</span>
          {insertAfterNodeId && (
            <span className="add-step-panel__context-label" title={contextLabel}>
              {contextLabel}
            </span>
          )}
        </div>
        <button
          id="add-step-close"
          className="add-step-panel__close-btn"
          onClick={onClose}
          aria-label="Close Add Step panel"
        >
          <X size={15} aria-hidden="true" />
        </button>
      </div>

      {/* ── AI Input (hero) ───────────────────────────────────────────────── */}
      <div className="add-step-panel__ai-section">
        <div className="add-step-panel__ai-label">
          <Sparkles size={12} aria-hidden="true" />
          Describe what should happen next
        </div>
        <textarea
          id="add-step-ai-input"
          ref={inputRef}
          className="add-step-panel__ai-input"
          placeholder={`e.g. "Send a Slack notification", "Classify the email with AI", "Invoice Processing"`}
          value={intent}
          onChange={e => setIntent(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={3}
          aria-label="Describe the next step in natural language"
          disabled={isLoading || applying}
        />

        {/* Capability chips (from backend registry) */}
        {capabilities.length > 0 && !pendingResponse && (
          <div className="add-step-panel__capability-chips" aria-label="Suggested capabilities">
            {capabilities.slice(0, 4).map(cap => (
              <button
                key={cap.name}
                className="add-step-panel__cap-chip"
                onClick={() => setIntent(cap.name)}
                type="button"
                aria-label={`Use capability: ${cap.name}`}
              >
                {cap.name}
              </button>
            ))}
          </div>
        )}

        <button
          id="add-step-suggest"
          className="add-step-panel__suggest-btn"
          onClick={handleSuggest}
          disabled={isLoading || applying || !intent.trim() || !currentDsl}
          aria-label={isLoading ? 'Generating suggestion…' : 'Generate AI suggestion'}
        >
          {isLoading ? (
            <Loader2 size={14} className="add-step-panel__spinner" aria-hidden="true" />
          ) : (
            <Sparkles size={14} aria-hidden="true" />
          )}
          {isLoading ? 'Thinking…' : 'Suggest'}
        </button>
      </div>

      {/* ── Error ─────────────────────────────────────────────────────────── */}
      {error && (
        <div className="add-step-panel__error" role="alert">
          {error}
        </div>
      )}

      {/* ── DiffPreview ─────────────────────────────────────────────────── */}
      {pendingResponse && (
        <div className="add-step-panel__diff-section">
          <DiffPreview
            response={pendingResponse}
            onApply={handleApply}
            onDiscard={handleDiscard}
            applying={applying}
          />
        </div>
      )}

      {/* ── Browse steps (secondary, collapsed by default) ──────────────── */}
      <div className="add-step-panel__browse-section">
        <button
          id="add-step-browse-toggle"
          className="add-step-panel__browse-toggle"
          onClick={() => setBrowseOpen(v => !v)}
          aria-expanded={browseOpen}
          aria-controls="add-step-browse-list"
        >
          {browseOpen
            ? <ChevronDown size={12} aria-hidden="true" />
            : <ChevronRight size={12} aria-hidden="true" />}
          <span>or browse steps</span>
        </button>

        {browseOpen && (
          <div
            id="add-step-browse-list"
            className="add-step-panel__browse-list"
            role="list"
          >
            {Object.entries(groupedNodes).map(([service, types]) => (
              <div key={service} className="add-step-panel__browse-group" role="listitem">
                <div className="add-step-panel__browse-group-header">
                  {service}
                </div>
                {types.map(t => (
                  <button
                    key={`${t.service}.${t.operation}`}
                    className="add-step-panel__browse-item"
                    onClick={() => handleBrowsePick(t)}
                    type="button"
                    aria-label={`Add ${t.label}`}
                  >
                    {t.label}
                    <span className="add-step-panel__browse-item-op">{t.operation}</span>
                  </button>
                ))}
              </div>
            ))}
            {Object.keys(groupedNodes).length === 0 && (
              <p className="add-step-panel__browse-empty">Loading node types…</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
