/**
 * AutoFlow AI X — Workflow API Service
 * All workflow CRUD, planning, execution, and validation operations.
 */

import { api } from './apiClient';

// Session-level cache for node types — near-static registry data.
// Populated on first call to getNodeTypes(), reused for the browser session.
let _nodeTypesCache = null;

// Session-level cache for capability patterns — fetched once from the backend.
// The Capability Registry is the backend source of truth; this is display-only.
let _capabilitiesCache = null;

export const workflowApi = {
  // ─── Workflow CRUD ────────────────────────────────────────────────────────

  /**
   * List all workflows for the current user.
   * GET /api/v1/workflows
   */
  list: async ({ page = 1, limit = 20, status } = {}) => {
    const offset = (page - 1) * limit;
    let path = `/api/v1/workflows?limit=${limit}&offset=${offset}`;
    if (status) path += `&status=${status}`;
    return api.get(path);
  },

  /**
   * Get a single workflow by ID.
   */
  get: async (workflowId) => {
    return api.get(`/api/v1/workflows/${workflowId}`);
  },

  /**
   * Create a new workflow.
   */
  create: async ({ name, description, dsl }) => {
    return api.post('/api/v1/workflows', { name, description, dsl_json: dsl });
  },

  /**
   * Update an existing workflow.
   */
  update: async (workflowId, { name, description, status, dsl }) => {
    return api.patch(`/api/v1/workflows/${workflowId}`, {
      name,
      description,
      status,
      dsl_json: dsl,
    });
  },

  /**
   * Delete a workflow.
   */
  delete: async (workflowId) => {
    return api.delete(`/api/v1/workflows/${workflowId}`);
  },

  // ─── AI Planner ──────────────────────────────────────────────────────────

  /**
   * Send a natural language prompt to the AI planner.
   * Returns a generated WorkflowDSL JSON.
   * POST /api/v1/ai/plan-workflow
   */
  planWorkflow: async (workflowName, intent, existingDsl = null) => {
    return api.post('/api/v1/ai/plan-workflow', {
      workflow_name: workflowName,
      intent: intent,
      ...(existingDsl ? { existing_dsl: existingDsl } : {}),
    });
  },

  // ─── Validation ──────────────────────────────────────────────────────────

  /**
   * Validate a DSL before saving or running.
   * POST /api/v1/workflows/validate
   */
  validate: async (dsl, workflowId = null) => {
    return api.post('/api/v1/workflows/validate', {
      dsl,
      workflow_id: workflowId,
    });
  },

  // ─── Execution ───────────────────────────────────────────────────────────

  /**
   * Trigger a manual run.
   * POST /api/v1/workflows/:id/run
   * Returns { run_id, workflow_id, status, message }
   */
  run: async (workflowId, triggerPayload = {}) => {
    return api.post(`/api/v1/workflows/${workflowId}/run`, {
      trigger_payload: triggerPayload,
    });
  },

  /**
   * List all runs for a workflow (paginated, newest first).
   * GET /api/v1/workflows/:id/runs
   */
  listRuns: async (workflowId, { limit = 20, offset = 0, status } = {}) => {
    let path = `/api/v1/workflows/${workflowId}/runs?limit=${limit}&offset=${offset}`;
    if (status) path += `&status=${status}`;
    return api.get(path);
  },

  /**
   * Get full detail of a single run including step logs.
   * GET /api/v1/workflows/:id/runs/:runId
   */
  getRun: async (workflowId, runId) => {
    return api.get(`/api/v1/workflows/${workflowId}/runs/${runId}`);
  },

  // ─── Scheduler ───────────────────────────────────────────────────────────

  /**
   * Create or update a schedule for a workflow.
   * POST /api/v1/workflows/:id/schedule
   */
  schedule: async (workflowId, scheduleConfig) => {
    return api.post(`/api/v1/workflows/${workflowId}/schedule`, scheduleConfig);
  },

  /**
   * Remove the schedule for a workflow.
   * DELETE /api/v1/workflows/:id/schedule
   */
  unschedule: async (workflowId) => {
    return api.delete(`/api/v1/workflows/${workflowId}/schedule`);
  },

  /**
   * List all scheduled workflows with next run time.
   * GET /api/v1/workflows/scheduled
   */
  listScheduled: async () => {
    return api.get('/api/v1/workflows/scheduled');
  },

  /**
   * Get next run time for a workflow.
   * GET /api/v1/workflows/:id/next-run
   */
  getNextRun: async (workflowId) => {
    return api.get(`/api/v1/workflows/${workflowId}/next-run`);
  },

  // ─── Node Inspector (Sprint 2) ───────────────────────────────────────────

  /**
   * Get all registered node types (NodeRegistry) as safe DTOs.
   * GET /api/v1/workflows/node-types
   *
   * Cached for the browser session — near-static registry data.
   * Invalidate by calling workflowApi.clearNodeTypesCache().
   */
  getNodeTypes: async () => {
    if (_nodeTypesCache) return _nodeTypesCache;
    const result = await api.get('/api/v1/workflows/node-types');
    _nodeTypesCache = result;
    return result;
  },

  /**
   * Clear the node types session cache (e.g. after plugin hot-reload in dev).
   */
  clearNodeTypesCache: () => {
    _nodeTypesCache = null;
  },

  /**
   * Execute a single node in isolation (Node Inspector “Execute Step”).
   * POST /api/v1/workflows/:workflowId/nodes/:nodeId/execute
   *
   * - Calls WorkflowRunner.execute_single_node() — real credentials, real pipeline.
   * - No DB run record written (ephemeral).
   * - Output is scrubbed of secret-looking keys by the server.
   * - execute_once and always_output_data are no-ops in this context.
   *
   * @param {string} workflowId
   * @param {string} nodeId - DSL node ID (e.g. 'send_email_1')
   * @param {object} opts
   * @param {object} opts.paramsOverride - Latest locally-patched params (read at click time)
   * @param {object} opts.triggerPayload - Optional trigger context
   * @returns {Promise<NodeExecuteResponse>}
   */
  executeNode: async (workflowId, nodeId, { paramsOverride = {}, triggerPayload = {} } = {}) => {
    return api.post(`/api/v1/workflows/${workflowId}/nodes/${nodeId}/execute`, {
      node_id: nodeId,
      params_override: paramsOverride,
      trigger_payload: triggerPayload,
    });
  },

  // ─── Sprint 3: Add Step (Editor AI) ──────────────────────────────────────

  /**
   * Add one or more nodes to an existing workflow using the Editor AI.
   * POST /api/v1/ai/add-step
   *
   * The backend returns ONLY a delta (new_nodes, new_edges, removed_edges).
   * The caller MUST pass this delta to mutationService.addStep() — never
   * apply it to the DSL directly.
   *
   * @param {string|null} workflowId   — Optional, used for audit logging only.
   * @param {object}      currentDsl   — The complete current WorkflowDSL JSON.
   * @param {string}      userIntent   — Free-text description of the desired step.
   * @param {string|null} insertAfterNodeId — ID of the node to insert after; null = append.
   * @returns {Promise<AddStepResponse>}
   */
  addStep: async (workflowId, { currentDsl, userIntent, insertAfterNodeId = null } = {}) => {
    return api.post('/api/v1/ai/add-step', {
      workflow_id: workflowId ?? null,
      current_dsl: currentDsl,
      user_intent: userIntent,
      insert_after_node_id: insertAfterNodeId,
    });
  },

  /**
   * List all registered Capability Registry patterns.
   * GET /api/v1/ai/capabilities
   *
   * Results are cached for the browser session — near-static registry data.
   * The Capability Registry is the backend source of truth; this is display-only.
   *
   * @returns {Promise<CapabilitiesListResponse>}
   */
  getCapabilities: async () => {
    if (_capabilitiesCache) return _capabilitiesCache;
    const result = await api.get('/api/v1/ai/capabilities');
    _capabilitiesCache = result;
    return result;
  },

  /**
   * Clear the capabilities session cache (e.g. after registry hot-reload in dev).
   */
  clearCapabilitiesCache: () => {
    _capabilitiesCache = null;
  },
};
