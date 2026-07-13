# AutoFlow AI — Sprint Prompts

Send these to your coding assistant **one at a time, in order**. Don't paste all six at once — that recreates the "one giant document" problem the RFC split was meant to solve. Commit the `rfc/` folder to the repo first (e.g. under `docs/rfc/`) so each prompt can point at it instead of re-explaining the architecture every time.

Wait for a sprint to actually pass its Definition of Done before sending the next one.

---

## Sprint 0 — Foundation Design

> Read `docs/rfc/RFC-000-engineering-rules.md`, `docs/rfc/RFC-001-editing-architecture.md`, and `docs/rfc/RFC-002-runtime-architecture.md` before doing anything else.
>
> Treat everything tagged **BUILD NOW** in RFC-001 and RFC-002 as in scope for this rebuild. Ignore everything tagged **DESIGN SURFACE ONLY** — don't build it, don't flag it as missing, it's intentionally deferred.
>
> This sprint is design only, no implementation code. Do the following:
> 1. Inspect the repository: frontend framework, canvas library, current DSL schema, existing services/hooks/state management.
> 2. Confirm whether a per-node-type parameter schema registry already exists.
> 3. Confirm whether a single-node execute endpoint already exists under a different path.
> 4. Confirm how credentials are currently stored/accessed by nodes.
> 5. Write an architecture analysis: what exists today, what's reusable, what's missing relative to RFC-001 §1–8 and RFC-002.
> 6. Write an implementation plan for Sprint 1 only (WorkflowMutationService, NodeRegistry, CredentialManager, WorkflowContext skeleton, DSL version fields, the three known bugs in `docs/rfc/RFC-005-roadmap.md` Appendix).
> 7. Stop. Share the analysis and plan. Do not write implementation code — wait for my approval.
>
> Definition of done for this sprint: a plan I've approved. Nothing else.

---

## Sprint 1 — Foundation Build

> Reference `docs/rfc/RFC-000-engineering-rules.md`, `docs/rfc/RFC-001-editing-architecture.md` (§1–8, BUILD NOW items only), `docs/rfc/RFC-002-runtime-architecture.md` §4 (DSL Versioning), and the Appendix in `docs/rfc/RFC-005-roadmap.md`.
>
> Build, in this order:
> 1. `WorkflowMutationService` with mutation history and undo/redo (RFC-001 §1).
> 2. `NodeRegistry` covering the six node types in RFC-001 §3, as a plugin structure.
> 3. `CredentialManager` (RFC-001 §8) — nodes reference `credential_id`, never raw secrets.
> 4. `WorkflowContext` skeleton (RFC-001 §5).
> 5. DSL version fields (RFC-002 §4).
> 6. Fix the three known bugs in the RFC-005 Appendix, as part of this same pass.
>
> Do not build the Node Inspector UI — that's Sprint 2. Do not touch anything tagged DESIGN SURFACE ONLY in RFC-001.
>
> Definition of done: RFC-000 §5 checklist, plus a passing regression test for each of the three bugs.

---

## Sprint 2 — Node Inspector (first user-visible feature)

> Reference `docs/rfc/RFC-001-editing-architecture.md` §3 and §5, `docs/rfc/RFC-002-runtime-architecture.md` §1 and §3, `docs/rfc/RFC-003-quality.md` §1.
>
> Build the Node Inspector Modal:
> - Trigger: click any node on canvas.
> - Header: node icon/name (from NodeRegistry), `Docs ↗` link, close.
> - Tabs: Parameters | Settings.
> - INPUT column: `previous_outputs` from WorkflowContext, Schema/Table/JSON toggle.
> - PARAMETERS tab: form driven by the node's registry parameter schema.
> - SETTINGS tab: Always Output Data, Execute Once, Retry On Fail, On Error (options informed by RFC-002 §3 Error Boundaries), Notes, Display Note in Flow.
> - OUTPUT column: empty state + Execute Step button.
>
> Execute Step: `POST /api/workflows/{workflow_id}/nodes/{node_id}/execute` — runs the single node through the real runtime pipeline (RFC-002 §1) in isolation, against real credentials via CredentialManager. No mocked data anywhere (RFC-003 §1).
>
> Acceptance: every node type in the registry opens this modal; Execute Step returns real data or a real error for at least Gmail, Slack, and the Groq AI agent node.
>
> Definition of done: RFC-000 §5 checklist.

---

## Sprint 3 — AI-Native Editing (Add Step)

> Reference `docs/rfc/RFC-001-editing-architecture.md` §1 and §4.
>
> Replace the raw "Add Node" picker's primary role with "Add with AI": free-text input on `+` click (node, edge, or empty canvas).
> - Parse intent → check the Capability Registry (RFC-001 §4) first for a known multi-node pattern before falling back to individual nodes.
> - Generate a DSL patch and apply it exclusively through `WorkflowMutationService` — never regenerate the whole workflow.
> - Preserve existing node positions/layout; insert and reconnect edges automatically.
> - Keep a secondary, visually de-emphasized "Browse steps" list grouped by app as the manual fallback — it must not compete visually with the AI input.
> - Every AI patch produces a diff before it's applied (RFC-000 §3).
>
> Definition of done: RFC-000 §5 checklist.

---

## Sprint 4 — Productivity

> Reference `docs/rfc/RFC-001-editing-architecture.md` §2, §3, §4.
>
> Build, all routed through `WorkflowMutationService` and the AI Service Boundaries in RFC-001 §2:
> 1. **Command Palette** — `Ctrl+K` or double-click empty canvas; search by capability ("invoice", "approval", "CRM"), not raw node name; known Capability Registry patterns surface as one grouped result.
> 2. **AI Recommendations** — `AI Recommended` section in Add Step results, sourced from each node type's `recommendations` field in the Node Registry.
> 3. **Improve with AI** — action in the Node Inspector; user describes a change ("reduce API cost", "add retry"), Editor AI patches that node's config via the mutation service.
> 4. **Edge AI menu** — clicking an edge opens Insert Step / Add Retry / Add Delay / Add Approval / Optimize Flow, same natural-language pattern as Add Step.
>
> Definition of done: RFC-000 §5 checklist.

---

## Sprint 5 — Polish

> Reference `docs/rfc/RFC-002-runtime-architecture.md` §1, `docs/rfc/RFC-003-quality.md` §3–4, `docs/rfc/RFC-000-engineering-rules.md` §4.
>
> 1. **Workflow Explanation** — after the AI Planner builds/materially edits a workflow, show a 1–2 sentence plain-English summary (Inspector AI) above the canvas or in the Planner panel.
> 2. **Workflow Intelligence** — after a run completes, Recommendation AI surfaces suggestions (parallelize branches, remove duplicate calls, reduce tokens, cache repeats, retry failures, batch, cheaper model) as suggestions only — applied via Editor AI / the mutation service if accepted.
> 3. **Performance pass** against RFC-003 §3 — verify hundreds of nodes stay smooth, incremental edits don't trigger full recompute, AI patches re-render only the diff.
> 4. **Test coverage pass** against RFC-003 §4 for everything built in Sprints 1–4.
> 5. **Visual polish pass** against RFC-000 §4 — animation timing, spacing, radius, keyboard accessibility, no layout shift.
>
> Definition of done: RFC-000 §5 checklist, for the whole v1 scope, not just this sprint's additions.

---

## After Sprint 5

Don't send a "Sprint 6" prompt against these RFCs. If a real architectural need comes up (Workflow Packages, multi-workspace, permissions, AI memory, etc.), write a new RFC-006+ proposal first, get it reviewed, then write its own sprint prompt the same way these were written.
