// File path: frontend/src/components/InfluencerCard.jsx
//
// One discovered creator, rendered as an index entry: handle and
// summary on the left, review score on the right, actions underneath.
// The outreach email draft expands inline; "Mark as sent" is a manual
// step because this system only ever drafts emails -- it never sends.

import { useState } from "react";
import { api } from "../lib/apiClient";
import { formatFollowers, normalizeScore } from "../lib/format";
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

export function InfluencerCard({ influencer, onUpdated }) {
  const [showDraft, setShowDraft] = useState(false);
  const [copied, setCopied] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState(null);

  const draft = influencer.email_draft;
  const hasDraft = Boolean(draft && (draft.subject || draft.body));
  const score = normalizeScore(influencer.review_score);
  const handle = (influencer.username || "").replace(/^@/, "");

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

  async function markSent() {
    setBusy(true);
    setActionError(null);
    try {
      const updated = await api.patch(`/api/influencers/${influencer.id}`, {
        outreach_status: "sent",
      });
      onUpdated(updated);
    } catch (err) {
      setActionError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="influencer-entry">
      <div>
        <div className="influencer-handle">{influencer.username || influencer.name}</div>
        <p className="muted" style={{ fontSize: "0.88rem", marginTop: "0.25rem" }}>
          {[
            influencer.username ? influencer.name : null,
            `${formatFollowers(influencer.followers)} followers`,
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
            <button className="link-button" onClick={markSent} disabled={busy}>
              {busy ? "Saving…" : "Mark as sent"}
            </button>
          )}
        </div>

        {actionError && (
          <p className="error-text" style={{ marginTop: "var(--space-1)" }}>
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