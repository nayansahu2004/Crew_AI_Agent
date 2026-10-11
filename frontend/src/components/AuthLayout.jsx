// File path: frontend/src/components/AuthLayout.jsx
//
// Shared full-page layout for sign-in/sign-up: a single centered
// editorial column rather than a boxed "auth card" -- keeps it
// consistent with the rest of the app's visual language.

export function AuthLayout({ title, children, footer }) {
  return (
    <div
      style={{
        minHeight: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "var(--space-4)",
      }}
    >
      <div style={{ width: "100%", maxWidth: "24rem" }}>
        <h1 style={{ marginBottom: "var(--space-4)" }}>{title}</h1>
        {children}
        {footer && (
          <p className="muted" style={{ fontSize: "0.88rem", marginTop: "var(--space-4)" }}>
            {footer}
          </p>
        )}
      </div>
    </div>
  );
}