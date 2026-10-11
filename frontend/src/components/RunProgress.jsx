// File path: frontend/src/components/RunProgress.jsx
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

export function RunProgress({ run, timedOut }) {
  if (!run) return null;

  const summary = run.result_summary || {};

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

      {run.status === "queued" && <p className="muted">Queued — waiting to start.</p>}

      {run.status === "running" && !timedOut && (
        <p className="muted">Running. This can take several minutes.</p>
      )}

      {timedOut && (
        <p className="error-text">
          This run is taking much longer than expected, so live updates have
          stopped. Refresh the page to check its latest status.
        </p>
      )}

      {run.status === "completed" && (
        <p className="muted">
          Found {summary.discovered_count ?? 0} creators · reviewed{" "}
          {summary.reviewed_count ?? 0} · {summary.emails_drafted ?? 0} email
          drafts ready.
        </p>
      )}

      {run.status === "failed" && (
        <p className="error-text">Run failed: {run.error || "unknown error"}</p>
      )}
    </div>
  );
}