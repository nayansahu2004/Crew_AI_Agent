// File path: frontend/src/hooks/useGmailStatus.js
//
// Whether this server has Gmail set up, and whether the signed-in user has
// connected an account. Pass enabled=false to hold off fetching.

import { useCallback, useEffect, useState } from "react";
import { api } from "../lib/apiClient";

export function useGmailStatus(enabled = true) {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  const reload = useCallback(async () => {
    try {
      setStatus(await api.get("/api/gmail/status"));
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    if (enabled) reload();
  }, [enabled, reload]);

  return { status, error, reload };
}