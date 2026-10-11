// File path: frontend/src/lib/apiClient.js
//
// Thin wrapper around fetch() that talks to the FastAPI backend: adds
// the base URL, attaches the current Supabase access token as a Bearer
// header, and normalizes the backend's error shape
// ({success: false, error: {code, message}}) into a thrown Error.

import { supabase } from "./supabaseClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

async function request(path, options = {}) {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
  });

  // 204 No Content (e.g. DELETE) has no body to parse.
  if (response.status === 204) {
    return null;
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    const message = body?.error?.message || `Request failed (${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    error.code = body?.error?.code;
    throw error;
  }

  return body;
}

export const api = {
  get: (path) => request(path, { method: "GET" }),
  post: (path, data) =>
    request(path, { method: "POST", body: data ? JSON.stringify(data) : undefined }),
  patch: (path, data) =>
    request(path, { method: "PATCH", body: JSON.stringify(data) }),
  delete: (path) => request(path, { method: "DELETE" }),
};