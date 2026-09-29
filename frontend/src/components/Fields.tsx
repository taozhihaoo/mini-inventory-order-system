import type { ChangeEvent, ReactNode } from "react";

interface FieldProps {
  label: string;
  required?: boolean;
  error?: string | null;
  hint?: string;
  children: ReactNode;
}

export function Field({ label, required, error, hint, children }: FieldProps) {
  return (
    <label className="field">
      <span className="field-label">
        {label}
        {required && <span className="field-required"> *</span>}
      </span>
      {children}
      {hint && !error && <span className="field-hint">{hint}</span>}
      {error && <span className="field-error">{error}</span>}
    </label>
  );
}

export function TextInput(props: {
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  min?: number | string;
  max?: number | string;
  step?: number | string;
  disabled?: boolean;
}) {
  const { value, onChange, type = "text", ...rest } = props;
  return (
    <input
      className="input"
      type={type}
      value={value}
      onChange={(event: ChangeEvent<HTMLInputElement>) => onChange(event.target.value)}
      {...rest}
    />
  );
}

export function TextArea(props: { value: string; onChange: (value: string) => void; rows?: number; placeholder?: string }) {
  const { value, onChange, rows = 3, placeholder } = props;
  return (
    <textarea
      className="input"
      rows={rows}
      value={value}
      placeholder={placeholder}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export function Select(props: {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  disabled?: boolean;
}) {
  const { value, onChange, options, disabled } = props;
  return (
    <select className="input" value={value} onChange={(event) => onChange(event.target.value)} disabled={disabled}>
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}
