// File path: frontend/src/lib/format.js

export function formatFollowers(n) {
  if (n == null) return "—";
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1).replace(/\.0$/, "")}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1).replace(/\.0$/, "")}K`;
  return String(n);
}

// The backend stores review scores on a 0-10 scale. Influencers reviewed
// before that normalization existed may still hold a 0-100 value, so
// scale those down here rather than showing "85.0 / 10".
export function normalizeScore(score) {
  if (score == null) return null;
  return score > 10 ? score / 10 : score;
}

// The API sends timestamps as UTC but without a "Z" suffix, which
// JavaScript would read as LOCAL time -- shifting every elapsed-time
// calculation by the viewer's UTC offset. Treat zone-less values as UTC.
export function parseUtc(value) {
  if (!value) return null;
  const hasZone = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(value);
  return new Date(hasZone ? value : `${value}Z`);
}

export function formatElapsed(totalSeconds) {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${String(seconds).padStart(2, "0")}`;
}