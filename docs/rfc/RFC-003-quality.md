# RFC-003: Quality Bar
**Depends on:** RFC-000
**Status:** Frozen v1.0

## 1. Data Integrity Rule

Never mock responses. Never hardcode sample outputs. Never fake integrations. Every execution calls the actual backend. If a backend/integration is unavailable, surface the real error via the Error Boundaries in RFC-002 §3 — don't paper over it with a fake success state.

## 2. AI Confidence & Clarification Protocol

Every AI decision (Planner, Editor, Recommendation) returns:

```
{ confidence, missing_information, assumptions }
```

Only auto-execute a change if confidence is above threshold. Below threshold, ask the user instead of guessing — e.g. if the user says "notify my boss," ask which Slack channel rather than defaulting to one.

## 3. Performance Goals

- Canvas interactions stay smooth with hundreds of nodes.
- Incremental edits (single-node patches) never trigger full graph recomputation — only the affected node and its direct dependents re-render.
- The Node Inspector modal opens without a perceptible delay.
- AI patch application re-renders only the diff, not the whole canvas.

## 4. Testing Expectations

Every sprint in RFC-005 requires, at minimum:

- Unit tests for the logic it adds (registry entries, validators, executors).
- Integration tests covering the path through `WorkflowMutationService`.
- Mutation tests — confirm a patch produces the expected before/after DSL state.
- Regression tests for the three known bugs (RFC-005 Appendix).
- No happy-path-only, fully mocked tests for anything that calls a real integration (Gmail/Slack/Groq/Sheets/Notion/HubSpot) — cover the real-error path too, per §1.
