/**
 * AutoFlow AI X — DiffPreview  (Sprint 3, RFC-000 §3)
 * =====================================================
 * Renders the AI-generated delta before it is applied to the canvas.
 * Shows "Why this change?" explanation, added nodes, wired edges, and
 * Apply / Discard controls.
 *
 * RFC-000 §3: "Every AI modification should produce a diff before it is applied."
 */

import React from 'react';
import { CheckCircle, GitBranch, GitMerge, Sparkles, X, Zap } from 'lucide-react';
import './DiffPreview.css';

/**
 * @param {object}   props
 * @param {object}   props.response          — AddStepResponse from the backend
 * @param {Function} props.onApply           — Called when user clicks Apply
 * @param {Function} props.onDiscard         — Called when user clicks Discard
 * @param {boolean}  [props.applying=false]  — True while the patch is being applied
 */
export default function DiffPreview({ response, onApply, onDiscard, applying = false }) {
  if (!response) return null;

  const { delta, explanation, capability_match, applied_node_ids, registry_driven } = response;
  const newNodes = delta?.new_nodes ?? [];
  const newEdges = delta?.new_edges ?? [];
  const removedEdges = delta?.removed_edges ?? [];

  const isMultiNode = newNodes.length > 1;

  return (
    <div className="diff-preview" role="region" aria-label="Proposed workflow change">

      {/* ── Why this change? ────────────────────────────────────────────── */}
      <div className="diff-preview__explanation">
        <Sparkles size={14} className="diff-preview__sparkle-icon" aria-hidden="true" />
        <p className="diff-preview__explanation-text">{explanation}</p>
      </div>

      {/* ── Capability badge ────────────────────────────────────────────── */}
      {capability_match && (
        <div className="diff-preview__capability-badge" aria-label={`Capability pattern: ${capability_match.capability_name}`}>
          <Zap size={12} aria-hidden="true" />
          <span>
            <strong>{capability_match.capability_name}</strong>
            {' '}· {Math.round(capability_match.confidence * 100)}% match
          </span>
          {capability_match.matched_keywords?.length > 0 && (
            <span className="diff-preview__keywords" aria-label="Matched keywords">
              {capability_match.matched_keywords.slice(0, 3).join(', ')}
            </span>
          )}
        </div>
      )}

      {/* ── Registry-driven badge ───────────────────────────────────────── */}
      {registry_driven && (
        <div className="diff-preview__registry-badge" title="Node parameters come from the NodeRegistry — no LLM-generated params">
          <CheckCircle size={11} aria-hidden="true" />
          Registry-driven
        </div>
      )}

      {/* ── Added nodes ─────────────────────────────────────────────────── */}
      {newNodes.length > 0 && (
        <section className="diff-preview__section" aria-label="Nodes to add">
          <h4 className="diff-preview__section-title">
            <GitBranch size={13} aria-hidden="true" />
            {newNodes.length === 1 ? 'Adding 1 node' : `Adding ${newNodes.length} nodes`}
          </h4>
          <ul className="diff-preview__node-list" role="list">
            {newNodes.map((n) => (
              <li key={n.id} className="diff-preview__node-chip diff-preview__node-chip--added">
                <span className="diff-preview__node-label">{n.label ?? n.id}</span>
                <span className="diff-preview__node-meta">{n.service}.{n.operation}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── Edge changes ────────────────────────────────────────────────── */}
      {(newEdges.length > 0 || removedEdges.length > 0) && (
        <section className="diff-preview__section" aria-label="Edge changes">
          <h4 className="diff-preview__section-title">
            <GitMerge size={13} aria-hidden="true" />
            Connections
          </h4>
          <ul className="diff-preview__edge-list" role="list">
            {newEdges.map((e, i) => (
              <li key={`new-${i}`} className="diff-preview__edge-chip diff-preview__edge-chip--added">
                + {e.source_id} → {e.target_id}
              </li>
            ))}
            {removedEdges.map((e, i) => (
              <li key={`rem-${i}`} className="diff-preview__edge-chip diff-preview__edge-chip--removed">
                − {e.source_id} → {e.target_id}
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── Actions ─────────────────────────────────────────────────────── */}
      <div className="diff-preview__actions">
        <button
          id="diff-preview-discard"
          className="diff-preview__btn diff-preview__btn--ghost"
          onClick={onDiscard}
          disabled={applying}
          aria-label="Discard this change"
        >
          <X size={14} aria-hidden="true" />
          Discard
        </button>
        <button
          id="diff-preview-apply"
          className="diff-preview__btn diff-preview__btn--primary"
          onClick={onApply}
          disabled={applying}
          aria-label={applying ? 'Applying change…' : 'Apply this change to the workflow'}
        >
          {applying ? (
            <span className="diff-preview__spinner" aria-hidden="true" />
          ) : (
            <CheckCircle size={14} aria-hidden="true" />
          )}
          {applying ? 'Applying…' : 'Apply'}
        </button>
      </div>
    </div>
  );
}
