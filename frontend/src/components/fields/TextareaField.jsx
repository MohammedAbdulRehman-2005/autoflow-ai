/** AutoFlow AI X — TextareaField  (Sprint 3.5, Goal 1) */
import { memo } from 'react';

function TextareaField({ fieldKey, value, ui, isDirty, disabled }) {
  return (
    <textarea
      id={`param-${fieldKey}`}
      rows={4}
      value={value ?? ''}
      readOnly={disabled}
      disabled={disabled}
      placeholder={ui?.placeholder ?? ''}
      spellCheck={false}
      className={
        'w-full bg-slate-900/60 border rounded-xl px-3 py-2 text-sm text-slate-200 font-mono ' +
        'resize-y focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 ' +
        'disabled:opacity-50 ' +
        (isDirty ? 'border-amber-500/40' : 'border-white/10')
      }
    />
  );
}

export { TextareaField };
export default memo(TextareaField);
