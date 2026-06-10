/**
 * AutoFlow AI X — Workflow API Service
 * All workflow CRUD, planning, execution, and validation operations.
 */

import { api } from './apiClient';

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
};
