// File path: frontend/src/pages/Dashboard.jsx
//
// Campaign index. Rendered as an editorial list (name, one line of
// metadata, status) separated by hairlines -- not a grid of cards.

import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/apiClient";

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

      {error && <p className="error-text">{error}</p>}

      {!campaigns && !error && <p className="muted">Loading…</p>}

      {campaigns && campaigns.length === 0 && (
        <div style={{ padding: "var(--space-5) 0" }}>
          <h3 style={{ marginBottom: "var(--space-2)" }}>No campaigns yet</h3>
          <p className="muted">
            Create your first campaign to start discovering creators.
          </p>
        </div>
      )}

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

function formatFollowers(n) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
  return String(n);
}

function toneFor(status) {
  if (status === "completed") return "active";
  if (status === "running" || status === "queued") return "pending";
  return undefined;
}