// File path: frontend/src/components/GmailConnectCard.jsx
//
// Shows the Gmail connection and lets the user connect, reconnect or
// disconnect. Connecting sends the browser to Google's consent screen;
// Google then returns to the backend, which sends them back to Settings.

import { useState } from "react";
import { api } from "../lib/apiClient";
import { parseUtc } from "../lib/format";

export function GmailConnectCard({ status, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      const { auth_url } = await api.get("/api/gmail/connect");
      window.location.assign(auth_url);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  async function disconnect() {
    const sure = window.confirm(
      "Disconnect Gmail? You won't be able to save drafts or send emails until you connect it again."
    );
    if (!sure) return;
    setBusy(true);
    setError(null);
    try {
      await api.delete("/api/gmail/connection");
      await onChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!status) return <p className="muted">Checking Gmail…</p>;

  if (!status.configured) {
    return (
      <p className="muted">
        Gmail isn't set up on this server yet. Ask the administrator to add the
        Google credentials.
      </p>
    );
  }

  const since = status.connected_at ? parseUtc(status.connected_at) : null;

  return (
    <div>
      {status.connected && (
        <p>
          Connected as <strong>{status.email}</strong>
          {since && (
            <span className="muted">
              {" "}
              since {since.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })}
            </span>
          )}
          . Emails you save or send go through this account.
        </p>
      )}

      {status.needs_reconnect && (
        <p className="error-text" role="alert">
          Your Gmail connection{status.email ? ` (${status.email})` : ""} has
          expired or was revoked. Reconnect to keep sending.
        </p>
      )}

      {!status.connected && !status.needs_reconnect && (
        <>
          <p className="muted">
            Connect the Gmail account your outreach should come from. You'll be
            asked on Google's own page, and you can disconnect any time.
          </p>
          <details style={{ fontSize: "0.88rem", marginBottom: "var(--space-3)" }}>
            <summary style={{ cursor: "pointer", color: "var(--ink-soft)" }}>
              What you'll see on Google
            </summary>
            <p className="muted" style={{ marginTop: "var(--space-2)" }}>
              Crew is an independent developer app that Google hasn't put
              through its own review yet, so you'll likely see "Google hasn't
              verified this app." That's standard for small apps. Click{" "}
              <strong>Advanced</strong>, then{" "}
              <strong>Go to Crew (unsafe)</strong>, and tick every permission
              box so Crew can save drafts and send on your behalf. If Google
              says your account isn't allowed, it needs to be added as a test
              user first — ask the administrator.
            </p>
          </details>
        </>
      )}

      {status.needs_reconnect && (
        <details style={{ fontSize: "0.88rem", marginBottom: "var(--space-3)" }}>
          <summary style={{ cursor: "pointer", color: "var(--ink-soft)" }}>
            What you'll see on Google
          </summary>
          <p className="muted" style={{ marginTop: "var(--space-2)" }}>
            You may see "Google hasn't verified this app" again — that's
            standard. Click <strong>Advanced</strong>, then{" "}
            <strong>Go to Crew (unsafe)</strong>, and re-approve every box.
          </p>
        </details>
      )}

      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}

      <div className="entry-actions">
        {status.connected ? (
          <button className="btn btn-secondary" onClick={disconnect} disabled={busy}>
            Disconnect Gmail
          </button>
        ) : (
          <button className="btn" onClick={connect} disabled={busy}>
            {busy ? "Opening Google…" : status.needs_reconnect ? "Reconnect Gmail" : "Connect Gmail"}
          </button>
        )}
      </div>
    </div>
  );
}