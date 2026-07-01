# RFC-004: Product Vision
**Depends on:** none (read alongside RFC-000 §4 for visual standards)
**Status:** Frozen v1.0

## 1. Product Philosophy (north star — not a literal checklist)

AutoFlow AI is not another n8n/Zapier/Make/Relay clone. AI is the **primary** way users build workflows; the visual canvas is a **secondary** surface for inspecting, editing, and debugging what AI built.

Users think in goals ("automate invoice approval"), not in nodes. AI decides which nodes are needed. Never expose raw technical complexity (node types, API field names) unless the user explicitly drills in.

Progressive disclosure by user sophistication:
- **Beginner** → sees AI chat only
- **Intermediate** → sees the visual graph, can drag/rewire
- **Advanced** → can inspect the compiled DSL
- **Expert** → can hand-edit node parameters directly

## 2. Target UX Pipeline

```
User prompt → AI Planner → clarifying follow-up questions (if needed)
  → DSL generation (via WorkflowMutationService) → compile (RFC-002 §1) → graph render → canvas
  → user edits visually / via AI (both via WorkflowMutationService) → execute (RFC-002 §1)
```

The AI Planner should always be the first surface a new user sees, not the canvas.

## 3. Visual Direction

Match the existing dark theme and right-panel chrome already in the AutoFlow AI builder (dark canvas, blue/teal node accents, AI Planner panel styling). Panels and menus appear only when triggered — nothing permanent that isn't already there. For concrete, checkable standards (animation timing, spacing, radius, accessibility), see RFC-000 §4 — that section is the implementable version of "polish."
