// File path: frontend/src/pages/Dashboard.jsx
//
// Campaign index. Rendered as an editorial list (name, one line of
// metadata, status) separated by hairlines -- not a grid of cards. With
// no campaigns yet it shows a short "getting started" list instead.

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/apiClient";
import { formatFollowers } from "../lib/format";

export function Dashboard() {
  const [campaigns, setCampaigns] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .get("/api/campaigns")
      .then(setCampaigns)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div style={{ maxWidth: "52rem" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "var(--space-4)",
        }}
      >
        <h2>Campaigns</h2>
        <Link to="/campaigns/new" className="btn" style={{ textDecoration: "none" }}>
          New campaign
        </Link>
      </header>

      {error && (
        <p className="error-text" role="alert">
          {error}
        </p>
      )}

      {!campaigns && !error && <p className="muted">Loading…</p>}

      {campaigns && campaigns.length === 0 && <GettingStarted />}

      {campaigns && campaigns.length > 0 && (
        <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {campaigns.map((c) => (
            <CampaignRow key={c.id} campaign={c} />
          ))}
        </ul>
      )}
    </div>
  );
}

function GettingStarted() {
  return (
    <div style={{ padding: "var(--space-4) 0" }}>
      <h3 style={{ marginBottom: "var(--space-2)" }}>Welcome to Crew</h3>
      <p className="muted" style={{ marginBottom: "var(--space-3)" }}>
        Three steps to your first list of creators:
      </p>
      <ol style={{ margin: 0, paddingLeft: "1.2rem", maxWidth: "36rem" }}>
        <li style={{ marginBottom: "var(--space-2)" }}>
          <Link to="/settings">Connect your Gmail</Link>. This lets you save drafts and send
          emails. You can skip it for now and do it later.
        </li>
        <li style={{ marginBottom: "var(--space-2)" }}>
          <Link to="/campaigns/new">Create a campaign</Link> describing the creators you're
          looking for.
        </li>
        <li style={{ marginBottom: "var(--space-2)" }}>
          Open the campaign and click <strong>Run pipeline</strong>. Crew finds, reviews and
          drafts emails for creators.
        </li>
      </ol>
      <p style={{ marginTop: "var(--space-3)" }}>
        <Link to="/guide">Read the full guide →</Link>
      </p>
    </div>
  );
}

function CampaignRow({ campaign }) {
  const range = `${formatFollowers(campaign.min_followers)}–${formatFollowers(
    campaign.max_followers
  )} followers`;

  return (
    <li style={{ borderTop: "1px solid var(--rule)" }}>
      <Link
        to={`/campaigns/${campaign.id}`}
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          gap: "var(--space-3)",
          padding: "var(--space-3) 0",
          textDecoration: "none",
          color: "inherit",
        }}
      >
        <div>
          <h3 style={{ fontFamily: "var(--font-display)", fontSize: "1.25rem", fontWeight: 500 }}>
            {campaign.name}
          </h3>
          <p className="muted" style={{ fontSize: "0.88rem", marginTop: "0.25rem" }}>
            {campaign.category} · {campaign.target_country} · {campaign.platform} · {range}
          </p>
        </div>
        <span className="status-pill" data-tone={toneFor(campaign.status)}>
          {campaign.status}
        </span>
      </Link>
    </li>
  );
}

function toneFor(status) {
  if (status === "completed") return "active";
  if (status === "running" || status === "queued") return "pending";
  return undefined;
}