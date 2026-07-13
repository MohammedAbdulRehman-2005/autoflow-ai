/** AutoFlow AI X — SecretField  (Sprint 3.5, Goal 1) */
import { memo, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

function SecretField({ fieldKey, value, ui, onChange, onBlur, disabled }) {
  const [show, setShow] = useState(false);

  return (
    <div className="relative">
      <input
        id={`param-${fieldKey}`}
        type={show ? 'text' : 'password'}
        value={value ?? ''}
        disabled={disabled}
        onChange={e => onChange(fieldKey, e.target.value)}
        onBlur={e => onBlur(fieldKey, e.target.value)}
        placeholder={ui?.placeholder ?? 'Paste secret value...'}
        autoComplete="off"
        className={
          'w-full bg-slate-900/60 border border-white/10 rounded-xl px-3 py-2 pr-9 text-sm ' +
          'text-slate-200 font-mono focus:outline-none focus:border-cyan-500/50 ' +
          'focus:ring-1 focus:ring-cyan-500/20 disabled:opacity-50'
        }
      />
      <button
        type="button"
        onClick={() => setShow(v => !v)}
        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
        aria-label={show ? 'Hide value' : 'Show value'}
      >
        {show ? <EyeOff size={13} /> : <Eye size={13} />}
      </button>
    </div>
  );
}

export { SecretField };
export default memo(SecretField);
