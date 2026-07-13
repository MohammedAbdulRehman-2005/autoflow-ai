/** AutoFlow AI X — TextField  (Sprint 3.5, Goal 1) */
import { memo } from 'react';

const INPUT_CLASS =
  'w-full bg-slate-900/60 border border-white/10 rounded-xl px-3 py-2 text-sm text-slate-200 ' +
  'focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/20 disabled:opacity-50';

function TextField({ fieldKey, value, schema, ui, onChange, onBlur, disabled }) {
  const isSecret = ui?.secret;
  const isNumber = schema?.type === 'integer' || schema?.type === 'number';
  const inputType = isSecret ? 'password' : isNumber ? 'number' : 'text';

  return (
    <input
      id={`param-${fieldKey}`}
      type={inputType}
      value={value ?? ''}
      disabled={disabled}
      min={schema?.minimum}
      max={schema?.maximum}
      onChange={e => onChange(
        fieldKey,
        isNumber ? (e.target.value === '' ? '' : Number(e.target.value)) : e.target.value,
      )}
      onBlur={e => onBlur(
        fieldKey,
        isNumber ? Number(e.target.value) : e.target.value,
      )}
      placeholder={ui?.placeholder ?? ''}
      autoComplete={isSecret ? 'off' : undefined}
      className={INPUT_CLASS}
    />
  );
}

export { TextField };
export default memo(TextField);
