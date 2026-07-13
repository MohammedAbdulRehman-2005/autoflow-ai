/**
 * AutoFlow AI X — InspectorActionBar  (Sprint 3.5 — Sprint 4 AI placeholder)
 * ===========================================================================
 * PLACEHOLDER: This component reserves space for Sprint 4 AI-driven node
 * improvement actions ("Improve with AI", "Suggest alternatives", etc.).
 *
 * Currently renders nothing (null). Do NOT add functionality here until
 * Sprint 4 is scoped and approved.
 *
 * The NodeInspector ACTION_SLOT should call this component so the reserved
 * slot is structurally present in the tree.
 */
import { memo } from 'react';

/**
 * InspectorActionBar
 * @param {Object} props
 * @param {Object} props.node    - DSL node (for future AI context)
 * @param {Object} props.plugin  - NodePlugin metadata (for future AI context)
 */
function InspectorActionBar({ node, plugin }) {
  // Sprint 4: render AI improvement actions here.
  // Do not add any logic until Sprint 4 is approved.
  // eslint-disable-next-line no-unused-vars
  void node; void plugin;
  return null;
}

export { InspectorActionBar };
export default memo(InspectorActionBar);
