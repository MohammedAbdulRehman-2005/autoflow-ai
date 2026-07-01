# RFC-005: Implementation Roadmap
**Depends on:** RFC-000 through RFC-004
**Status:** Frozen v1.0

Six sprints. Each produces working software — you never sit on pure infrastructure for weeks before a user sees anything. Every sprint ends against the RFC-000 §5 Definition of Done. Ready-to-send prompt text for each sprint lives in `IMPLEMENTATION_PROMPTS.md`.

## Sprint 0 — Foundation Design
Repo inspection, architecture analysis, confirm existing DSL/canvas library/state management, design (not build) WorkflowMutationService, NodeRegistry, CredentialManager, WorkflowContext. Output: a written plan. Wait for approval before Sprint 1.

## Sprint 1 — Foundation Build
Implement WorkflowMutationService (+ mutation history/undo-redo), NodeRegistry & plugin structure (six node types, RFC-001 §3), CredentialManager (RFC-001 §8), WorkflowContext skeleton (RFC-001 §5), DSL version fields (RFC-002 §4). Fix the three known bugs (Appendix below) as part of this pass. Regression tests required.

## Sprint 2 — First User Value: Node Inspector
Node Inspector Modal, Execute Step endpoint, Parameter Registry wiring — all driven by Sprint 1's registries, executing through the runtime pipeline (RFC-002 §1) in isolation.

## Sprint 3 — AI-Native Editing
Replace Add Node with Add Step (AI-first), DSL patch diffing, Capability Registry (RFC-001 §4) wiring into intent parsing.

## Sprint 4 — Productivity
Command Palette, AI Recommendations + Improve with AI, Edge AI menu.

## Sprint 5 — Polish
Workflow Explanation, Post-Execution Workflow Intelligence, performance optimization pass (RFC-003 §3), full test coverage (RFC-003 §4), visual polish pass against RFC-000 §4 tokens.

## After Sprint 5

Freeze this RFC set as v1.0. Do not keep expanding these six documents. Backlog items — Capability Blocks, Workflow Packages (RFC-001 §12), full Workspace Architecture (RFC-001 §9), Permissions (RFC-001 §10), AI Memory (RFC-001 §11), Agent Framework, event sourcing — get proposed as new RFCs (RFC-006, RFC-007, ...) once there's a concrete reason to build them, not by editing RFC-000 through RFC-005.

---

## Appendix: Known Bugs — fold in during Sprint 1

You'll be building the Node Registry, Mutation Service, and DSL versioning in Sprint 1 anyway — fix these as part of that work, not as a separate detour.

1. **Condition key bug** — the LLM sometimes generates `output.count` in a DSL condition when it should reference `output.emails`. Add schema-aware validation when generating/patching conditions, checking keys against the actual upstream node's output schema via the Node Registry validator (RFC-001 §3) and WorkflowContext (RFC-001 §5) — not guessing.
2. **Hardcoded Slack channel** — `all-xyz` is a placeholder that shipped as a regression. Slack action nodes must resolve the channel from a real config/credential value, filtered to `is_member: true`.
3. **Dual routing sources** — node-level `on_success`/`on_failure` fields AND a top-level `edges` array both encode routing, with nothing keeping them in sync. `edges` is canonical (RFC-001 §1); derive per-node fields from it at read-time or deprecate them entirely, and add a validator/migration (tied to DSL versioning, RFC-002 §4) so they can't drift again.

Each fix needs a regression test per RFC-003 §4.
