# AutoFlow AI X — API Integration Checklist

This checklist defines the contract requirements for connecting each frontend screen to future Stage 2/3 backend endpoints. Currently, all screens use `apiBridge.js` which gracefully connects to real endpoints when available and falls back to typed `mockService.js` data otherwise.

---

## Screen 1: Overview Dashboard (`/dashboard`)

- [ ] **`GET /api/v1/workflows`**
  - Query parameters: `?limit=10&offset=0&status=active`
  - Response payload: `{ total: number, workflows: Array<Workflow> }`
  - Required fields per workflow: `id`, `name`, `description`, `status`, `version`, `nodes_count`, `metrics: { success_rate, avg_duration_ms }`.
- [ ] **`GET /api/v1/workflows/runs`**
  - Global or per-workflow run list: `?limit=10`
  - Response payload: `{ runs: Array<Run> }`
  - Required fields per run: `id`, `workflow_id`, `workflow_name`, `status`, `duration_ms`, `started_at`, `error_summary`.
- [ ] **`POST /api/v1/workflows/:id/run`**
  - Trigger manual execution: `{ trigger_payload: object }`
  - Response payload: `{ run_id: string, status: "pending" | "running", idempotency_key: string }`

---

## Screen 2: Workflow Studio (`/workflow-builder`)

- [ ] **`GET /api/v1/workflows/:id`**
  - Fetch complete workflow DSL: `{ id: string, name: string, ai_context_json: WorkflowDSL }`
- [ ] **`PATCH /api/v1/workflows/:id`**
  - Save updated DSL: `{ name: string, dsl_json: WorkflowDSL, status: string }`
- [ ] **`POST /api/v1/ai/plan-workflow`**
  - AI Planner endpoint: `{ workflow_name: string, intent: string, existing_dsl?: object }`
  - Returns validated `WorkflowDSL` JSON.
- [ ] **`POST /api/v1/workflows/:id/nodes/:nodeId/execute`**
  - Single node isolated test execution (Node Inspector "Execute Step").
  - Request: `{ node_id: string, params_override: object, trigger_payload?: object }`
  - Response: `{ status: "success" | "failed", output: object, error?: object, duration_ms: number }`

---

## Screen 3: Execution Monitor (`/executions`)

- [ ] **`GET /api/v1/workflows/:id/runs`**
  - List runs: `?limit=50&offset=0&status=failed`
- [ ] **`GET /api/v1/workflows/:id/runs/:runId`**
  - Fetch detailed run trace:
  - Required fields:
    - `id`, `workflow_id`, `workflow_name`, `status`, `started_at`, `completed_at`, `duration_ms`, `idempotency_key`, `workflow_version`.
    - `step_logs: Array<{ step_id, node_id, node_title, status, duration_ms, started_at, completed_at, input, output, error }>`
- [ ] **`POST /api/v1/workflows/:id/runs/:runId/replay`**
  - Replay run from start or from a specific node step:
  - Request: `{ from_step_id?: string }`
  - Response: `{ new_run_id: string, status: "running" }`
- [ ] **`POST /api/v1/workflows/:id/runs/:runId/cancel`**
  - Terminate an in-flight execution.

---

## Screen 4: Recovery Center (`/recovery`)

- [ ] **`GET /api/v1/recovery/incidents`**
  - Fetch diagnosed failure clusters: `?status=pending_triage`
  - Required response shape:
    ```typescript
    interface RecoveryIncident {
      id: string;
      run_id: string;
      workflow_id: string;
      workflow_name: string;
      failed_node_id: string;
      failed_node_title: string;
      cluster_type: "SCHEMA_MISMATCH" | "RATE_LIMIT_EXCEEDED" | "CREDENTIAL_EXPIRED" | "UNHANDLED_EXCEPTION";
      cluster_name: string;
      severity: "critical" | "high" | "medium" | "low";
      status: "pending_triage" | "resolved" | "dismissed";
      blast_radius: { affected_runs_count: number; downstream_blocked: string[]; financial_risk: string; };
      diagnosis: { summary: string; root_cause: string; confidence: number; reasoning_steps: string[]; };
      proposed_action: {
        type: string;
        title: string;
        description: string;
        original_payload: object;
        patched_payload: object;
        dry_run_available: boolean;
      };
      policy: {
        status: "COMPLIANT_AUTO_APPROVABLE" | "REQUIRES_HUMAN_SIGN_OFF" | "POLICY_VIOLATION";
        policy_id: string;
        name: string;
        description: string;
        is_auto_remediable: boolean;
      };
    }
    ```
- [ ] **`POST /api/v1/recovery/incidents/:id/dry-run`**
  - Simulate patch in sandbox: `{ custom_patch?: object }`
  - Returns simulated HTTP status code, execution duration, and mock verification message.
- [ ] **`POST /api/v1/recovery/incidents/:id/apply`**
  - Apply recovery patch and resume execution: `{ custom_patch?: object }`
- [ ] **`POST /api/v1/recovery/incidents/:id/dismiss`**
  - Dismiss incident with audit reason: `{ reason: string }`

---

## Screen 5: Approval Center (`/approvals`)

- [ ] **`GET /api/v1/governance/approvals`**
  - Fetch pending human approval items: `?status=pending`
  - Required response shape:
    ```typescript
    interface ApprovalRequest {
      id: string;
      run_id: string;
      workflow_id: string;
      workflow_name: string;
      node_id: string;
      node_title: string;
      step_id: string;
      title: string;
      description: string;
      urgency: "critical" | "high" | "medium" | "low";
      status: "pending" | "approved" | "rejected";
      requested_at: string;
      expires_at: string;
      requester: { type: string; name: string; model?: string; };
      target_roles: string[];
      context_data: Record<string, any>;
      action_preview: {
        type: string;
        summary: string;
        draft_email?: { to: string; subject: string; body: string; };
        outbound_payload?: object;
      };
      policy_checks: Array<{ name: string; passed: boolean; note: string; }>;
    }
    ```
- [ ] **`POST /api/v1/governance/approvals/:id/review`**
  - Submit approval or rejection:
  - Request: `{ decision: "APPROVED" | "REJECTED", notes?: string }`
  - Returns updated approval record and resumed run state.
