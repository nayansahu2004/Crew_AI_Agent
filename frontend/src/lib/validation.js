// File path: frontend/src/lib/validation.js
//
// Mirrors the backend's rules for the profile details (the backend is
// still the authority -- this just gives instant feedback).

// Optional +, then digits with spaces/dashes/brackets: "+91 98765 43210"
export const PHONE_PATTERN = /^\+?[0-9][0-9\s\-()]{6,19}$/;

const tidy = (value) => (value ?? "").trim().replace(/\s+/g, " ");

export function cleanProfile(values) {
  return {
    name: tidy(values.name),
    job_title: tidy(values.job_title),
    company_name: tidy(values.company_name),
    phone: tidy(values.phone),
  };
}

// Returns an object of field -> message; empty means valid.
export function validateProfile(values) {
  const v = cleanProfile(values);
  const errors = {};
  if (v.name.length < 2) errors.name = "Enter your full name.";
  if (v.job_title.length < 2) errors.job_title = "Enter your job title.";
  if (v.company_name.length < 2) errors.company_name = "Enter your company name.";
  if (!PHONE_PATTERN.test(v.phone)) {
    errors.phone = "Enter a valid phone number, e.g. +91 98765 43210.";
  }
  return errors;
}

// Sign-up stores the details in the Supabase user's metadata (the user
// has no session yet if email confirmation is on). This reads them back
// out; returns null unless every field is present and valid.
export function profileFromMetadata(metadata) {
  if (!metadata) return null;
  const candidate = cleanProfile({
    name: metadata.full_name,
    job_title: metadata.job_title,
    company_name: metadata.company_name,
    phone: metadata.phone,
  });
  return Object.keys(validateProfile(candidate)).length === 0 ? candidate : null;
}