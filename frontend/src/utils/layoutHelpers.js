/**
 * AutoFlow AI X — Layout Helpers  (Sprint 3)
 * ============================================
 * Centralises all canvas layout calculations so hardcoded pixel offsets
 * never appear in component code.
 *
 * RFC-000 §3: "Replace hardcoded layout offsets with a layout helper/service."
 *
 * @module layoutHelpers
 */

// ── Grid constants ─────────────────────────────────────────────────────────
/** Width of a WorkflowNode card in pixels (must match CSS). */
export const NODE_WIDTH_PX  = 300;
/** Height of a WorkflowNode card in pixels (must match CSS). */
export const NODE_HEIGHT_PX = 90;
/** Vertical gap between two sequentially connected nodes. */
export const VERTICAL_SPACING_PX = 180;
/** Horizontal gap between parallel branches. */
export const HORIZONTAL_SPACING_PX = 360;
/** Canvas starting X for the first node (when the canvas is empty). */
export const CANVAS_ORIGIN_X = 400;
/** Canvas starting Y for the first node (when the canvas is empty). */
export const CANVAS_ORIGIN_Y = 100;


// ── Single-node placement ──────────────────────────────────────────────────

/**
 * Calculate the insertion position for a new node placed directly below
 * a reference node.
 *
 * @param {{ x: number, y: number }} referencePosition
 * @param {number} [spacing] — override VERTICAL_SPACING_PX
 * @returns {{ x: number, y: number }}
 */
export function insertionPositionBelow(
  referencePosition,
  spacing = VERTICAL_SPACING_PX,
) {
  return {
    x: referencePosition.x,
    y: referencePosition.y + spacing,
  };
}


/**
 * Return the position of the bottom-most node currently on the canvas,
 * i.e. the node with the greatest Y coordinate.
 *
 * Falls back to CANVAS_ORIGIN when the canvas is empty.
 *
 * @param {import('@xyflow/react').Node[]} rfNodes
 * @returns {{ x: number, y: number }}
 */
export function getLastNodePosition(rfNodes) {
  if (!rfNodes?.length) {
    return { x: CANVAS_ORIGIN_X, y: CANVAS_ORIGIN_Y };
  }
  return rfNodes.reduce(
    (lowest, n) =>
      n.position && n.position.y > lowest.y ? n.position : lowest,
    rfNodes[0].position ?? { x: CANVAS_ORIGIN_X, y: CANVAS_ORIGIN_Y },
  );
}


/**
 * Return the canvas position of a specific node by its ID.
 * Falls back to the last-node position when the ID is not found.
 *
 * @param {import('@xyflow/react').Node[]} rfNodes
 * @param {string} nodeId
 * @returns {{ x: number, y: number }}
 */
export function getNodePosition(rfNodes, nodeId) {
  const found = rfNodes?.find((n) => n.id === nodeId);
  return found?.position ?? getLastNodePosition(rfNodes);
}


// ── Multi-node placement ───────────────────────────────────────────────────

/**
 * Spread `count` new nodes vertically below a reference position.
 * Nodes are placed in a straight vertical column.
 *
 * @param {{ x: number, y: number }} referencePosition
 * @param {number} count — number of new nodes
 * @param {number} [spacing] — override VERTICAL_SPACING_PX
 * @returns {{ x: number, y: number }[]}
 */
export function spreadNodesBelow(
  referencePosition,
  count,
  spacing = VERTICAL_SPACING_PX,
) {
  return Array.from({ length: count }, (_, i) => ({
    x: referencePosition.x,
    y: referencePosition.y + spacing * (i + 1),
  }));
}


/**
 * Build a position map `{ nodeId: { x, y } }` for a list of new nodes,
 * starting below `anchorPosition`.
 *
 * @param {{ x: number, y: number }} anchorPosition — position of the insert-after node
 * @param {string[]} newNodeIds — ordered list of new node IDs
 * @param {number} [spacing]
 * @returns {Record<string, { x: number, y: number }>}
 */
export function buildInsertionPositions(anchorPosition, newNodeIds, spacing = VERTICAL_SPACING_PX) {
  const positions = {};
  newNodeIds.forEach((id, idx) => {
    positions[id] = {
      x: anchorPosition.x,
      y: anchorPosition.y + spacing * (idx + 1),
    };
  });
  return positions;
}
