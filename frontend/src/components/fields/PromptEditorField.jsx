/** AutoFlow AI X — PromptEditorField  (Sprint 3.5, Goal 1) */
import { memo } from 'react';

function PromptEditorField({ fieldKey, value, schema, ui, isDirty, disabled }) {
  const charCount = (value ?? '').length;
  const maxLen = schema?.maxLength;

  return (
    <div className="space-y-1">
      <textarea
        id={`param-${fieldKey}`}
        rows={8}
        value={value ?? ''}
        readOnly   // large editor — parent passes value; user commits via Apply
        disabled={disabled}
        placeholder={ui?.placeholder ?? 'Enter your prompt...'}
        spellCheck={false}
        className={
          'w-full bg-slate-900/60 border rounded-xl px-3 py-2 text-sm text-slate-200 ' +
          'resize-y focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 ' +
          'disabled:opacity-50 ' +
          (isDirty ? 'border-amber-500/40' : 'border-white/10')
        }
      />
      <p className="text-[10px] text-slate-500 text-right tabular-nums">
        {charCount}{maxLen ? ` / ${maxLen}` : ''} chars
      </p>
    </div>
  );
}

export { PromptEditorField };
export default memo(PromptEditorField);
