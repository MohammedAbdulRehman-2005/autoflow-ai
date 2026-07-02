/**
 * AutoFlow AI X — Node Inspector Modal (Sprint 2)
 * ================================================
 * Triggered by clicking any node on the canvas.
 *
 * Architecture:
 *  - Plugin metadata fetched from NodeRegistry via /api/v1/workflows/node-types (session-cached).
 *  - Parameter form is fully driven by plugin.parameter_schema — no hardcoded node-type branching.
 *  - Three-tier INPUT lookup:
 *      (1) Session cache: most recent Execute Step result for this node (in-memory, cleared on modal close).
 *      (2) Last full run: GET /workflows/:id/runs?limit=1 → step_logs (fetched once on open).
 *      (3) Schema reference: output_schema as empty table if no run exists.
 *  - Parameters auto-apply on blur (simple fields) or on explicit Apply click (large editors).
 *  - Execute Step reads latest locally-patched params at click time, never an open-time snapshot.
 *  - Double-submit is blocked while a request is in-flight.
 *  - Sprint 4 "Improve with AI" entry point is structurally reserved in the action area (see ACTION_SLOT).
 *
 * Accessibility:
 *  - Focus trap inside modal; Esc closes.
 *  - All inputs have labels and unique IDs.
 *  - Error states use role="alert".
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, ExternalLink, Play, ChevronRight, AlertCircle,
  CheckCircle2, Loader2, Table, Code, List, Info,
  RefreshCw, RotateCcw, Settings, Sliders, StickyNote,
  Eye, EyeOff, Zap
} from 'lucide-react';
import { workflowApi } from '../services/workflowApi';
import { mutationService } from '../services/mutationService';

// ─── Icon map for node types (avoids hardcoded branching) ────────────────────
const ICON_MAP = {
  Mail: '✉',
  Inbox: '📥',
  MessageSquare: '💬',
  Sparkles: '✨',
  GitBranch: '⑂',
  Clock: '⏰',
  Variable: '𝑥',
  Brain: '🧠',
  Server: '⚙',
  Zap: '⚡',
  RefreshCw: '🔁',
  Layers: '⋮',
};

// ─── Large-editor widget types (require explicit Apply, not auto-apply on blur) ─
const LARGE_EDITOR_WIDGETS = new Set(['textarea', 'json', 'expression']);

// ─── Validate a value against a JSON Schema property def ─────────────────────
function validateField(value, schemaProp) {
  if (!schemaProp) return null;
  const { type, minimum, maximum, minLength, maxLength, pattern, enum: enumVals } = schemaProp;

  if (type === 'integer' || type === 'number') {
    const n = Number(value);
    if (isNaN(n)) return 'Must be a number.';
    if (minimum !== undefined && n < minimum) return `Minimum is ${minimum}.`;
    if (maximum !== undefined && n > maximum) return `Maximum is ${maximum}.`;
  }
  if (type === 'string') {
    if (minLength && String(value).length < minLength) return `Minimum length is ${minLength}.`;
    if (maxLength && String(value).length > maxLength) return `Maximum length is ${maxLength}.`;
    if (pattern && !new RegExp(pattern).test(String(value))) return 'Value does not match the required pattern.';
  }
  if (enumVals && !enumVals.includes(value)) return `Must be one of: ${enumVals.join(', ')}.`;
  return null;
}

// ─── Simple client-side schema validator ─────────────────────────────────────
function validateParams(params, schema) {
  const errors = {};
  if (!schema?.properties) return errors;
  for (const [key, prop] of Object.entries(schema.properties)) {
    const err = validateField(params[key], prop);
    if (err) errors[key] = err;
  }
  const required = schema.required || [];
  for (const key of required) {
    if (!params[key] && params[key] !== 0 && params[key] !== false) {
      errors[key] = errors[key] || 'This field is required.';
    }
  }
  return errors;
}

// ─── Output view toggle ───────────────────────────────────────────────────────
function OutputView({ data, schema }) {
  const [mode, setMode] = useState('table'); // 'table' | 'json' | 'schema'

  const entries = Object.entries(data || {});
  const schemaProps = schema?.properties || {};

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-1 mb-3">
        {[['table', Table, 'Table'], ['json', Code, 'JSON'], ['schema', List, 'Schema']].map(([m, Icon, label]) => (
          <button
            key={m}
            id={`output-view-${m}`}
            onClick={() => setMode(m)}
            className={`flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium transition-all ${
              mode === m
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'text-slate-400 hover:text-slate-300 border border-transparent'
            }`}
          >
            <Icon size={11} />
            {label}
          </button>
        ))}
      </div>

      {mode === 'table' && (
        <div className="flex-1 overflow-auto">
          {entries.length === 0 ? (
            <div className="text-slate-500 text-xs italic">No data</div>
          ) : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left text-slate-400 font-medium pb-2 pr-3">Key</th>
                  <th className="text-left text-slate-400 font-medium pb-2">Value</th>
                </tr>
              </thead>
              <tbody>
                {entries.map(([k, v]) => (
                  <tr key={k} className="border-b border-white/5">
                    <td className="py-1.5 pr-3 text-slate-300 font-mono">{k}</td>
                    <td className="py-1.5 text-slate-400 font-mono truncate max-w-[160px]" title={JSON.stringify(v)}>
                      {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {mode === 'json' && (
        <pre className="flex-1 overflow-auto text-xs text-slate-300 font-mono bg-white/5 rounded-xl p-3 border border-white/10">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}

      {mode === 'schema' && (
        <div className="flex-1 overflow-auto space-y-1">
          {Object.entries(schemaProps).map(([k, def]) => (
            <div key={k} className="flex items-start gap-2 py-1.5 border-b border-white/5">
              <span className="text-cyan-400 font-mono text-xs min-w-[80px]">{k}</span>
              <span className="text-slate-500 text-xs">{def.type || 'any'}</span>
              {def.description && <span className="text-slate-600 text-xs">{def.description}</span>}
            </div>
          ))}
          {Object.keys(schemaProps).length === 0 && (
            <div className="text-slate-500 text-xs italic">No schema defined for this node type.</div>
          )}
        </div>
      )}
    </div>
  );
}

// ─── Single parameter field ───────────────────────────────────────────────────
function ParamField({ fieldKey, schema, value, onChange, onBlur, onApply, isDirty, validationError, schemaRequired }) {
  const ui = schema.ui || {};
  const widget = ui.widget || (
    schema.type === 'boolean' ? 'toggle' :
    schema.enum ? 'select' :
    schema.type === 'integer' || schema.type === 'number' ? 'number' :
    'text'
  );
  const isLarge = LARGE_EDITOR_WIDGETS.has(widget);
  const fieldId = `param-${fieldKey}`;
  const isRequired = schemaRequired;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label
          htmlFor={fieldId}
          className="text-xs font-semibold text-slate-300 flex items-center gap-1"
        >
          {fieldKey}
          {isRequired && <span className="text-rose-400">*</span>}
        </label>
        {isLarge && isDirty && (
          <button
            id={`apply-${fieldKey}`}
            onClick={() => onApply(fieldKey)}
            className="text-[10px] px-2 py-0.5 rounded-md bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 transition-colors"
          >
            Apply
          </button>
        )}
        {isLarge && !isDirty && value && (
          <span className="text-[10px] text-slate-500">saved</span>
        )}
      </div>

      {widget === 'toggle' ? (
        <button
          id={fieldId}
          role="switch"
          aria-checked={!!value}
          onClick={() => { onChange(fieldKey, !value); if (!isLarge) onBlur(fieldKey, !value); }}
          className={`relative w-9 h-5 rounded-full transition-colors ${
            value ? 'bg-cyan-500' : 'bg-slate-700'
          }`}
        >
          <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${value ? 'translate-x-4' : ''}`} />
        </button>
      ) : widget === 'select' ? (
        <select
          id={fieldId}
          value={value ?? ''}
          onChange={e => onChange(fieldKey, e.target.value)}
          onBlur={e => onBlur(fieldKey, e.target.value)}
          className="w-full bg-slate-900/60 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20"
        >
          <option value="">Select...</option>
          {(schema.enum || []).map(opt => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      ) : widget === 'number' ? (
        <input
          id={fieldId}
          type="number"
          value={value ?? ''}
          min={schema.minimum}
          max={schema.maximum}
          onChange={e => onChange(fieldKey, e.target.value === '' ? '' : Number(e.target.value))}
          onBlur={e => onBlur(fieldKey, Number(e.target.value))}
          placeholder={ui.placeholder || ''}
          className="w-full bg-slate-900/60 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20"
        />
      ) : (widget === 'textarea' || widget === 'json' || widget === 'expression') ? (
        <textarea
          id={fieldId}
          rows={widget === 'json' ? 6 : 4}
          value={value ?? ''}
          onChange={e => onChange(fieldKey, e.target.value)}
          onBlur={e => { if (!isLarge) onBlur(fieldKey, e.target.value); }}
          placeholder={ui.placeholder || ''}
          spellCheck={false}
          className={`w-full bg-slate-900/60 border rounded-xl px-3 py-2 text-sm text-slate-200 font-mono resize-y focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 ${
            isDirty ? 'border-amber-500/40' : 'border-white/10'
          }`}
        />
      ) : (
        <input
          id={fieldId}
          type={ui.secret ? 'password' : 'text'}
          value={value ?? ''}
          onChange={e => onChange(fieldKey, e.target.value)}
          onBlur={e => onBlur(fieldKey, e.target.value)}
          placeholder={ui.placeholder || ''}
          className="w-full bg-slate-900/60 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20"
        />
      )}

      {ui.helpText && (
        <p className="text-[10px] text-slate-500 flex items-start gap-1">
          <Info size={9} className="mt-0.5 flex-shrink-0" />{ui.helpText}
        </p>
      )}
      {validationError && (
        <p className="text-[10px] text-rose-400 flex items-center gap-1" role="alert">
          <AlertCircle size={9} />{validationError}
        </p>
      )}
    </div>
  );
}

// ─── Settings Tab ─────────────────────────────────────────────────────────────
function SettingsTab({ node, onSettingChange }) {
  const ERROR_POLICY_OPTIONS = [
    { value: 'stop',     label: 'Stop',     desc: 'Halt the workflow immediately. on_failure is ignored.' },
    { value: 'continue', label: 'Continue', desc: 'Mark failed, route to on_failure if set.' },
    { value: 'retry',    label: 'Retry',    desc: 'Use retry_policy, then route to on_failure.' },
  ];

  return (
    <div className="space-y-5">
      {/* Execution behaviour */}
      <div className="space-y-3">
        <p className="text-[10px] font-bold tracking-widest uppercase text-slate-500">Execution</p>

        <label className="flex items-center justify-between cursor-pointer group">
          <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
            Always Output Data
            <span className="block text-[10px] text-slate-500 mt-0.5 font-normal">
              Pass output downstream even if this node failed. No-op in Execute Step.
            </span>
          </span>
          <button
            id="setting-always-output"
            role="switch"
            aria-checked={!!node.always_output_data}
            onClick={() => onSettingChange('always_output_data', !node.always_output_data)}
            className={`ml-4 flex-shrink-0 relative w-9 h-5 rounded-full transition-colors ${node.always_output_data ? 'bg-cyan-500' : 'bg-slate-700'}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${node.always_output_data ? 'translate-x-4' : ''}`} />
          </button>
        </label>

        <label className="flex items-center justify-between cursor-pointer group">
          <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
            Execute Once
            <span className="block text-[10px] text-slate-500 mt-0.5 font-normal">
              Skip if already ran in this run_id. No-op in Execute Step.
            </span>
          </span>
          <button
            id="setting-execute-once"
            role="switch"
            aria-checked={!!node.execute_once}
            onClick={() => onSettingChange('execute_once', !node.execute_once)}
            className={`ml-4 flex-shrink-0 relative w-9 h-5 rounded-full transition-colors ${node.execute_once ? 'bg-cyan-500' : 'bg-slate-700'}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${node.execute_once ? 'translate-x-4' : ''}`} />
          </button>
        </label>
      </div>

      {/* Error policy */}
      <div className="space-y-2">
        <p className="text-[10px] font-bold tracking-widest uppercase text-slate-500">On Error</p>
        <div className="space-y-1.5">
          {ERROR_POLICY_OPTIONS.map(opt => (
            <label key={opt.value} className="flex items-start gap-3 cursor-pointer p-2 rounded-xl hover:bg-white/5 transition-colors">
              <input
                id={`error-policy-${opt.value}`}
                type="radio"
                name="error_policy"
                value={opt.value}
                checked={node.error_policy === opt.value || (!node.error_policy && opt.value === 'stop')}
                onChange={() => onSettingChange('error_policy', opt.value)}
                className="mt-0.5 accent-cyan-500"
              />
              <div>
                <span className="text-sm text-slate-300 font-medium">{opt.label}</span>
                <p className="text-[10px] text-slate-500 mt-0.5">{opt.desc}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Retry */}
      <div className="space-y-2">
        <label className="flex items-center justify-between cursor-pointer group">
          <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
            Retry On Fail
            <span className="block text-[10px] text-slate-500 mt-0.5 font-normal">
              Uses error_policy=retry. Active only in full run context.
            </span>
          </span>
          <button
            id="setting-retry"
            role="switch"
            aria-checked={node.error_policy === 'retry'}
            onClick={() => onSettingChange('error_policy', node.error_policy === 'retry' ? 'stop' : 'retry')}
            className={`ml-4 flex-shrink-0 relative w-9 h-5 rounded-full transition-colors ${node.error_policy === 'retry' ? 'bg-cyan-500' : 'bg-slate-700'}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${node.error_policy === 'retry' ? 'translate-x-4' : ''}`} />
          </button>
        </label>
      </div>

      {/* Notes */}
      <div className="space-y-2">
        <p className="text-[10px] font-bold tracking-widest uppercase text-slate-500">Notes</p>
        <textarea
          id="setting-notes"
          rows={4}
          value={node.notes || ''}
          onChange={e => onSettingChange('notes', e.target.value)}
          placeholder="Add notes about this node..."
          className="w-full bg-slate-900/60 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-200 resize-y focus:outline-none focus:border-cyan-500/50"
        />

        <label className="flex items-center gap-2 cursor-pointer">
          <button
            id="setting-display-note"
            role="switch"
            aria-checked={!!node.display_note_in_flow}
            onClick={() => onSettingChange('display_note_in_flow', !node.display_note_in_flow)}
            className={`flex-shrink-0 relative w-9 h-5 rounded-full transition-colors ${node.display_note_in_flow ? 'bg-cyan-500' : 'bg-slate-700'}`}
          >
            <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${node.display_note_in_flow ? 'translate-x-4' : ''}`} />
          </button>
          <span className="text-xs text-slate-400">Display note in flow</span>
        </label>
      </div>
    </div>
  );
}

// ─── NodeInspector ────────────────────────────────────────────────────────────
/**
 * @param {object}   props
 * @param {object}   props.node          - WorkflowNodeDSL object (from plannedDsl.nodes)
 * @param {string}   props.workflowId    - Workflow UUID (for Execute Step and run lookup)
 * @param {object}   props.sessionCache  - { [nodeId]: ExecuteStepResult } — in-memory, never persisted
 * @param {Function} props.onParamChange - (nodeId, key, value) → mutationService.applyPatch()
 * @param {Function} props.onSettingChange - (nodeId, key, value) → mutationService.applyPatch()
 * @param {Function} props.onCacheUpdate - (nodeId, result) → update session cache in parent
 * @param {Function} props.onClose       - close the inspector
 */
export default function NodeInspector({
  node,
  workflowId,
  sessionCache = {},
  onParamChange,
  onSettingChange,
  onCacheUpdate,
  onClose,
}) {
  const [activeTab, setActiveTab] = useState('parameters');
  const [plugin, setPlugin] = useState(null);
  const [pluginLoading, setPluginLoading] = useState(true);

  // Local params state — starts from node.params, mutated by field changes
  // (auto-apply on blur or explicit Apply click writes back via onParamChange)
  const [localParams, setLocalParams] = useState({ ...node.params });
  const [dirtyFields, setDirtyFields] = useState(new Set());
  const [validationErrors, setValidationErrors] = useState({});

  // INPUT column state
  const [inputData, setInputData] = useState(null);    // { data: {}, source: 'cache'|'run'|'schema' }
  const [inputLoading, setInputLoading] = useState(true);

  // OUTPUT column state
  const [executing, setExecuting] = useState(false);
  const [executeResult, setExecuteResult] = useState(null);
  const executeInFlight = useRef(false);

  // Focus trap
  const modalRef = useRef(null);

  // ── Load plugin metadata (session-cached in workflowApi) ─────────────────
  useEffect(() => {
    let cancelled = false;
    setPluginLoading(true);
    workflowApi.getNodeTypes()
      .then(res => {
        if (cancelled) return;
        const found = res.plugins?.find(
          p => p.service === node.service && p.operation === node.operation
        );
        setPlugin(found || null);
      })
      .catch(() => { if (!cancelled) setPlugin(null); })
      .finally(() => { if (!cancelled) setPluginLoading(false); });
    return () => { cancelled = true; };
  }, [node.service, node.operation]);

  // ── Three-tier INPUT lookup ───────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    async function loadInput() {
      setInputLoading(true);

      // Tier 1: session cache from Execute Step
      if (sessionCache[node.id]) {
        if (!cancelled) {
          setInputData({ data: sessionCache[node.id].output || {}, source: 'cache' });
          setInputLoading(false);
        }
        return;
      }

      // Tier 2: last full workflow run step_logs
      try {
        const runList = await workflowApi.listRuns(workflowId, { limit: 1 });
        if (!cancelled && runList?.runs?.length > 0) {
          const lastRun = runList.runs[0];
          const runDetail = await workflowApi.getRun(workflowId, lastRun.id);
          if (!cancelled) {
            // step_logs keyed by node_id — match DSL id via node label or position
            const stepLog = runDetail?.step_logs?.find(s =>
              String(s.node_id) === String(node.id) ||
              (runDetail?.step_logs?.length === 1)
            );
            if (stepLog?.output_json) {
              setInputData({ data: stepLog.output_json, source: 'run' });
              setInputLoading(false);
              return;
            }
          }
        }
      } catch {
        // fall through to tier 3
      }

      // Tier 3: output_schema as empty reference
      if (!cancelled) {
        setInputData({ data: {}, source: 'schema' });
        setInputLoading(false);
      }
    }

    loadInput();
    return () => { cancelled = true; };
  }, [node.id, workflowId, sessionCache]);

  // ── Keyboard handler (Esc to close, focus trap) ──────────────────────────
  useEffect(() => {
    function onKeyDown(e) {
      if (e.key === 'Escape') { onClose(); return; }
      if (e.key === 'Tab' && modalRef.current) {
        const focusable = modalRef.current.querySelectorAll(
          'button, input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey ? document.activeElement === first : document.activeElement === last) {
          e.preventDefault();
          (e.shiftKey ? last : first)?.focus();
        }
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  // ── Param field handlers ──────────────────────────────────────────────────
  const handleParamChange = useCallback((key, value) => {
    setLocalParams(prev => ({ ...prev, [key]: value }));
    setDirtyFields(prev => new Set([...prev, key]));
    // Clear validation error while editing
    setValidationErrors(prev => { const n = { ...prev }; delete n[key]; return n; });
  }, []);

  const commitParam = useCallback((key, value) => {
    if (!plugin) return;
    const prop = plugin.parameter_schema?.properties?.[key];
    const err = validateField(value, prop);
    if (err) {
      setValidationErrors(prev => ({ ...prev, [key]: err }));
      return;
    }
    setDirtyFields(prev => { const n = new Set(prev); n.delete(key); return n; });
    onParamChange(node.id, key, value);
  }, [plugin, node.id, onParamChange]);

  const handleApply = useCallback((key) => {
    commitParam(key, localParams[key]);
  }, [commitParam, localParams]);

  const handleBlur = useCallback((key, value) => {
    const ui = plugin?.parameter_schema?.properties?.[key]?.ui || {};
    const widget = ui.widget || 'text';
    if (!LARGE_EDITOR_WIDGETS.has(widget)) {
      commitParam(key, value);
    }
  }, [plugin, commitParam]);

  // ── Settings handler ──────────────────────────────────────────────────────
  const handleSettingChange = useCallback((key, value) => {
    onSettingChange(node.id, key, value);
  }, [node.id, onSettingChange]);

  // ── Execute Step ──────────────────────────────────────────────────────────
  const handleExecute = useCallback(async () => {
    if (executeInFlight.current) return; // double-submit guard
    executeInFlight.current = true;
    setExecuting(true);
    setExecuteResult(null);

    // Validate all params client-side before calling the backend
    const schema = plugin?.parameter_schema;
    const errors = validateParams(localParams, schema);
    if (Object.keys(errors).length > 0) {
      setValidationErrors(errors);
      setExecuting(false);
      executeInFlight.current = false;
      return;
    }

    try {
      // Read latest locally-patched params at click time (not modal-open snapshot)
      const result = await workflowApi.executeNode(workflowId, node.id, {
        paramsOverride: localParams,
      });
      setExecuteResult(result);
      // Update session cache (tier-1 for INPUT on next open)
      onCacheUpdate(node.id, result);
    } catch (err) {
      setExecuteResult({
        success: false,
        error: err?.message || 'Request failed',
        error_type: 'node',
        output: {},
        duration_ms: 0,
      });
    } finally {
      setExecuting(false);
      executeInFlight.current = false;
    }
  }, [workflowId, node.id, localParams, plugin, onCacheUpdate]);

  // ─────────────────────────────────────────────────────────────────────────
  const schemaRequired = new Set(plugin?.parameter_schema?.required || []);
  const iconGlyph = ICON_MAP[plugin?.icon] || '⚙';
  const hasNotes = node.display_note_in_flow && node.notes;

  return (
    <AnimatePresence>
      {/* Backdrop */}
      <motion.div
        key="backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        className="fixed inset-0 bg-black/50 z-40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <motion.div
        key="panel"
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Node Inspector: ${node.label}`}
        initial={{ opacity: 0, x: 40 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 40 }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
        className="fixed right-0 top-0 h-full w-[760px] max-w-full z-50 flex flex-col bg-slate-950 border-l border-white/10 shadow-2xl"
      >
        {/* ── Header ── */}
        <div className="flex items-center gap-3 px-6 py-4 border-b border-white/10 flex-shrink-0">
          <div
            className="w-9 h-9 rounded-xl flex items-center justify-center text-base flex-shrink-0"
            style={{ background: 'rgba(6,182,212,0.15)', border: '1px solid rgba(6,182,212,0.3)' }}
          >
            {iconGlyph}
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-[9px] font-bold tracking-widest uppercase text-cyan-400 font-mono">
              {node.service} · {node.operation}
            </div>
            <div className="text-base font-bold text-white truncate">{node.label}</div>
          </div>
          {plugin?.doc_url && (
            <a
              id="inspector-docs-link"
              href={plugin.doc_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-slate-400 hover:text-cyan-400 transition-colors px-2 py-1 rounded-lg border border-white/10 hover:border-cyan-500/30"
            >
              Docs <ExternalLink size={11} />
            </a>
          )}
          <button
            id="inspector-close"
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-1.5 rounded-lg hover:bg-white/10"
            aria-label="Close inspector"
          >
            <X size={18} />
          </button>
        </div>

        {/* ── Body: three columns ── */}
        <div className="flex-1 flex overflow-hidden">

          {/* INPUT column */}
          <div className="w-52 flex-shrink-0 border-r border-white/10 flex flex-col p-4 overflow-y-auto">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[9px] font-bold tracking-widest uppercase text-slate-500">Input</p>
              {inputData?.source && (
                <span className="text-[9px] text-slate-600 font-mono">
                  {inputData.source === 'cache' ? 'execute step' :
                   inputData.source === 'run' ? 'last run' : 'schema ref'}
                </span>
              )}
            </div>

            {inputLoading ? (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Loader2 size={12} className="animate-spin" /> Loading...
              </div>
            ) : (
              <OutputView
                data={inputData?.data || {}}
                schema={plugin?.output_schema}
              />
            )}
          </div>

          {/* MIDDLE column: tabs */}
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Tab bar */}
            <div className="flex border-b border-white/10 px-4 flex-shrink-0">
              {[['parameters', Sliders, 'Parameters'], ['settings', Settings, 'Settings']].map(([tab, Icon, label]) => (
                <button
                  key={tab}
                  id={`inspector-tab-${tab}`}
                  onClick={() => setActiveTab(tab)}
                  className={`flex items-center gap-1.5 px-3 py-3 text-xs font-semibold border-b-2 transition-all -mb-px ${
                    activeTab === tab
                      ? 'border-cyan-500 text-cyan-400'
                      : 'border-transparent text-slate-500 hover:text-slate-300'
                  }`}
                >
                  <Icon size={12} />{label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto p-4">
              {activeTab === 'parameters' && (
                <div className="space-y-4">
                  {pluginLoading ? (
                    <div className="flex items-center gap-2 text-xs text-slate-500">
                      <Loader2 size={12} className="animate-spin" /> Loading schema...
                    </div>
                  ) : plugin ? (
                    Object.entries(plugin.parameter_schema?.properties || {}).map(([key, prop]) => (
                      <ParamField
                        key={key}
                        fieldKey={key}
                        schema={prop}
                        value={localParams[key] ?? node.params[key] ?? ''}
                        onChange={handleParamChange}
                        onBlur={handleBlur}
                        onApply={handleApply}
                        isDirty={dirtyFields.has(key)}
                        validationError={validationErrors[key]}
                        schemaRequired={schemaRequired.has(key)}
                      />
                    ))
                  ) : (
                    <p className="text-xs text-slate-500 italic">
                      No schema registered for {node.service}.{node.operation}
                    </p>
                  )}
                </div>
              )}

              {activeTab === 'settings' && (
                <SettingsTab node={node} onSettingChange={handleSettingChange} />
              )}
            </div>

            {/* ── ACTION SLOT ──────────────────────────────────────────────────────
                Sprint 4: "Improve with AI" entry point will be inserted here.
                Do NOT build any AI affordance now — the slot is structurally reserved
                so Sprint 4 can inject a button without restructuring the modal layout.
                Leave as a named comment only (no DOM element needed yet).
            ─────────────────────────────────────────────────────────────────────── */}
          </div>

          {/* OUTPUT column */}
          <div className="w-56 flex-shrink-0 border-l border-white/10 flex flex-col p-4 overflow-y-auto">
            <p className="text-[9px] font-bold tracking-widest uppercase text-slate-500 mb-3">Output</p>

            {/* Execute Step button */}
            <button
              id="execute-step-btn"
              onClick={handleExecute}
              disabled={executing}
              className={`w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl font-semibold text-sm transition-all mb-4 ${
                executing
                  ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-white/10'
                  : 'bg-gradient-to-r from-cyan-600 to-cyan-500 text-white hover:from-cyan-500 hover:to-cyan-400 shadow-lg shadow-cyan-500/20 hover:shadow-cyan-500/30'
              }`}
              aria-busy={executing}
            >
              {executing ? (
                <><Loader2 size={14} className="animate-spin" /> Running...</>
              ) : (
                <><Zap size={14} /> Execute Step</>
              )}
            </button>

            {/* execute_once / always_output_data no-op notice */}
            {(node.execute_once || node.always_output_data) && (
              <div className="mb-3 p-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-[10px] text-amber-400" role="note">
                {node.execute_once && <p>⚠ Execute Once is a no-op here (full runs only).</p>}
                {node.always_output_data && <p>⚠ Always Output Data is a no-op here (full runs only).</p>}
              </div>
            )}

            {/* Results */}
            {executeResult ? (
              <div className="space-y-3 flex-1">
                {/* Status badge */}
                <div className={`flex items-center gap-2 p-2.5 rounded-xl text-xs font-semibold ${
                  executeResult.success
                    ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
                    : 'bg-rose-500/10 border border-rose-500/20 text-rose-400'
                }`} role={executeResult.success ? undefined : 'alert'}>
                  {executeResult.success
                    ? <><CheckCircle2 size={13} /> Success</>
                    : <><AlertCircle size={13} /> {executeResult.error_type || 'Error'}</>
                  }
                  <span className="ml-auto text-[10px] font-normal text-slate-500">
                    {executeResult.duration_ms}ms
                  </span>
                </div>

                {/* Error message */}
                {!executeResult.success && executeResult.error && (
                  <div className="p-2.5 rounded-xl bg-rose-500/5 border border-rose-500/15 text-[11px] text-rose-300 break-words">
                    {executeResult.error}
                    {executeResult.error_type === 'credential' && (
                      <p className="mt-1.5 text-rose-400 font-semibold">
                        → Connect or re-authenticate your {node.service} integration.
                      </p>
                    )}
                  </div>
                )}

                {/* Output data */}
                {executeResult.success && (
                  <OutputView
                    data={executeResult.output}
                    schema={plugin?.output_schema}
                  />
                )}
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center gap-2 py-8 text-slate-600">
                <Zap size={24} className="opacity-20" />
                <p className="text-xs">Run the node to see output here.</p>
                <p className="text-[10px] text-slate-700">Uses real credentials — no mocks.</p>
              </div>
            )}
          </div>
        </div>

        {/* ── Node ID footer ── */}
        <div className="px-6 py-2 border-t border-white/5 flex items-center gap-3 flex-shrink-0">
          <span className="text-[9px] font-mono text-slate-600">#{node.id}</span>
          {hasNotes && (
            <span className="flex items-center gap-1 text-[9px] text-amber-400/60">
              <StickyNote size={9} /> {node.notes?.slice(0, 60)}{node.notes?.length > 60 ? '…' : ''}
            </span>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
