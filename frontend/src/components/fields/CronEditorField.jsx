/** AutoFlow AI X — CronEditorField  (Sprint 3.5, Goal 1 — placeholder) */
import { memo } from 'react';
import TextField from './TextField';

function CronEditorField({ fieldKey, value, schema, ui, onChange, onBlur, validationError, disabled }) {
  return (
    <div className="space-y-1">
      <TextField
        fieldKey={fieldKey}
        value={value}
        schema={schema}
        ui={{ ...ui, placeholder: ui?.placeholder ?? '0 9 * * 1' }}
        onChange={onChange}
        onBlur={onBlur}
        validationError={validationError}
        disabled={disabled}
      />
      <p className="text-[10px] text-slate-500 flex items-center gap-1">
        ⏰ Visual cron builder coming in a future sprint.
      </p>
    </div>
  );
}

export { CronEditorField };
export default memo(CronEditorField);
