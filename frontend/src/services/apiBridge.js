/**
 * AutoFlow AI X — API Bridge
 *
 * Provides a strictly partitioned boundary between backend services and UI screens.
 * Supports explicit modes:
 *   - 'demo': Mock data allowed for evaluation/design; clearly marked with _is_demo: true.
 *   - 'staging': Real API required. Zero mock fallbacks on mutations/executions; failures surface immediately.
 *   - 'production': Real API required. Zero mock fallbacks on mutations/executions; failures surface immediately.
 */

import { workflowApi } from './workflowApi';
import { mockService } from './mockService';

const RAW_MODE = import.meta.env.VITE_APP_MODE || (import.meta.env.VITE_USE_MOCKS === 'true' ? 'demo' : 'production');
const APP_MODE = ['demo', 'staging', 'production'].includes(String(RAW_MODE).toLowerCase())
  ? String(RAW_MODE).toLowerCase()
  : 'production';

function markDemo(data) {
  if (!data) return data;
  if (Array.isArray(data)) {
    return data.map(item => (typeof item === 'object' && item !== null ? { ...item, _is_demo: true } : item));
  }
  if (typeof data === 'object') {
    return { ...data, _is_demo: true };
  }
  return data;
}

export const apiBridge = {
  getAppMode() {
    return APP_MODE;
  },

  isDemoMode() {
    return APP_MODE === 'demo';
  },

  // ─── Workflows ────────────────────────────────────────────────────────────
  async getWorkflows(params = {}) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.getWorkflows());
    }
    const res = await workflowApi.list(params);
    return res?.workflows || res?.items || [];
  },

  async getWorkflow(workflowId) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.getWorkflowById(workflowId));
    }
    return await workflowApi.get(workflowId);
  },

  async saveWorkflow(workflow) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.saveWorkflow(workflow));
    }
    // In staging / production: strict real API execution, never mock fallback
    if (workflow.id && !workflow.id.startsWith('wf-')) {
      return await workflowApi.update(workflow.id, workflow);
    }
    return await workflowApi.create(workflow);
  },

  // ─── Runs & Execution Timeline ────────────────────────────────────────────
  async getRuns(params = {}) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.getRuns(params));
    }
    if (!params.workflow_id) {
      return [];
    }
    const res = await workflowApi.listRuns(params.workflow_id, params);
    return res?.runs || [];
  },

  async getRun(workflowId, runId) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.getRunById(runId));
    }
    if (!workflowId) {
      throw new Error("workflowId is required to fetch run status from backend.");
    }
    return await workflowApi.getRun(workflowId, runId);
  },

  async triggerRun(workflowId, triggerPayload = {}) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.triggerRun(workflowId, triggerPayload));
    }
    // In staging / production: real API call required. Failures must surface.
    const res = await workflowApi.run(workflowId, triggerPayload);
    if (!res || !res.run_id) {
      throw new Error("Workflow execution failed: No run_id returned by backend.");
    }
    return res;
  },

  // ─── Recovery Center (AI Diagnosis & Self-Healing - Stage 4) ──────────────
  async getRecoveryIncidents(params = {}) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.getIncidents(params));
    }
    throw new Error("Recovery Center backend service is scheduled for Stage 4 (Temporal Recovery Cluster). Mock data is only permitted in demo mode.");
  },

  async getRecoveryIncident(incidentId) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.getIncidentById(incidentId));
    }
    throw new Error("Recovery incident retrieval requires Stage 4 backend service.");
  },

  async dryRunRecoveryPatch(incidentId) {
    if (APP_MODE === 'demo') {
      await new Promise(r => setTimeout(r, 600));
      const incident = mockService.getIncidentById(incidentId);
      return markDemo(incident?.proposed_action?.dry_run_result || {
        status: 'simulated_success',
        simulated_status_code: 200,
        message: 'Dry run executed successfully with proposed patch (Demo Mode).'
      });
    }
    throw new Error("Dry-run recovery patches require Stage 4 backend cluster.");
  },

  async applyRecoveryPatch(incidentId, customPatch = null) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.applyRecoveryPatch(incidentId, customPatch));
    }
    throw new Error("Applying recovery patches requires Stage 4 backend cluster.");
  },

  async dismissRecoveryIncident(incidentId, reason) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.dismissIncident(incidentId, reason));
    }
    throw new Error("Dismissing recovery incidents requires Stage 4 backend cluster.");
  },

  // ─── Approval Center (Human-In-The-Loop - Stage 4) ─────────────────────────
  async getApprovals(params = {}) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.getApprovals(params));
    }
    throw new Error("Approval Center backend service is scheduled for Stage 4 (Human-in-the-loop Signals). Mock data is only permitted in demo mode.");
  },

  async getApproval(approvalId) {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.getApprovalById(approvalId));
    }
    throw new Error("Approval retrieval requires Stage 4 backend service.");
  },

  async reviewApproval(approvalId, decision, comments = '') {
    if (APP_MODE === 'demo') {
      return markDemo(mockService.reviewApproval(approvalId, decision, comments));
    }
    throw new Error("Approval decisions require Stage 4 backend service.");
  }
};
