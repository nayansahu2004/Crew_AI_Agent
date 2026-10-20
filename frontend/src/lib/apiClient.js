// File path: frontend/src/lib/apiClient.js
//
// Thin wrapper around fetch() that talks to the FastAPI backend: adds
// the base URL, attaches the current Supabase access token as a Bearer
// header, and turns failures into Errors with a message a person can
// act on (not "Failed to fetch" or a raw status code).

import { supabase } from "./supabaseClient";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

function friendlyMessage(status, backendMessage) {
  if (status === 401) return "Your session has expired. Please sign in again.";
  if (status === 429) return "Too many requests. Please wait a moment and try again.";
  if (status >= 500) return "Something went wrong on the server. Please try again in a moment.";
  return backendMessage || `Request failed (${status}).`;
}

function apiError(message, status, code) {
  const error = new Error(message);
  error.status = status;
  error.code = code;
  return error;
}

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

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    // fetch() only rejects when the request never got an answer: server
    // down, offline, or blocked by CORS. status 0 marks it as retryable.
    throw apiError(
      "Can't reach the server. Check that the backend is running and that you're online.",
      0,
      "NETWORK_ERROR"
    );
  }

  // 204 No Content (e.g. DELETE) has no body to parse.
  if (response.status === 204) {
    return null;
  }

  const body = await response.json().catch(() => null);

  if (!response.ok) {
    throw apiError(
      friendlyMessage(response.status, body?.error?.message),
      response.status,
      body?.error?.code
    );
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