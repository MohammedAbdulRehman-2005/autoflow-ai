/**
 * AutoFlow AI — WorkflowNode Custom React Flow Node
 *
 * Renders as a polished card with:
 *  - Color-coded accent bar by node type
 *  - Service + operation badge
 *  - Node ID displayed in monospace
 *  - Animated hover glow
 */

import { Handle, Position } from '@xyflow/react';
import { Zap, Brain, Server, GitBranch, Clock, RefreshCw, Layers, AlertCircle } from 'lucide-react';

const TYPE_ICONS = {
  trigger:     Zap,
  ai_agent:    Brain,
  action:      Server,
  condition:   GitBranch,
  delay:       Clock,
  loop:        RefreshCw,
  transformer: Layers,
};

export default function WorkflowNode({ data, selected }) {
  const Icon = TYPE_ICONS[data.type] || Server;
  const colors = data.colors || { accent: '#06b6d4', bg: 'from-cyan-500/10 to-cyan-500/5', border: 'border-cyan-500/30' };

  return (
    <div
      className={`
        relative w-[300px] rounded-2xl border bg-gradient-to-br ${colors.bg} ${colors.border}
        backdrop-blur-md shadow-lg transition-all duration-200
        ${selected ? 'ring-2 ring-offset-2 ring-offset-slate-950' : ''}
      `}
      style={{
        borderColor: selected ? colors.accent : undefined,
        boxShadow: selected ? `0 0 20px ${colors.accent}33` : undefined,
      }}
    >
      {/* Top handle (except for trigger) */}
      {data.type !== 'trigger' && (
        <Handle
          type="target"
          position={Position.Top}
          className="!w-3 !h-3 !rounded-full !border-2 !bg-slate-950"
          style={{ borderColor: colors.accent }}
        />
      )}

      <div className="p-4 flex items-center gap-3">
        {/* Icon */}
        <div
          className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: `${colors.accent}20`, border: `1px solid ${colors.accent}40` }}
        >
          <Icon size={18} style={{ color: colors.accent }} />
        </div>

        {/* Labels */}
        <div className="min-w-0 flex-1">
          <div
            className="text-[9px] font-bold tracking-widest uppercase font-mono mb-0.5"
            style={{ color: colors.accent }}
          >
            {data.type}
          </div>
          <div className="text-sm font-bold text-white truncate font-display">
            {data.label || data.id}
          </div>
          <div className="text-[10px] text-slate-400 font-mono truncate mt-0.5">
            {data.service}.{data.operation}
          </div>
        </div>
      </div>

      {/* Node ID pill */}
      <div className="px-4 pb-3">
        <span className="text-[9px] font-mono text-slate-500 bg-white/5 border border-white/8 rounded px-2 py-0.5">
          #{data.id}
        </span>
        {data.is_disabled && (
          <span className="ml-2 text-[9px] font-mono text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded px-2 py-0.5">
            disabled
          </span>
        )}
      </div>

      {/* Bottom handle (except for terminal actions with no on_success) */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !rounded-full !border-2 !bg-slate-950"
        style={{ borderColor: colors.accent }}
      />
    </div>
  );
}
