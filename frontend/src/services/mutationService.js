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
 * Scope changes from plan approval:
 *   - No undo/redo in Sprint 1 (MutationRecord stack kept for Sprint 2)
 *   - Backend WorkflowMutationService deferred — this is frontend-only
 *   - History is in-memory only; no sessionStorage, no DB writes
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
   * For AI-generated workflows the patch is typically the full new DSL.
   * For canvas drag events the patch contains position updates only.
   *
   * @param {Object} currentDsl  - The current WorkflowDSL state
   * @param {Object} patch       - Partial or full DSL to merge in
   * @param {string} actor       - 'ai' | 'user'
   * @param {string} reason      - Human-readable description, e.g. 'AI planner'
   * @returns {Object}           - The new DSL after applying the patch
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

// Module-level singleton — import this everywhere.
export const mutationService = new WorkflowMutationService();
