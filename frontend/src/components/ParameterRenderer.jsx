/**
 * AutoFlow AI X — ParameterRenderer  (Sprint 3.5, Goal 1)
 * =========================================================
 * Schema-driven parameter field renderer.
 *
 * Resolution order:
 *   1. ui.widget (explicit — e.g. 'slider', 'prompt', 'secret', 'cron')
 *   2. 'credential_select' — rendered as SecretField until Sprint 4 OAuth picker
 *   3. schema.type fallback:
 *        boolean       → ToggleField
 *        enum          → SelectField
 *        integer/number → TextField[type=number]
 *        array/object   → JsonEditorField
 *        string (default) → TextField
 *
 * LARGE_EDITOR_WIDGETS: textarea, json, expression, prompt
 *   These use a draft/apply pattern: onChange updates draft, onBlur is suppressed,
 *   an Apply button calls onCommit when clicked.
 *
 * @module ParameterRenderer
 */

import { memo, useState, useCallback } from 'react';
import { Info, AlertCircle } from 'lucide-react';

import TextField        from './fields/TextField';
import TextareaField    from './fields/TextareaField';
import ToggleField      from './fields/ToggleField';
import SelectField      from './fields/SelectField';
import SliderField      from './fields/SliderField';
import JsonEditorField  from './fields/JsonEditorField';
import PromptEditorField from './fields/PromptEditorField';
import CronEditorField  from './fields/CronEditorField';
import SecretField      from './fields/SecretField';

// Widgets that require explicit Apply button — not auto-blur-commit
const LARGE_EDITOR_WIDGETS = new Set(['textarea', 'json', 'expression', 'prompt']);

/**
 * Resolve widget identifier from a JSON Schema property definition.
 *
 * @param {Object} schemaProp
 * @returns {string} widget key
 */
function resolveWidget(schemaProp) {
  const ui = schemaProp?.ui ?? {};
  if (ui.widget) return ui.widget;
  if (schemaProp?.type === 'boolean') return 'toggle';
  if (Array.isArray(schemaProp?.enum) && schemaProp.enum.length) return 'select';
  if (schemaProp?.type === 'integer' || schemaProp?.type === 'number') return 'number';
  if (schemaProp?.type === 'array' || schemaProp?.type === 'object') return 'json';
  return 'text';
}

/**
 * Map a widget identifier to its React component.
 * 'credential_select' uses SecretField until Sprint 4 OAuth picker.
 *
 * @param {string} widget
 * @returns {React.ComponentType}
 */
function getFieldComponent(widget) {
  const MAP = {
    text:              TextField,
    number:            TextField,
    textarea:          TextareaField,
    toggle:            ToggleField,
    select:            SelectField,
    slider:            SliderField,
    json:              JsonEditorField,
    expression:        TextareaField,   // expression ≈ textarea
    prompt:            PromptEditorField,
    cron:              CronEditorField,
    secret:            SecretField,
    credential_select: SecretField,     // Sprint 4: replace with CredentialPickerField
  };
  return MAP[widget] ?? TextField;
}


/**
 * ParameterRenderer
 *
 * Renders a single schema-defined parameter: label, widget, help text,
 * validation error, and (for large editors) an Apply button.
 *
 * @param {Object}   props
 * @param {string}   props.fieldKey       - Parameter key
 * @param {*}        props.value          - Current committed value
 * @param {Object}   props.schemaProp     - JSON Schema property definition
 * @param {boolean}  props.isRequired     - True if this field is in schema.required
 * @param {Function} props.onCommit       - fn(key, value) — called to persist a value
 * @param {boolean}  [props.disabled]     - Disable all input
 */
function ParameterRenderer({ fieldKey, value, schemaProp, isRequired, onCommit, disabled }) {
  const ui     = schemaProp?.ui ?? {};
  const widget = resolveWidget(schemaProp);
  const isLarge = LARGE_EDITOR_WIDGETS.has(widget);
  const FieldComponent = getFieldComponent(widget);

  // Large editors maintain local draft state until Apply is clicked
  const [draft, setDraft]   = useState(value);
  const [isDirty, setIsDirty] = useState(false);
  const [validationError]   = useState(null);

  const handleChange = useCallback((key, val) => {
    if (isLarge) {
      setDraft(val);
      setIsDirty(String(val ?? '') !== String(value ?? ''));
    }
    // Non-large fields bypass draft — they call onBlur directly
  }, [isLarge, value]);

  const handleBlur = useCallback((key, val) => {
    if (!isLarge) {
      onCommit(key, val);
    }
    // Large editors commit via Apply button only
  }, [isLarge, onCommit]);

  const handleApply = useCallback(() => {
    onCommit(fieldKey, draft);
    setIsDirty(false);
  }, [fieldKey, draft, onCommit]);

  const fieldId = `param-${fieldKey}`;

  return (
    <div className="space-y-1.5">
      {/* Label row */}
      <div className="flex items-center justify-between">
        <label
          htmlFor={fieldId}
          className="text-xs font-semibold text-slate-300 flex items-center gap-1"
        >
          {fieldKey}
          {isRequired && <span className="text-rose-400 ml-0.5">*</span>}
        </label>

        {isLarge && isDirty && (
          <button
            id={`apply-${fieldKey}`}
            type="button"
            onClick={handleApply}
            className="text-[10px] px-2 py-0.5 rounded-md bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/30 transition-colors"
          >
            Apply
          </button>
        )}
        {isLarge && !isDirty && value && (
          <span className="text-[10px] text-slate-500">saved</span>
        )}
      </div>

      {/* Widget */}
      <FieldComponent
        fieldKey={fieldKey}
        value={isLarge ? draft : value}
        schema={schemaProp}
        ui={ui}
        onChange={handleChange}
        onBlur={handleBlur}
        onApply={handleApply}
        isDirty={isDirty}
        validationError={validationError}
        disabled={disabled}
      />

      {/* Help text */}
      {ui.helpText && (
        <p className="text-[10px] text-slate-500 flex items-start gap-1">
          <Info size={9} className="mt-0.5 flex-shrink-0 text-slate-600" />
          {ui.helpText}
        </p>
      )}

      {/* Validation error */}
      {validationError && (
        <p className="text-[10px] text-rose-400 flex items-center gap-1" role="alert">
          <AlertCircle size={9} />
          {validationError}
        </p>
      )}
    </div>
  );
}

export { ParameterRenderer };
export default memo(ParameterRenderer);
