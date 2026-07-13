/** AutoFlow AI X — ToggleField  (Sprint 3.5, Goal 1) */
import { memo } from 'react';

function ToggleField({ fieldKey, value, onChange, onBlur, disabled }) {
  const checked = !!value;
  return (
    <button
      id={`param-${fieldKey}`}
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => {
        const next = !checked;
        onChange(fieldKey, next);
        onBlur(fieldKey, next);
      }}
      className={
        'relative w-9 h-5 rounded-full transition-colors disabled:opacity-50 ' +
        (checked ? 'bg-cyan-500' : 'bg-slate-700')
      }
    >
      <span
        className={
          'absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ' +
          (checked ? 'translate-x-4' : '')
        }
      />
    </button>
  );
}

export { ToggleField };
export default memo(ToggleField);
