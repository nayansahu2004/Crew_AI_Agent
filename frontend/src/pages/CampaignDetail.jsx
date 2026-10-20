// File path: frontend/src/pages/CampaignDetail.jsx
//
// A campaign's page: its settings, the pipeline Run control with live
// progress, and the creators found so far (with review scores and
// outreach email drafts). Each run uses one of the account's free
// searches; when none are left the Run button is replaced by a notice
// explaining how to get more.

import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../lib/apiClient";
import { useAuth } from "../context/AuthContext";
import { formatFollowers, normalizeScore } from "../lib/format";
import { searchesLabel } from "../lib/siteConfig";
import { ACTIVE_STATUSES, useRunPolling } from "../hooks/useRunPolling";
import { useGmailStatus } from "../hooks/useGmailStatus";
import { RunProgress } from "../components/RunProgress";
import { InfluencerCard } from "../components/InfluencerCard";
import { UpgradeNotice } from "../components/UpgradeNotice";
import "../styles/campaign.css";

export function CampaignDetail() {
  const { id } = useParams();
  const { status: gmailStatus } = useGmailStatus();
  const { profile, refreshProfile } = useAuth();
  const [campaign, setCampaign] = useState(null);
  const [influencers, setInfluencers] = useState(null);
  const [activeRunId, setActiveRunId] = useState(null);
  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(false);
  const [runError, setRunError] = useState(null);

  // Searches left; null means this account is unlimited.
  const credits = profile?.run_credits ?? null;
  const outOfSearches = credits === 0;

  // Load everything on arrival. The newest run (if any) becomes the one
  // we show/poll, so a page refresh mid-run picks the progress view back
  // up instead of losing it.
  useEffect(() => {
    let cancelled = false;
    setCampaign(null);
    setInfluencers(null);
    setActiveRunId(null);
    setError(null);

    Promise.all([
      api.get(`/api/campaigns/${id}`),
      api.get(`/api/campaigns/${id}/influencers`),
      api.get(`/api/campaigns/${id}/runs`),
    ])
      .then(([c, inf, runs]) => {
        if (cancelled) return;
        setCampaign(c);
        setInfluencers(inf);
        setActiveRunId(runs[0]?.run_id ?? null);
      })
      .catch((err) => !cancelled && setError(err.message));

    return () => {
      cancelled = true;
    };
  }, [id]);

  // When a run we were watching finishes, pull in the new creators, the
  // campaign's updated status, and the search count (a failed run gives its
  // search back).
  const handleRunFinished = useCallback(() => {
    api.get(`/api/campaigns/${id}/influencers`).then(setInfluencers).catch(() => {});
    api.get(`/api/campaigns/${id}`).then(setCampaign).catch(() => {});
    refreshProfile();
  }, [id, refreshProfile]);

  const { run, error: pollError, timedOut } = useRunPolling(activeRunId, handleRunFinished);

  const runIsActive = run ? ACTIVE_STATUSES.has(run.status) : false;
  const waitingForFirstPoll = Boolean(activeRunId) && !run && !pollError;
  const working = starting || runIsActive;
  const runDisabled = working || waitingForFirstPoll || outOfSearches;

  async function startRun() {
    setStarting(true);
    setRunError(null);
    try {
      const created = await api.post(`/api/campaigns/${id}/runs`);
      setActiveRunId(created.run_id);
    } catch (err) {
      // "Out of searches" is explained by the notice below, not an error line.
      setRunError(err.code === "NO_CREDITS" ? null : err.message);
    } finally {
      setStarting(false);
      refreshProfile(); // the count has changed (or was out of date)
    }
  }

  function replaceInfluencer(updated) {
    setInfluencers((list) => list.map((i) => (i.id === updated.id ? updated : i)));
  }

  // Highest-scored creators first; unreviewed ones last.
  const sortedInfluencers = useMemo(() => {
    if (!influencers) return null;
    return [...influencers].sort(
      (a, b) =>
        (normalizeScore(b.review_score) ?? -1) - (normalizeScore(a.review_score) ?? -1)
    );
  }, [influencers]);

  const showSkeleton = sortedInfluencers && sortedInfluencers.length === 0 && working;

  return (
    <div style={{ maxWidth: "52rem" }}>
      <p style={{ marginBottom: "var(--space-3)" }}>
        <Link to="/campaigns" className="muted" style={{ fontSize: "0.88rem" }}>
          ← All campaigns
        </Link>
      </p>

      {error && <p className="error-text">{error}</p>}
      {!campaign && !error && <p className="muted">Loading…</p>}

      {campaign && (
        <>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "baseline",
              gap: "var(--space-3)",
            }}
          >
            <h2>{campaign.name}</h2>
            <span className="status-pill">{campaign.status}</span>
          </div>

          {campaign.description && (
            <p className="muted" style={{ marginTop: "var(--space-2)" }}>
              {campaign.description}
            </p>
          )}

          <p className="muted" style={{ fontSize: "0.88rem", marginTop: "var(--space-2)" }}>
            {campaign.category} · {campaign.target_country} · {campaign.platform} ·{" "}
            {formatFollowers(campaign.min_followers)}–{formatFollowers(campaign.max_followers)}{" "}
            followers
          </p>

          <hr className="hairline" />

          <section>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "baseline",
                marginBottom: "var(--space-2)",
              }}
            >
              <h3>Pipeline</h3>
              <button className="btn" onClick={startRun} disabled={runDisabled}>
                {working && <span className="spinner" aria-hidden="true" />}
                {working
                  ? "Running…"
                  : outOfSearches
                  ? "No searches left"
                  : run
                  ? "Run again"
                  : "Run pipeline"}
              </button>
            </div>

            {credits != null && credits > 0 && (
              <p className="muted" style={{ fontSize: "0.85rem", marginBottom: "var(--space-3)" }}>
                {searchesLabel(credits)} left. Each run uses one; a run that fails or finds no creators doesn't.
              </p>
            )}

            {runError && (
              <p className="error-text" role="alert" style={{ marginBottom: "var(--space-2)" }}>
                {runError}
              </p>
            )}
            {pollError && !run && (
              <p className="error-text" role="alert" style={{ marginBottom: "var(--space-2)" }}>
                {pollError}
              </p>
            )}

            {outOfSearches && !working && (
              <div style={{ marginBottom: "var(--space-3)" }}>
                <UpgradeNotice />
              </div>
            )}

            <RunProgress run={run} timedOut={timedOut} />
            {!activeRunId && !starting && !outOfSearches && (
              <p className="muted">
                Discovers creators matching this campaign, reviews them, and drafts
                an outreach email for each. Nothing is ever sent automatically.
              </p>
            )}
          </section>

          <hr className="hairline" />

          <section>
            <h3 style={{ marginBottom: "var(--space-1)" }}>
              Creators{sortedInfluencers ? ` (${sortedInfluencers.length})` : ""}
            </h3>
            <p className="muted" style={{ fontSize: "0.82rem", marginBottom: "var(--space-3)" }}>
              Found in public search results, not by visiting Instagram. Follower counts
              can be out of date, so check each profile before reaching out.
            </p>

            {showSkeleton && (
              <ul style={{ listStyle: "none", margin: 0, padding: 0 }} aria-hidden="true">
                {[0, 1, 2].map((n) => (
                  <li key={n} className="influencer-entry">
                    <div>
                      <div className="skeleton" style={{ height: "1.2rem", width: "11rem" }} />
                      <div
                        className="skeleton"
                        style={{ height: "0.8rem", width: "20rem", marginTop: "0.6rem" }}
                      />
                    </div>
                    <div className="skeleton" style={{ height: "2rem", width: "3rem" }} />
                  </li>
                ))}
              </ul>
            )}

            {sortedInfluencers && sortedInfluencers.length === 0 && !working && (
              <p className="muted">
                No creators yet. Run the pipeline to discover creators for this
                campaign.
              </p>
            )}

            {sortedInfluencers && sortedInfluencers.length > 0 && (
              <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                {sortedInfluencers.map((inf) => (
                  <InfluencerCard
                    key={inf.id}
                    influencer={inf}
                    onUpdated={replaceInfluencer}
                    gmail={gmailStatus}
                  />
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}