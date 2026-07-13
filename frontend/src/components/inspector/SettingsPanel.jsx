/**
 * AutoFlow AI X — SettingsPanel  (Sprint 3.5, Goal 5)
 * =====================================================
 * Extracted from NodeInspector SettingsTab (lines 282-405).
 * Renders execution settings, error policy, retry, and notes.
 *
 * @param {Object}   props
 * @param {Object}   props.node            - DSL node object
 * @param {Function} props.onSettingChange - fn(key, value)
 */
import { memo } from 'react';

const ERROR_POLICY_OPTIONS = [
  { value: 'stop',     label: 'Stop',     desc: 'Halt the workflow immediately. on_failure is ignored.' },
  { value: 'continue', label: 'Continue', desc: 'Mark failed, route to on_failure if set.' },
  { value: 'retry',    label: 'Retry',    desc: 'Use retry_policy, then route to on_failure.' },
];

function Toggle({ id, checked, onClick }) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onClick}
      className={`ml-4 flex-shrink-0 relative w-9 h-5 rounded-full transition-colors ${checked ? 'bg-cyan-500' : 'bg-slate-700'}`}
    >
      <span className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${checked ? 'translate-x-4' : ''}`} />
    </button>
  );
}

function SettingsPanel({ node, onSettingChange }) {
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
          <Toggle
            id="setting-always-output"
            checked={!!node.always_output_data}
            onClick={() => onSettingChange('always_output_data', !node.always_output_data)}
          />
        </label>

        <label className="flex items-center justify-between cursor-pointer group">
          <span className="text-sm text-slate-300 group-hover:text-white transition-colors">
            Execute Once
            <span className="block text-[10px] text-slate-500 mt-0.5 font-normal">
              Skip if already ran in this run_id. No-op in Execute Step.
            </span>
          </span>
          <Toggle
            id="setting-execute-once"
            checked={!!node.execute_once}
            onClick={() => onSettingChange('execute_once', !node.execute_once)}
          />
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
          <Toggle
            id="setting-retry"
            checked={node.error_policy === 'retry'}
            onClick={() => onSettingChange('error_policy', node.error_policy === 'retry' ? 'stop' : 'retry')}
          />
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
          <Toggle
            id="setting-display-note"
            checked={!!node.display_note_in_flow}
            onClick={() => onSettingChange('display_note_in_flow', !node.display_note_in_flow)}
          />
          <span className="text-xs text-slate-400">Display note in flow</span>
        </label>
      </div>
    </div>
  );
}

export { SettingsPanel };
export default memo(SettingsPanel);
