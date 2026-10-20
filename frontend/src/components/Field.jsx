// File path: frontend/src/components/Field.jsx
// A labelled input with an inline error, wired up for screen readers
// (aria-invalid / aria-describedby).

export function Field({ id, label, error, hint, ...inputProps }) {
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;

  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        {...inputProps}
      />
      {hint && !error && (
        <span id={`${id}-hint`} className="muted" style={{ fontSize: "0.8rem" }}>
          {hint}
        </span>
      )}
      {error && (
        <span id={`${id}-error`} className="error-text">
          {error}
        </span>
      )}
    </div>
  );
}