// File path: frontend/src/components/GmailPromptModal.jsx
//
// A one-time nudge to connect Gmail, shown after the user's details are
// saved. Unlike the details form it can be skipped -- Gmail is only needed
// at the moment someone saves a draft or sends, and that point explains
// what's missing.

import { useEffect, useRef, useState } from "react";
import { api } from "../lib/apiClient";
import "../styles/dialog.css";

export function GmailPromptModal({ onDismiss }) {
  const dialogRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => dialog?.close();
  }, []);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const { auth_url } = await api.get("/api/gmail/connect");
      onDismiss(); // asked once -- don't ask again after they return
      window.location.assign(auth_url);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="modal"
      aria-labelledby="gmail-prompt-title"
      onCancel={(e) => {
        e.preventDefault();
        onDismiss();
      }}
    >
      <h2 id="gmail-prompt-title" style={{ marginBottom: "var(--space-2)" }}>
        Connect your Gmail
      </h2>
      <p className="muted" style={{ marginBottom: "var(--space-3)" }}>
        Connect the Gmail account your outreach should come from. You can then
        save any drafted email to your Gmail drafts, or send it, with one
        click. Nothing is ever sent unless you press Send on a specific email.
      </p>
      <p className="muted" style={{ fontSize: "0.88rem", marginBottom: "var(--space-3)" }}>
        You'll approve this on Google's own page, and you can disconnect from
        Settings at any time.
      </p>
      <details style={{ marginBottom: "var(--space-4)", fontSize: "0.88rem" }}>
        <summary style={{ cursor: "pointer", color: "var(--ink-soft)" }}>
          What you'll see on Google
        </summary>
        <p className="muted" style={{ marginTop: "var(--space-2)" }}>
          Crew is an independent developer app that Google hasn't put through
          its own review yet, so you'll likely see a notice saying "Google
          hasn't verified this app." That's standard for small apps. Click{" "}
          <strong>Advanced</strong>, then <strong>Go to Crew (unsafe)</strong>,
          and tick every permission box so Crew can save drafts and send on
          your behalf. If Google says your account isn't allowed, it needs to
          be added as a test user first — ask the administrator.
        </p>
      </details>

      {error && (
        <p className="error-text" role="alert" style={{ marginBottom: "var(--space-3)" }}>
          {error}
        </p>
      )}

      <div className="entry-actions">
        <button className="btn" onClick={connect} disabled={busy}>
          {busy ? "Opening Google…" : "Connect Gmail"}
        </button>
        <button className="btn btn-secondary" onClick={onDismiss} disabled={busy}>
          Not now
        </button>
      </div>
    </dialog>
  );
}