// File path: frontend/src/components/InfluencerCard.jsx
//
// One discovered creator, rendered as an index entry: handle and
// summary on the left, review score on the right, actions underneath.
//
// Email flow: add the creator's address -> "Save to Gmail drafts" (review
// and edit it in Gmail) or "Send email" (asks to confirm first). Nothing
// is ever sent without the user pressing the confirm button for that one
// creator. "Mark as sent" remains for emails sent outside the app.

import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/apiClient";
import { formatFollowers, normalizeScore, parseUtc } from "../lib/format";
import "../styles/campaign.css";

const OUTREACH_LABELS = {
  not_started: "No draft",
  drafted: "Draft ready",
  sent: "Sent",
  replied: "Replied",
};

function outreachTone(status) {
  if (status === "sent" || status === "replied") return "active";
  if (status === "drafted") return "pending";
  return undefined;
}

function formatDate(value) {
  const date = parseUtc(value);
  return date
    ? date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" })
    : null;
}

export function InfluencerCard({ influencer, onUpdated, gmail }) {
  const [showDraft, setShowDraft] = useState(false);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(null); // "sent-mark" | "email" | "draft" | "send"
  const [actionError, setActionError] = useState(null);
  const [editingEmail, setEditingEmail] = useState(false);
  const [emailInput, setEmailInput] = useState("");
  const [confirmSend, setConfirmSend] = useState(false);

  const draft = influencer.email_draft;
  const hasDraft = Boolean(draft && (draft.subject || draft.body));
  const score = normalizeScore(influencer.review_score);
  const handle = (influencer.username || "").replace(/^@/, "");
  const isSent = influencer.outreach_status === "sent" || influencer.outreach_status === "replied";
  const sentOn = formatDate(influencer.gmail?.sent_at);

  // Runs one request, keeping the busy flag and any error message tidy.
  async function run(name, request, onDone) {
    setBusy(name);
    setActionError(null);
    try {
      const updated = await request();
      onUpdated(updated);
      onDone?.();
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(null);
    }
  }

  async function copyDraft() {
    try {
      await navigator.clipboard.writeText(
        `Subject: ${draft.subject ?? ""}\n\n${draft.body ?? ""}`
      );
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setActionError("Couldn't copy to the clipboard.");
    }
  }

  const markSent = () =>
    run("sent-mark", () =>
      api.patch(`/api/influencers/${influencer.id}`, { outreach_status: "sent" })
    );

  function saveEmail(e) {
    e.preventDefault();
    run(
      "email",
      () => api.patch(`/api/influencers/${influencer.id}`, { email: emailInput }),
      () => setEditingEmail(false)
    );
  }

  const saveGmailDraft = () =>
    run("draft", () => api.post(`/api/influencers/${influencer.id}/gmail/draft`));

  const sendEmail = () =>
    run(
      "send",
      () => api.post(`/api/influencers/${influencer.id}/gmail/send`),
      () => setConfirmSend(false)
    );

  const isEditingRecipient = editingEmail || !influencer.email;

  return (
    <li className="influencer-entry">
      <div>
        <div className="influencer-handle">{influencer.username || influencer.name}</div>
        <p className="muted" style={{ fontSize: "0.88rem", marginTop: "0.25rem" }}>
          {[
            influencer.username ? influencer.name : null,
            influencer.followers == null
              ? "Followers not found"
              : `${formatFollowers(influencer.followers)} followers`,
            influencer.category.join(", ") || null,
            influencer.location,
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>

        {influencer.review_reasoning && (
          <p style={{ marginTop: "var(--space-2)", fontSize: "0.92rem" }}>
            {influencer.review_reasoning}
          </p>
        )}

        <div className="entry-actions">
          <span className="status-pill" data-tone={outreachTone(influencer.outreach_status)}>
            {OUTREACH_LABELS[influencer.outreach_status] ?? influencer.outreach_status}
          </span>

          {handle && (
            <a
              href={`https://www.instagram.com/${handle}/`}
              target="_blank"
              rel="noreferrer"
              style={{ fontSize: "0.88rem" }}
            >
              Open on Instagram
            </a>
          )}

          {hasDraft && (
            <button className="link-button" onClick={() => setShowDraft((v) => !v)}>
              {showDraft ? "Hide email draft" : "View email draft"}
            </button>
          )}

          {influencer.outreach_status === "drafted" && (
            <button
              className="link-button"
              onClick={markSent}
              disabled={busy === "sent-mark"}
              title="Use this if you sent the email yourself, outside the app"
            >
              {busy === "sent-mark" ? "Saving…" : "Mark as sent"}
            </button>
          )}
        </div>

        {hasDraft && (
          <div style={{ marginTop: "var(--space-3)" }}>
            {isSent ? (
              <p className="muted" style={{ fontSize: "0.88rem" }}>
                Sent{influencer.email ? ` to ${influencer.email}` : ""}
                {influencer.gmail?.sent_from ? ` from ${influencer.gmail.sent_from}` : ""}
                {sentOn ? ` on ${sentOn}` : ""}.
              </p>
            ) : isEditingRecipient ? (
              <form
                onSubmit={saveEmail}
                style={{ display: "flex", gap: "var(--space-2)", alignItems: "center", flexWrap: "wrap" }}
              >
                <input
                  type="email"
                  required
                  aria-label="Creator's email address"
                  placeholder="creator@example.com"
                  value={emailInput}
                  onChange={(e) => setEmailInput(e.target.value)}
                  style={{
                    border: "1px solid var(--rule)",
                    background: "#fff",
                    padding: "0.45rem 0.6rem",
                    borderRadius: "2px",
                    minWidth: "15rem",
                  }}
                />
                <button className="btn btn-secondary" type="submit" disabled={busy === "email"}>
                  {busy === "email" ? "Saving…" : "Save email"}
                </button>
                {influencer.email && (
                  <button type="button" className="link-button" onClick={() => setEditingEmail(false)}>
                    Cancel
                  </button>
                )}
                {!influencer.email && (
                  <span className="muted" style={{ fontSize: "0.82rem", flexBasis: "100%" }}>
                    Add the creator's email address to send this. We find handles, not addresses.
                  </span>
                )}
              </form>
            ) : (
              <p className="muted" style={{ fontSize: "0.88rem" }}>
                To: {influencer.email}{" "}
                <button
                  className="link-button"
                  onClick={() => {
                    setEmailInput(influencer.email);
                    setEditingEmail(true);
                  }}
                >
                  Change
                </button>
              </p>
            )}

            {!isSent && !isEditingRecipient && gmail && (
              <>
                {!gmail.configured && (
                  <p className="muted" style={{ fontSize: "0.82rem", marginTop: "var(--space-2)" }}>
                    Sending isn't available: Gmail isn't set up on this server.
                  </p>
                )}

                {gmail.configured && !gmail.connected && (
                  <p className="muted" style={{ fontSize: "0.88rem", marginTop: "var(--space-2)" }}>
                    <Link to="/settings">
                      {gmail.needs_reconnect ? "Reconnect Gmail" : "Connect Gmail"}
                    </Link>{" "}
                    to save drafts and send from this app.
                  </p>
                )}

                {gmail.connected && !confirmSend && (
                  <div className="entry-actions">
                    <button className="btn btn-secondary" onClick={saveGmailDraft} disabled={busy !== null}>
                      {busy === "draft"
                        ? "Saving…"
                        : influencer.gmail?.draft_id
                        ? "Save to Gmail drafts again"
                        : "Save to Gmail drafts"}
                    </button>
                    <button className="btn" onClick={() => setConfirmSend(true)} disabled={busy !== null}>
                      Send email
                    </button>
                  </div>
                )}

                {gmail.connected && confirmSend && (
                  <div
                    role="alertdialog"
                    aria-label="Confirm sending"
                    style={{
                      marginTop: "var(--space-2)",
                      padding: "var(--space-3)",
                      borderLeft: "2px solid var(--berry)",
                      background: "var(--paper-raised)",
                    }}
                  >
                    <p style={{ fontSize: "0.92rem" }}>
                      Send this email to <strong>{influencer.email}</strong> from{" "}
                      <strong>{gmail.email}</strong>? It can't be unsent.
                    </p>
                    <div className="entry-actions">
                      <button className="btn" onClick={sendEmail} disabled={busy === "send"}>
                        {busy === "send" ? "Sending…" : "Yes, send it"}
                      </button>
                      <button
                        className="btn btn-secondary"
                        onClick={() => setConfirmSend(false)}
                        disabled={busy === "send"}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                )}

                {gmail.connected && influencer.gmail?.draft_id && !confirmSend && (
                  <p style={{ fontSize: "0.82rem", marginTop: "var(--space-1)", color: "var(--moss)" }}>
                    Saved to your Gmail drafts — you can edit it there. "Send email" sends that
                    saved version.
                  </p>
                )}
              </>
            )}
          </div>
        )}

        {actionError && (
          <p className="error-text" role="alert" style={{ marginTop: "var(--space-2)" }}>
            {actionError}
          </p>
        )}
      </div>

      <div className="influencer-score">
        {score != null ? score.toFixed(1) : "—"}
        <small>review score</small>
      </div>

      {showDraft && hasDraft && (
        <div className="email-draft">
          <h3 style={{ fontSize: "1rem" }}>{draft.subject || "(no subject)"}</h3>
          <pre>{draft.body}</pre>
          <div className="entry-actions">
            <button className="btn btn-secondary" onClick={copyDraft}>
              {copied ? "Copied" : "Copy email"}
            </button>
          </div>
        </div>
      )}
    </li>
  );
}