# RFC-000: Engineering Rules
**Status:** Frozen v1.0
**Applies to:** every RFC in this set, every sprint in RFC-005.

Read this first. Every other RFC and every sprint prompt assumes these rules without repeating them.

---

## 1. Development Process

Before writing implementation code for any sprint:

1. Inspect the repository (frontend framework, canvas library, current DSL schema, existing services/hooks/state management).
2. Confirm whether the thing you're about to build already exists under a different name/path.
3. Produce a short architecture analysis: what exists today, what's reusable, what's missing relative to the relevant RFC(s).
4. Identify risks — places likely to cause duplicated state, duplicated components, or multiple sources of truth.
5. Produce an implementation plan scoped to *this sprint only*.
6. **Wait for approval** on that plan before writing implementation code.

## 2. Repository Rules

Unless a sprint explicitly calls for it:

- Do NOT rewrite existing authentication.
- Do NOT rewrite the execution engine wholesale (bug fixes in RFC-005 Appendix are the only sanctioned exception, and only the specific lines involved).
- Do NOT replace React Flow / the existing canvas library.
- Do NOT migrate the styling system.
- Do NOT change routing.
- Do NOT replace the state management approach already in use.
- Only modify what the current sprint requires. Prefer extending existing files over creating parallel ones.

## 3. Engineering Principles

- Do not duplicate state. Never create two sources of truth for the same data.
- Prefer extending existing architecture over introducing a parallel one.
- Reuse existing APIs whenever possible; confirm an endpoint doesn't already exist before adding a new one.
- Preserve backward compatibility. Preserve node IDs. Do not break existing workflows.
- Prefer composition over rewriting.
- Avoid introducing unnecessary dependencies.
- Every new feature must be modular and independently testable.
- The UI must remain responsive while AI requests are in flight.
- Never regenerate an entire workflow DSL when only one node changed — patch incrementally.
- Every AI modification should produce a diff before it is applied.
- Node metadata comes from a registry, never hardcoded `if node.type == "gmail"` branching.
- If a sprint prompt references something marked **DESIGN SURFACE ONLY** in RFC-001/002, do not build it. Its shape exists so later work doesn't conflict with it — nothing more.

## 4. Visual & Interaction Standard

Replaces vague direction like "Apple-level polish" with things that can actually be implemented and checked:

- Animations: 150–250ms; ease-out on entrances, ease-in on exits.
- Corner radius: 12px for panels/cards/modals, 8px for buttons/inputs.
- Spacing: 8-point grid (8 / 16 / 24 / 32...).
- Color: use the existing dark-theme design tokens — no new hardcoded hex values.
- No layout shift on load or while AI responses stream in.
- Full keyboard accessibility: tab order, visible focus states, Esc closes modals.
- Responsive down to the breakpoints already supported in the repo — confirm them, don't invent new ones.

## 5. Definition of Done

A sprint is not complete until every box below is true. Use this literally as a checklist at the end of each sprint prompt.

- [ ] Feature works end-to-end against real backends — no mocks (RFC-003 §1).
- [ ] Unit, integration, and mutation tests pass (RFC-003 §4).
- [ ] No regressions — existing workflows still load and run.
- [ ] Docs updated (this RFC set, plus inline code docs where relevant).
- [ ] Existing workflows migrate automatically if the DSL shape changed (RFC-002 §DSL Versioning).
- [ ] No console errors.
- [ ] Accessibility checks pass (§4 above).
- [ ] Types pass, lint passes.
