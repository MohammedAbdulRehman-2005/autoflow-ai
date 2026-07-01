# RFC-002: Runtime Architecture
**Depends on:** RFC-000, RFC-001
**Status:** Frozen v1.0

## 1. Execution Pipeline — BUILD NOW

```
Planner
  ↓
Compiler            (DSL → executable graph)
  ↓
Validator            (schema + WorkflowContext checks before running)
  ↓
Dependency Resolver   (execution order / parallel branches)
  ↓
Execution Scheduler
  ↓
Node Executors        (one per plugin, RFC-001 §3)
  ↓
Retry Manager         (honors each node's Retry On Fail / On Error setting)
  ↓
Output Store           (feeds previous_outputs in WorkflowContext, RFC-001 §5)
  ↓
Workflow Intelligence  (post-run analysis, RFC-005 Sprint 5)
```

The Execute Step endpoint (RFC-005 Sprint 2) runs a single node through this same pipeline in isolation — not a separate code path.

## 2. Execution Modes — interface BUILD NOW, most triggers DESIGN SURFACE ONLY

The Execution Scheduler accepts a `mode` field so execution stays extensible:

```
Execution Modes: Manual, Webhook, Schedule, Event, API, CLI, Agent
```

Manual and Schedule are the two modes this build actually wires up (Schedule already exists as a trigger node type). Event, API, CLI, and Agent are enum placeholders reserved for later — don't build their trigger plumbing now, just don't design the scheduler in a way that would need a rewrite to add them.

## 3. Error Boundaries — BUILD NOW

```
Node Error
  ↓
Workflow Error
  ↓
Integration Error     (e.g. Slack API failure)
  ↓
Credential Error       (expired/invalid auth)
  ↓
Compiler Error         (DSL fails to compile)
  ↓
Validation Error       (schema/condition-key mismatch — RFC-005 Appendix bug #1)
```

Each layer determines what the On Error setting (Node Inspector, RFC-005 Sprint 2) can meaningfully offer — e.g. a Credential Error shouldn't offer "Continue," it should surface a reconnect prompt.

## 4. DSL Versioning — BUILD NOW

```
DSL
  version
  created_at
  updated_at
  migration_version
  compiler_version
```

`WorkflowMutationService` bumps `version`/`updated_at` on every accepted patch; the compiler checks `compiler_version` compatibility before running.

## 5. Observability — BUILD NOW

Every mutation, execution, AI patch, integration call, retry, and failure emits telemetry. This isn't a new pipeline — it's making sure the Mutation History (RFC-001 §1) and Event Bus (RFC-001 §6) events that already exist are actually logged and queryable.
