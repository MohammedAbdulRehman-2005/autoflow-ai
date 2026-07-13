/** AutoFlow AI X — JsonEditorField  (Sprint 3.5, Goal 1) */
import { memo, useState } from 'react';

function JsonEditorField({ fieldKey, value, ui, isDirty, disabled }) {
  const [jsonError, setJsonError] = useState(null);

  const handleInput = (e) => {
    const raw = e.target.value;
    try {
      if (raw.trim()) JSON.parse(raw);
      setJsonError(null);
    } catch {
      setJsonError('Invalid JSON');
    }
    // onChange is called by parent ParameterRenderer via textarea's onChange prop
    e.target.dataset.raw = raw;
  };

  const borderClass = isDirty
    ? 'border-amber-500/40'
    : jsonError
      ? 'border-rose-500/40'
      : 'border-white/10';

  return (
    <div className="space-y-1">
      <textarea
        id={`param-${fieldKey}`}
        rows={6}
        defaultValue={value ?? ''}
        disabled={disabled}
        onInput={handleInput}
        placeholder={ui?.placeholder ?? '{}'}
        spellCheck={false}
        className={
          'w-full bg-slate-900/60 border rounded-xl px-3 py-2 text-sm text-slate-200 font-mono ' +
          'resize-y focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 ' +
          `disabled:opacity-50 ${borderClass}`
        }
      />
      {jsonError && (
        <p className="text-[10px] text-rose-400">{jsonError}</p>
      )}
    </div>
  );
}

export { JsonEditorField };
export default memo(JsonEditorField);
