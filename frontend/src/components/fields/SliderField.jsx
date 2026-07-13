/** AutoFlow AI X — SliderField  (Sprint 3.5, Goal 1) */
import { memo } from 'react';

function SliderField({ fieldKey, value, schema, ui, onChange, onBlur, disabled }) {
  const min = schema?.minimum ?? 0;
  const max = schema?.maximum ?? 100;
  const step = ui?.step ?? 1;
  const current = value ?? min;

  return (
    <div className="flex items-center gap-3">
      <input
        id={`param-${fieldKey}`}
        type="range"
        min={min}
        max={max}
        step={step}
        value={current}
        disabled={disabled}
        onChange={e => onChange(fieldKey, Number(e.target.value))}
        onBlur={e => onBlur(fieldKey, Number(e.target.value))}
        className="flex-1 accent-cyan-500 disabled:opacity-50"
      />
      <span className="text-xs font-mono text-slate-300 w-10 text-right tabular-nums">
        {current}
      </span>
    </div>
  );
}

export { SliderField };
export default memo(SliderField);
