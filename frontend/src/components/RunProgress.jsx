// File path: frontend/src/components/RunProgress.jsx
import { useEffect, useState } from "react";
import { formatElapsed, parseUtc } from "../lib/format";
import "../styles/campaign.css";

const STAGES = [
  { key: "discovery", label: "Discovery" },
  { key: "review", label: "Review" },
  { key: "outreach", label: "Outreach" },
];

function stageState(run, index) {
  if (run.status === "completed") return "done";
  const current = STAGES.findIndex((s) => s.key === run.current_stage);
  if (run.status === "queued" || current === -1) return "pending";
  if (index < current) return "done";
  if (index === current) return run.status === "failed" ? "failed" : "active";
  return "pending";
}

// Seconds since the run started, ticking once a second while `active`.
function useElapsedSeconds(startedAt, active) {
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!active) return undefined;
    setNow(Date.now());
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active]);

  const start = parseUtc(startedAt);
  if (!start) return null;
  // Clamped: the browser's clock can be slightly behind the server's.
  return Math.max(0, Math.floor((now - start.getTime()) / 1000));
}

export function RunProgress({ run, timedOut }) {
  const active = Boolean(run) && ["queued", "running"].includes(run.status) && !timedOut;
  const elapsed = useElapsedSeconds(run?.started_at, active);

  if (!run) return null;

  const summary = run.result_summary || {};
  const start = parseUtc(run.started_at);
  const end = parseUtc(run.completed_at);
  const duration =
    start && end ? Math.max(0, Math.round((end - start) / 1000)) : null;

  return (
    <div>
      <ol className="run-steps">
        {STAGES.map((stage, i) => (
          <li key={stage.key} className="run-step" data-state={stageState(run, i)}>
            <span className="run-step-num">0{i + 1}</span>
            {stage.label}
          </li>
        ))}
      </ol>

      {/* Indeterminate bar: the pipeline reports no percentage, so this
          just shows that work is in progress. */}
      {active && <div className="run-track" aria-hidden="true" />}

      {run.status === "queued" && !timedOut && (
        <p className="muted" role="status">
          Queued — waiting to start.
        </p>
      )}

      {run.status === "running" && !timedOut && (
        <p className="muted" role="status">
          Running{elapsed != null ? ` — ${formatElapsed(elapsed)} elapsed` : ""}. This usually
          takes less than a minute.
        </p>
      )}

      {timedOut && (
        <p className="error-text" role="alert">
          This run is taking much longer than expected, so live updates have
          stopped. Refresh the page to check its latest status.
        </p>
      )}

      {run.status === "completed" && (summary.discovered_count ?? 0) === 0 && (
        <p className="muted" role="status">
          No creators matched this time, so this search wasn't used. Try broader category
          words or a wider follower range.
        </p>
      )}

      {run.status === "completed" && (summary.discovered_count ?? 0) > 0 && (
        <p className="muted">
          Found {summary.discovered_count ?? 0} creators · reviewed{" "}
          {summary.reviewed_count ?? 0} · {summary.emails_drafted ?? 0} email drafts
          ready{duration != null ? ` · finished in ${formatElapsed(duration)}` : ""}.
        </p>
      )}

      {run.status === "failed" && (
        <div role="alert">
          <p className="error-text">
            <strong>This run couldn't finish.</strong>
          </p>
          <p className="error-text">{run.error || "Something went wrong."}</p>
          <p className="muted" style={{ fontSize: "0.82rem", marginTop: "0.25rem" }}>
            Technical details are in the server logs.
          </p>
        </div>
      )}
    </div>
  );
}