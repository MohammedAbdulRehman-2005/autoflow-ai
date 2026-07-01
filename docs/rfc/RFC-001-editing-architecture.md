# RFC-001: Editing Architecture
**Depends on:** RFC-000
**Status:** Frozen v1.0

## Scope key

Every section below is tagged:
- **BUILD NOW** — implemented in the sprints in RFC-005.
- **DESIGN SURFACE ONLY** — the shape is defined here so nothing built now conflicts with it later. Do not implement it ahead of schedule, and do not raise it as a gap during a sprint — it's intentionally deferred.

---

## 1. Workflow Mutation Service — BUILD NOW

**Core rule for the entire product:** every workflow modification, whether initiated by AI or by the user, goes through the same mutation pipeline. The canvas never mutates the graph directly.

```
WorkflowMutationService
  responsibilities:
    - Add Step / Remove Step / Replace Step
    - AI Patch / Manual Patch (drag/rewire on canvas)
    - Edge Insert / Edge Edit
    - Capability Block Expansion (backlog, see RFC-005)

  every call:
    - validates the patch against the DSL schema
    - preserves node IDs and layout
    - updates the canonical DSL (RFC-002 DSL Versioning)
    - writes a mutation history record (below)
    - emits an event on the Event Bus (§6)
    - triggers a graph re-render from the updated DSL
```

**Mutation history & undo/redo.** Every mutation writes a history record — undo/redo replays this history rather than maintaining separate state:

```
MutationRecord
  before_state
  after_state
  patch
  timestamp
  actor        (ai | user)
  reason
```

## 2. AI Service Boundaries — BUILD NOW

| AI Service | Responsibility |
|---|---|
| Planner AI | Creates a new workflow from a user goal |
| Editor AI | Patches an existing workflow (Add Step, Edge menu, Improve with AI) |
| Recommendation AI | Suggests next steps / improvements, doesn't apply them |
| Execution AI | Runs nodes (e.g. the Groq/AI agent node) — never edits the DSL |
| Inspector AI | Explains a node's config/output in plain English |

Only Editor AI and Planner AI may call `WorkflowMutationService`.

*Design surface note:* these five roles could later be reframed as an Agent with Skills (Planner Skill, Editor Skill, Inspector Skill, Optimizer Skill). Not needed for v1 — the five-service split is simpler to implement correctly. Do not build an agent/skill framework now.

## 3. Node Registry & Plugin System — BUILD NOW

Every integration is installable, not hardcoded. A node type is a plugin that registers all of the following in one place:

```
NodeRegistry entry per type ("plugin"):
  - icon
  - parameter schema
  - validator
  - default values
  - executor
  - inspector renderer
  - recommendations
  - documentation link
```

Minimum coverage: Gmail action, Slack action, Groq/AI agent, condition/branch, set_variable, scheduler trigger.

## 4. Capability Registry — BUILD NOW

```
Capability Registry (examples):
  Invoice Processing:   OCR → Extract → Validate → Store → Notify
  Meeting Assistant:    Calendar → AI Summary → Slack → Notion
  Lead Qualification:   HubSpot → AI Score → CRM Update
```

*Forward note:* Capability Registry entries are the basis for Workflow Packages (§12) later.

## 5. Workflow Context — BUILD NOW

Nodes read from a shared, scoped context, not from arbitrary previous nodes directly:

```
WorkflowContext
  variables
  secrets               (resolved via Credential Manager, §8 — never logged or returned to client)
  memory                (short-term state across nodes in one run)
  execution_metadata    (workflow_id, run_id, triggered_by, started_at)
  previous_outputs      (keyed by node_id)
  temporary_storage
  global_config
```

## 6. Event Bus — BUILD NOW

```
Events: Node Added, Node Removed, Workflow Patched,
        Execution Started, Execution Finished,
        Node Failed, Suggestion Generated
```

Components communicate through these events, not direct references to each other.

*Design surface note:* full event sourcing (storing the event log as the source of truth and deriving DSL state by replay — how Figma/Linear scale collaboration) is not needed yet. Keep `MutationRecord` (§1) event-shaped so this migration stays possible later, but don't build a replay engine now.

## 7. Component Ownership — BUILD NOW

```
AIPlanner
WorkflowCanvas
NodeInspector
AddStepDialog
CommandPalette
WorkflowSummary
WorkflowMutationService
NodeRegistry
NodeParameterRegistry
CredentialManager
RecommendationEngine
WorkflowExplanation
```

## 8. Credential Manager — BUILD NOW

Nodes never hold raw secrets:

```
CredentialRegistry → CredentialResolver → Node Executor
```

Node configs reference a `credential_id`; the resolver fetches the actual secret at execution time and places it into `WorkflowContext.secrets` (§5) for that run only.

## 9. Workspace Architecture — DESIGN SURFACE ONLY

```
Workspace
  Projects
  Folders
  Templates
  Credentials
  Variables
  Secrets
  Workflows
  Executions
```

The current build operates within a single implicit workspace — don't build multi-workspace support now. But don't hardcode single-workspace assumptions into the Mutation Service or Node Registry either; this is the shape the product is headed toward.

## 10. Permissions — DESIGN SURFACE ONLY

Roles: Viewer, Editor, Builder, Admin. Not built now. Noted so `MutationRecord.actor` (§1) can later carry a role, not just `ai`/`user`.

## 11. AI Memory — DESIGN SURFACE ONLY

Planner Memory / Workspace Memory / Workflow Memory / Execution Memory. AI stays stateless per-request for v1 — this is a future direction, not a Sprint 0–5 task.

## 12. Workflow Packages — BACKLOG (Phase 8+, see RFC-005)

```
Workflow Package
  Nodes
  Capabilities
  AI prompts
  Validation
  Tests
  Examples
```

Bundles a Capability Registry entry (§4) into something shareable/installable — e.g. "HR Onboarding," "Expense Approval," "Customer Support." Revisit once the Capability Registry is proven with the initial capabilities in this brief; not in Sprints 0–5.
