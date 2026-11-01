# AutoFlow AI X — Frontend Design System

This design system establishes the foundational standards for AutoFlow AI X. It is built on Tailwind CSS v4, `@xyflow/react`, and modern developer SaaS interaction paradigms.

---

## 1. Typography & Hierarchy

The platform uses three dedicated font families configured in `index.css`:

| Category | Font Family | Usage |
|---|---|---|
| **Body & UI** | `Inter` (`--font-sans`) | Body copy, buttons, tooltips, forms, documentation. |
| **Headings & Display** | `Space Grotesk` (`--font-display`) | Page headers, panel titles, metric numbers, brand logotype. |
| **Data & Identifiers** | `JetBrains Mono` (`--font-mono`) | Run IDs, node tags, JSON payloads, durations, timestamps, badges. |

### Type Scale
- `text-2xl` / `text-3xl` (`font-bold`, `font-display`): Primary KPI metrics and page headers.
- `text-lg` / `text-xl` (`font-bold`, `font-display`): Card and modal titles.
- `text-sm` (`font-medium` / `font-semibold`): Section labels, standard buttons, primary card names.
- `text-xs` (`font-sans` / `font-mono`): Secondary descriptions, input forms, table cells.
- `text-[11px]` / `text-[10px]` (`font-mono`): Metadata chips, badges, timestamps, byte counts.

---

## 2. Color Palette & Semantics

The palette uses a deep obsidian dark background with calibrated glass borders and semantic accents.

### Core Foundation
- **Background Base:** `#020617` (Deep Obsidian / Slate 950)
- **Glass Container:** `rgba(15, 23, 42, 0.6)` with `backdrop-filter: blur(20px)` and `border: 1px solid rgba(255, 255, 255, 0.1)`
- **Border Default:** `border-white/10` (interactive: `hover:border-white/20`, focus: `focus:border-cyan-400/50`)
- **Text Primary:** `#f8fafc` (`text-slate-100` / `text-white`)
- **Text Secondary:** `#94a3b8` (`text-slate-400`)
- **Text Muted:** `#64748b` (`text-slate-500`)

### Semantic Accents & Statuses

| State / Type | Tailwind Color | Hex Accent | Usage |
|---|---|---|---|
| **Success / Succeeded** | `emerald-400` / `emerald-500` | `#10b981` | Completed runs, passed checks, operational status. |
| **Running / In Progress** | `blue-400` / `blue-500` | `#3b82f6` | Active executions (animated pulse), trigger nodes. |
| **Failed / Error** | `rose-400` / `rose-500` | `#f43f5e` | Execution errors, failed steps, critical triage alerts. |
| **Pending / Triage** | `amber-400` / `amber-500` | `#f59e0b` | Condition nodes, pending queue items, transient warnings. |
| **Awaiting Approval** | `purple-400` / `purple-500` | `#c084fc` | Human-in-the-loop governance pauses, approval queue. |
| **Primary Brand / AI** | `cyan-400` / `cyan-500` | `#06b6d4` | Primary buttons, AI planner highlights, action handles. |

---

## 3. Spacing, Borders, and Radii

- **Container Radii:**
  - Cards & Modals: `rounded-2xl` (`16px`)
  - Buttons & Inputs: `rounded-xl` (`12px`)
  - Badges & Chips: `rounded-full` (`9999px`) or `rounded-md` (`6px`)
- **Layout Spacing:**
  - Page margins: `px-6 md:px-10`, `pt-24 pb-16`
  - Grid gutters: `gap-4` for metrics, `gap-6` for split-screen layouts, `gap-8` for sections
  - Card internal padding: `p-4` or `p-5`

---

## 4. Component States

Every interactive element implements 5 mandatory states:

1. **Loading State:**
   - Buttons: Inner spinning indicator (`RotateCw`), disabled click events, dimmed text.
   - Data grids: Shimmer pulse skeletons (`LoadingSkeleton`, `MetricSkeleton`).
2. **Empty State:**
   - Visual icon container (`Inbox` / `Sparkles`), clear title, descriptive helper text, and a primary action trigger (`EmptyState.jsx`).
3. **Error State:**
   - Monospace error box with border (`border-rose-500/30`), stack trace viewer, and 1-click clipboard copy.
4. **Disabled State:**
   - `opacity-50`, `cursor-not-allowed`, `pointer-events-none`, preserving accessible title attributes.
5. **Success / Active State:**
   - High-contrast highlight rings (`focus:ring-2 focus:ring-cyan-400`), subtle glow shadows, and feedback toasts (`useToast`).

---

## 5. Accessibility & Keyboard Controls

- **Focus Rings:** All buttons, inputs, and interactive cards implement high-contrast focus rings (`focus:ring-2 focus:ring-offset-2 focus:ring-offset-slate-950`).
- **Keyboard Traps & Dismissals:**
  - `Escape` key closes all slide-over Drawers and Modals.
  - Form submissions bound to `Enter` and `Cmd/Ctrl + Enter`.
- **Labels & Contrast:** All icon-only buttons include `aria-label` or `title` attributes. Color contrast exceeds WCAG 2.1 AA standards across dark backgrounds.
