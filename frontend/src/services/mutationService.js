/**
 * AutoFlow AI X — Workflow Mutation Service  (RFC-001 §1)
 * =========================================================
 * The single pipeline for all DSL changes on the frontend.
 *
 * Every change to the workflow goes through applyPatch():
 *   1. Merges the patch into the current DSL
 *   2. Bumps version + updated_at  (RFC-002 §4)
 *   3. Records a MutationRecord in memory (in-memory only — Sprint 1)
 *   4. Emits WorkflowPatched on the event bus
 *   5. Returns the new DSL (caller calls applyDsl() with it)
 *
 * Sprint 3 additions:
 *   - addStep()      — the ONLY method for applying Add Step deltas
 *   - computeDiff()  — static utility for computing before/after diffs
 *
 * CRITICAL: applyPatch(currentDsl, patch, actor, reason)
 *   First arg is ALWAYS the current DSL object (or null for full replace).
 *   Do NOT pass {nodeId, patch, actor, reason} as the first arg — that is
 *   a call-signature bug fixed in Sprint 3 (see WorkflowBuilderPage.jsx).
 *
 * @module mutationService
 */

import { eventBus } from './eventBus';

/**
 * @typedef {Object} MutationRecord
 * @property {string} mutationId
 * @property {Object} patch        - The patch that was applied
 * @property {string} actor        - 'ai' | 'user'
 * @property {string} reason       - Human-readable description
 * @property {string} timestamp    - ISO datetime string
 */

/**
 * @typedef {Object} DiffResult
 * @property {string[]} addedNodeIds    - IDs of nodes present in after but not before
 * @property {string[]} removedNodeIds  - IDs of nodes present in before but not after
 * @property {string[]} addedEdgeKeys   - "src→tgt" strings for new edges
 * @property {string[]} removedEdgeKeys - "src→tgt" strings for removed edges
 */

class WorkflowMutationService {
  constructor() {
    /** @type {MutationRecord[]} */
    this._history = [];
    // _redoStack reserved for Sprint 2 undo/redo
    this._redoStack = [];
  }

  /**
   * Apply a patch to the current DSL.
   *
   * SIGNATURE: applyPatch(currentDsl, patch, actor, reason)
   *   - currentDsl : The current WorkflowDSL state object.
   *                  Pass null ONLY for full DSL replacement (e.g. AI planner result).
   *   - patch      : Partial or full DSL to merge in (patch fields win).
   *   - actor      : 'ai' | 'user'
   *   - reason     : Human-readable description
   *
   * @param {Object|null} currentDsl
   * @param {Object} patch
   * @param {string} actor
   * @param {string} reason
   * @returns {Object} The new DSL after applying the patch
   */
  applyPatch(currentDsl, patch, actor = 'user', reason = '') {
    if (!patch) return currentDsl;

    // 1. Merge patch into current DSL (patch fields win)
    const newDsl = this._merge(currentDsl, patch);

    // 2. Bump version + updated_at (RFC-002 §4)
    newDsl.version = (newDsl.version ?? 1) + 1;
    newDsl.updated_at = new Date().toISOString();

    // 3. Record mutation (in-memory, Sprint 1 only)
    const record = {
      mutationId: crypto.randomUUID(),
      patch,
      actor,
      reason,
      timestamp: newDsl.updated_at,
    };
    this._history.push(record);
    this._redoStack = []; // clear redo stack on new mutation

    // 4. Emit event for any listeners (e.g. sidebar, status bar)
    eventBus.emit('WorkflowPatched', { dsl: newDsl, actor, reason });

    return newDsl;
  }

  /**
   * Replace the entire DSL (e.g. AI planner returns a completely new graph).
   * Convenience wrapper around applyPatch for the common full-replacement case.
   *
   * @param {Object} newDsl  - The new complete DSL from the AI planner
   * @param {string} actor   - 'ai' | 'user'
   * @param {string} reason  - Human-readable description
   * @returns {Object}       - The new DSL with version bumped
   */
  replaceDsl(newDsl, actor = 'ai', reason = 'AI planner') {
    return this.applyPatch(null, newDsl, actor, reason);
  }

  /**
   * Apply a node-position-only patch (from canvas drag stop).
   * Does NOT change the DSL graph structure — just persists positions
   * so dagre doesn't reset them on next render.
   *
   * @param {Object} currentDsl
   * @param {string} nodeId
   * @param {{ x: number, y: number }} position
   * @returns {Object} new DSL
   */
  applyNodePosition(currentDsl, nodeId, position) {
    if (!currentDsl?.nodes) return currentDsl;
    const patch = {
      nodes: currentDsl.nodes.map(n =>
        n.id === nodeId ? { ...n, position } : n
      ),
    };
    return this.applyPatch(currentDsl, patch, 'user', `Node '${nodeId}' repositioned`);
  }

  /**
   * Insert one or more new nodes into the DSL, wiring edges automatically.
   *
   * This is THE ONLY method for applying Add Step deltas from the backend.
   * The backend returns a delta (new_nodes, new_edges, removed_edges);
   * this method is the sole component that merges it into the canonical DSL.
   *
   * @param {Object} currentDsl
   * @param {Object} options
   * @param {Object[]} options.newNodes      — new WorkflowNodeDSL objects
   * @param {Object[]} options.newEdges      — new WorkflowEdgeDSL objects {source_id, target_id, label?}
   * @param {Array<{source_id:string, target_id:string}>} [options.removedEdges]
   *   — edges to remove when splicing new node(s) into the middle of the flow
   * @param {string} [options.actor]
   * @param {string} [options.reason]
   * @returns {Object} new DSL
   */
  addStep(currentDsl, {
    newNodes = [],
    newEdges = [],
    removedEdges = [],
    actor = 'ai',
    reason = 'Add Step',
  } = {}) {
    if (!currentDsl) {
      throw new Error('addStep() requires a non-null currentDsl.');
    }
    if (!newNodes.length) {
      throw new Error('addStep() requires at least one new node.');
    }

    const existingNodes = currentDsl.nodes ?? [];
    const existingEdges = currentDsl.edges ?? [];

    // Remove specified edges (splice insertion)
    const filteredEdges = existingEdges.filter(
      e => !removedEdges.some(
        r => r.source_id === e.source_id && r.target_id === e.target_id
      )
    );

    const patch = {
      nodes: [...existingNodes, ...newNodes],
      edges: [...filteredEdges, ...newEdges],
    };

    return this.applyPatch(
      currentDsl,
      patch,
      actor,
      reason,
    );
  }

  /**
   * Emit WorkflowSaved when the workflow is persisted to the backend.
   * Replaces window.dispatchEvent(new Event('workflow-saved')).
   *
   * @param {{ workflowId: string, name: string }} payload
   */
  notifySaved(payload) {
    eventBus.emit('WorkflowSaved', payload);
  }

  /** Return the full mutation history for debugging. */
  getHistory() {
    return [...this._history];
  }

  /**
   * Update a single parameter on a node.
   * Named intention — preferred over a raw applyPatch() call from NodeInspector.
   *
   * @param {Object} currentDsl
   * @param {string} nodeId
   * @param {string} paramKey
   * @param {*}      value
   * @returns {Object} new DSL
   */
  updateParameter(currentDsl, nodeId, paramKey, value) {
    if (!currentDsl?.nodes) return currentDsl;
    const patch = {
      nodes: currentDsl.nodes.map(n =>
        n.id === nodeId
          ? { ...n, params: { ...(n.params || {}), [paramKey]: value } }
          : n
      ),
    };
    return this.applyPatch(
      currentDsl,
      patch,
      'user',
      `Node '${nodeId}': set param '${paramKey}'`,
    );
  }

  /**
   * Update a node-level setting (always_output_data, execute_once, etc.).
   *
   * @param {Object} currentDsl
   * @param {string} nodeId
   * @param {string} settingKey
   * @param {*}      value
   * @returns {Object} new DSL
   */
  updateSetting(currentDsl, nodeId, settingKey, value) {
    if (!currentDsl?.nodes) return currentDsl;
    const patch = {
      nodes: currentDsl.nodes.map(n =>
        n.id === nodeId ? { ...n, [settingKey]: value } : n
      ),
    };
    return this.applyPatch(
      currentDsl,
      patch,
      'user',
      `Node '${nodeId}': set setting '${settingKey}'`,
    );
  }

  /**
   * Update a node's display label.
   *
   * @param {Object} currentDsl
   * @param {string} nodeId
   * @param {string} label
   * @returns {Object} new DSL
   */
  updateNodeLabel(currentDsl, nodeId, label) {
    if (!currentDsl?.nodes) return currentDsl;
    const patch = {
      nodes: currentDsl.nodes.map(n =>
        n.id === nodeId ? { ...n, label } : n
      ),
    };
    return this.applyPatch(currentDsl, patch, 'user', `Node '${nodeId}': renamed`);
  }

  /**
   * @typedef {Object} Transaction
   * @description Reserved for Sprint 4 undo/redo. Groups multiple applyPatch()
   *   calls under a single atomic mutation record.
   *
   * Usage (future):
   *   const tx = mutationService.beginTransaction('Bulk update');
   *   dsl = mutationService.updateParameter(dsl, nodeId, 'model', 'gpt-4o');
   *   dsl = mutationService.updateSetting(dsl, nodeId, 'retry_on_fail', true);
   *   mutationService.commitTransaction(tx);
   *
   * NOT IMPLEMENTED — placeholder to reserve the API surface.
   */
  beginTransaction(reason) {
    // Sprint 4: implement Transaction grouping for undo/redo
    return { reason, startVersion: undefined };
  }

  commitTransaction(_tx) {
    // Sprint 4: no-op placeholder
  }

  // ── Internal helpers ───────────────────────────────────────────────────────

  /**
   * Merge patch into base. If patch is a full replacement (has `nodes`),
   * use the patch directly (preserving base fields that patch doesn't set).
   * For position-only patches, merge at field level.
   */
  _merge(base, patch) {
    if (!base) {
      // Full replacement — patch is the new DSL
      return { ...patch };
    }
    return { ...base, ...patch };
  }
}



// ─────────────────────────────────────────────────────────────────────────────
// STATIC DIFF UTILITY  (exported separately — no state, no side effects)
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Compute a human-readable diff between two DSLs.
 *
 * @param {Object|null} beforeDsl
 * @param {Object|null} afterDsl
 * @returns {DiffResult}
 */
export function computeDiff(beforeDsl, afterDsl) {
  const beforeNodes = new Set((beforeDsl?.nodes ?? []).map(n => n.id));
  const afterNodes  = new Set((afterDsl?.nodes  ?? []).map(n => n.id));

  const edgeKey = (e) => `${e.source_id}→${e.target_id}`;
  const beforeEdgeKeys = new Set((beforeDsl?.edges ?? []).map(edgeKey));
  const afterEdgeKeys  = new Set((afterDsl?.edges  ?? []).map(edgeKey));

  return {
    addedNodeIds:    [...afterNodes].filter(id => !beforeNodes.has(id)),
    removedNodeIds:  [...beforeNodes].filter(id => !afterNodes.has(id)),
    addedEdgeKeys:   [...afterEdgeKeys].filter(k  => !beforeEdgeKeys.has(k)),
    removedEdgeKeys: [...beforeEdgeKeys].filter(k  => !afterEdgeKeys.has(k)),
  };
}


// Module-level singleton — import this everywhere.
export const mutationService = new WorkflowMutationService();
