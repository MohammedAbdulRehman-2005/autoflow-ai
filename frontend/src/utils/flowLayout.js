/**
 * AutoFlow AI — DSL ↔ React Flow Adapter
 *
 * Converts a backend WorkflowDSL JSON into React Flow nodes + edges.
 * Uses dagre for automatic hierarchical layout.
 * Preserves manual positions that the user has dragged (stored in dsl.nodes[].position).
 */

import dagre from 'dagre';

const NODE_WIDTH = 300;
const NODE_HEIGHT = 90;

// Map node type → display color family
export const NODE_COLOR_MAP = {
  trigger:     { accent: '#3b82f6', bg: 'from-blue-500/10 to-blue-500/5',    border: 'border-blue-500/30' },
  action:      { accent: '#06b6d4', bg: 'from-cyan-500/10 to-cyan-500/5',     border: 'border-cyan-500/30' },
  ai_agent:    { accent: '#a855f7', bg: 'from-purple-500/10 to-purple-500/5', border: 'border-purple-500/30' },
  condition:   { accent: '#f59e0b', bg: 'from-amber-500/10 to-amber-500/5',   border: 'border-amber-500/30' },
  delay:       { accent: '#64748b', bg: 'from-slate-500/10 to-slate-500/5',   border: 'border-slate-500/30' },
  loop:        { accent: '#10b981', bg: 'from-emerald-500/10 to-emerald-500/5', border: 'border-emerald-500/30' },
  transformer: { accent: '#f97316', bg: 'from-orange-500/10 to-orange-500/5', border: 'border-orange-500/30' },
};

/**
 * Run dagre layout over the set of nodes and edges.
 * Returns nodes enriched with { position: { x, y } }.
 * Nodes that already have a saved position (from previous drag) are kept.
 */
function applyDagreLayout(rfNodes, rfEdges) {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 80, marginx: 40, marginy: 40 });

  rfNodes.forEach((n) => {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });
  rfEdges.forEach((e) => {
    g.setEdge(e.source, e.target);
  });

  dagre.layout(g);

  return rfNodes.map((n) => {
    // Preserve manually dragged positions
    if (n.data?.manualPosition) return n;

    const { x, y } = g.node(n.id);
    return {
      ...n,
      position: { x: x - NODE_WIDTH / 2, y: y - NODE_HEIGHT / 2 },
    };
  });
}

/**
 * Convert a WorkflowDSL JSON object into React Flow nodes + edges.
 *
 * @param {object} dsl          — WorkflowDSL from the backend
 * @param {object} savedPositions — Map of { nodeId: {x, y} } from previous drag events
 */
export function dslToFlow(dsl, savedPositions = {}) {
  if (!dsl?.nodes) return { nodes: [], edges: [] };

  // ── Build RF nodes ────────────────────────────────────────────────────────
  const rfNodes = dsl.nodes.map((n) => {
    const colors = NODE_COLOR_MAP[n.type] || NODE_COLOR_MAP.action;
    const savedPos = savedPositions[n.id];

    return {
      id: n.id,
      type: 'workflowNode',          // our custom node component
      position: savedPos || { x: 0, y: 0 },
      data: {
        ...n,
        colors,
        manualPosition: !!savedPos,  // flag to skip dagre for this node
      },
    };
  });

  // ── Build RF edges ────────────────────────────────────────────────────────
  const rfEdges = dsl.edges.map((e, i) => ({
    id: `edge-${e.source_id}-${e.target_id}-${i}`,
    source: e.source_id,
    target: e.target_id,
    label: e.label || undefined,
    type: 'smoothstep',
    animated: true,
    style: { stroke: '#475569', strokeWidth: 2 },
    labelStyle: { fill: '#94a3b8', fontSize: 10, fontWeight: 700 },
    labelBgStyle: { fill: '#0f172a', fillOpacity: 0.8 },
    labelBgPadding: [4, 6],
    labelBgBorderRadius: 4,
  }));

  // ── Auto-layout nodes that don't have saved positions ────────────────────
  const laidOut = applyDagreLayout(rfNodes, rfEdges);

  return { nodes: laidOut, edges: rfEdges };
}
