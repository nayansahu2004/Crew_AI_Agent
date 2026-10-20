// File path: frontend/src/lib/authErrors.js
//
// Supabase's error messages are written for developers. This maps the
// common ones to something a person can act on; anything unrecognized
// falls through unchanged.

export function friendlyAuthError(error) {
  const message = error?.message ?? "";

  if (/rate limit|too many requests|over_email_send_rate_limit/i.test(message)) {
    return "Too many attempts. Please wait a few minutes and try again.";
  }
  if (/already registered|already exists/i.test(message)) {
    return "An account with this email already exists. Try signing in instead.";
  }
  if (/invalid login credentials/i.test(message)) {
    return "Incorrect email or password.";
  }
  if (/email not confirmed/i.test(message)) {
    return "Please confirm your email first — check your inbox for the link.";
  }
  if (/failed to fetch|network/i.test(message)) {
    return "Can't reach the sign-in service. Check your internet connection and try again.";
  }
  return message || "Something went wrong. Please try again.";
}