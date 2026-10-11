// File path: frontend/src/hooks/useRunPolling.js
//
// Polls GET /api/runs/{runId} until the run finishes (completed/failed).
//
// - Never overlaps requests: the next poll is only scheduled after the
//   previous one returns.
// - Stops on unmount, on a run change, on a 4xx (retrying a 404/403
//   won't help), and after MAX_POLL_MS -- a run whose server restarted
//   mid-way stays "running" in the database forever, and the UI
//   shouldn't poll it forever too.
// - Calls onFinished only if it actually watched the run go from active
//   to finished, so opening a page for an already-completed run doesn't
//   trigger a pointless refetch.

import { useEffect, useRef, useState } from "react";
import { api } from "../lib/apiClient";

const POLL_MS = 3000;
const MAX_POLL_MS = 20 * 60 * 1000;
export const ACTIVE_STATUSES = new Set(["queued", "running"]);

export function useRunPolling(runId, onFinished) {
  const [run, setRun] = useState(null);
  const [error, setError] = useState(null);
  const [timedOut, setTimedOut] = useState(false);

  // Keep the latest callback without restarting the polling effect.
  const onFinishedRef = useRef(onFinished);
  onFinishedRef.current = onFinished;

  useEffect(() => {
    setRun(null);
    setError(null);
    setTimedOut(false);
    if (!runId) return undefined;

    let cancelled = false;
    let timer;
    let sawActive = false;
    const startedAt = Date.now();

    async function tick() {
      try {
        const data = await api.get(`/api/runs/${runId}`);
        if (cancelled) return;
        setRun(data);
        setError(null);

        if (ACTIVE_STATUSES.has(data.status)) {
          sawActive = true;
          if (Date.now() - startedAt > MAX_POLL_MS) {
            setTimedOut(true);
            return;
          }
          timer = setTimeout(tick, POLL_MS);
        } else if (sawActive) {
          onFinishedRef.current?.(data);
        }
      } catch (err) {
        if (cancelled) return;
        setError(err.message);
        // Retry transient failures (network, 5xx); give up on 4xx.
        if (!err.status || err.status >= 500) {
          timer = setTimeout(tick, POLL_MS * 2);
        }
      }
    }

    tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [runId]);

  return { run, error, timedOut };
}