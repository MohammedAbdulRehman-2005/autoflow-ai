/** AutoFlow AI X — SelectField  (Sprint 3.5, Goal 1) */
import { memo } from 'react';

const SELECT_CLASS =
  'w-full bg-slate-900/60 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-200 ' +
  'focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 disabled:opacity-50';

function SelectField({ fieldKey, value, schema, onChange, onBlur, disabled }) {
  const options = schema?.enum ?? [];
  return (
    <select
      id={`param-${fieldKey}`}
      value={value ?? ''}
      disabled={disabled}
      onChange={e => onChange(fieldKey, e.target.value)}
      onBlur={e => onBlur(fieldKey, e.target.value)}
      className={SELECT_CLASS}
    >
      <option value="">Select...</option>
      {options.map(opt => (
        <option key={opt} value={opt}>{opt}</option>
      ))}
    </select>
  );
}

export { SelectField };
export default memo(SelectField);
