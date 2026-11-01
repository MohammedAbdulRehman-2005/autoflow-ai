# AutoFlow AI X — UI Reference Notes & UX Patterns Research

This document outlines the UX research and architectural patterns selected for AutoFlow AI X, drawing from leading developer and productivity platforms (Linear, Temporal Cloud, Retool, Inngest, Datadog, n8n, incident.io, and AWS Step Functions).

---

## 1. Product Direction & Persona

**Product Persona:** A developer/productivity SaaS control plane built for mission-critical automation, high-frequency background execution, and zero-downtime self-healing.
**Aesthetic & Feel:** Dark mode first (`#020617` base, frosted glass borders, subtle neon accents), high information density without clutter, keyboard-accessible shortcuts, monospace identifiers (`#run-9841`, `POL-DATA-MUTATION-03`), and zero generic AI chatbot clichés.

---

## 2. Selected UX Patterns by Screen

### A. Overview Dashboard
- **Telemetry-at-a-Glance:** Top-row telemetry cards displaying Active Workflows, 24h Executions, Success Rate percentage, and Active Failure/Approval counts.
- **Urgent Action Banners:** Decoupled priority alerts at the very top of the workspace. If workflows are paused awaiting human approval or failed runs require diagnosis, prominent banners immediately surface them with direct navigation.
- **Fast-Track AI Generator:** A natural language input that doesn't feel like a chat window—instead formatted as a developer prompt engine with immediate "Generate in Studio" intent.
- **Split Workflows & Activity Stream:** Left pane showcases orchestrations with last run metrics; right pane streams live execution events with real-time status pulses.

### B. Workflow Studio (Visual Node Editor)
- **DSL Single Source of Truth:** The visual canvas is a projection of the underlying declarative WorkflowDSL JSON.
- **Custom Node Cards (React Flow):** Color-coded accent bars (triggers = blue, actions = cyan, AI agents = purple, conditions = amber, approvals = violet, recovery = rose). Each node card displays its unique ID, service.operation, status, notes, and hover handles.
- **Hover `+` Add Step Handle:** Inspired by modern flow builders (n8n, Zapier Central), hovering a node displays a quick-add step trigger directly beneath the node for linear insertion without breaking layout.
- **Slide-over Node Inspector:** Clicking any node slides in a focused configuration drawer (Parameters, Error Settings, Isolated Step Execution) without obscuring the canvas context.
- **Dagre Hierarchical Layout:** Automatic DAG layout computation while preserving manual drag coordinates stored in `savedPositions`.

### C. Execution Monitor (Run Timeline & Step Details)
- **Master-Detail Triage Layout:**
  - Left pane: Filterable runs queue (All, Running, Succeeded, Failed, Awaiting Approval) with search by run ID, workflow name, or trigger type.
  - Right pane: Run header with execution metadata (Started at, Duration, Version hash, Idempotency key, Error summary).
- **Step Execution Trace (Gantt/DAG Timeline):**
  - Continuous vertical trace with color-coded node states (green check for success, red cross for failure, blue spinner for active, purple pause for awaiting approval).
  - Explicit duration metrics per step (`110ms`, `1.2s`) to identify bottlenecks immediately.
- **Deep-Dive Step Inspector Drawer:**
  - Clicking any step in the timeline opens a slide-over drawer displaying exact resolved Input JSON, produced Output JSON, and full stack trace for failed steps with 1-click clipboard copy.

### D. Recovery Center (AI-Assisted Failure Diagnosis & Self-Healing)
- **Incident Clustering over Chronological Logs:** Failures are grouped by root-cause clusters (e.g. `SCHEMA_MISMATCH`, `RATE_LIMIT_EXCEEDED`, `CREDENTIAL_EXPIRED`) rather than raw log lines, eliminating operator review fatigue.
- **4-Part Diagnosis Display:**
  1. *Plain-Language Diagnosis:* Concise explanation of what broke and why.
  2. *Explainable Reasoning Trace:* Expandable step-by-step evidence accordion detailing how the AI reached its diagnosis.
  3. *Side-by-Side Payload Diff:* Visual comparison between the failing payload and the AI-generated recovery patch.
  4. *Policy Evaluation Badge:* Real-time governance check (`COMPLIANT_AUTO_APPROVABLE` vs `REQUIRES_HUMAN_SIGN_OFF`).
- **Dry-Run Simulation Before Apply:** Operators can simulate the recovery patch in an isolated sandbox, inspecting the simulated HTTP status code and response time before resuming production execution.
- **Inline Patch Editing:** Operators can fine-tune or override the proposed JSON patch before applying.

### E. Approval Center (Human-In-The-Loop Governance)
- **Decoupled Inbox:** Stakeholders review high-stakes actions without diving into visual graph code.
- **Contextual Transparency:**
  - Requester metadata (e.g. `Financial Auditor Agent (Llama 3.3 70B)`).
  - Key parameters formatted as a quick-read metric grid (e.g. Transaction amount, customer deviance score).
  - SLA countdown timer showing time remaining before automated escalation.
- **Outbound Action Preview:** Exact preview of customer-facing drafts (e.g. emails) or external API mutation payloads.
- **Pre-Flight Compliance Checklist:** Live validation against policies (e.g. Dual-custody thresholds, PII scrubbing, audit signatures).
- **Granular Actions:** Explicit `Authorize & Resume` vs `Reject (with reason dialog)` to avoid mindless rubber-stamping.
