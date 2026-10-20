// File path: frontend/src/pages/SignUp.jsx
import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AuthLayout } from "../components/AuthLayout";
import { Field } from "../components/Field";
import { friendlyAuthError } from "../lib/authErrors";
import { cleanProfile, validateProfile } from "../lib/validation";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function SignUp() {
  const { session, signUp } = useAuth();
  const [values, setValues] = useState({
    name: "",
    job_title: "",
    company_name: "",
    phone: "",
    email: "",
    password: "",
  });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  if (session) {
    return <Navigate to="/campaigns" replace />;
  }

  function update(field, value) {
    setValues((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setFormError(null);

    const found = validateProfile(values);
    if (!EMAIL_PATTERN.test(values.email.trim())) found.email = "Enter a valid email address.";
    if (values.password.length < 8) found.password = "Use at least 8 characters.";
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSubmitting(true);
    const { data, error } = await signUp(
      values.email.trim(),
      values.password,
      cleanProfile(values)
    );
    setSubmitting(false);

    if (error) {
      setFormError(friendlyAuthError(error));
      return;
    }

    // For an email that's already registered, Supabase answers "success"
    // with a user that has no identities (so it doesn't reveal which
    // emails have accounts) and sends no email. Say so, rather than
    // telling them to check an inbox that will stay empty.
    if (data?.user && Array.isArray(data.user.identities) && data.user.identities.length === 0) {
      setFormError("An account with this email already exists. Try signing in instead.");
      return;
    }

    setSubmitted(true);
  }

  if (submitted) {
    return (
      <AuthLayout title="Check your email">
        <p>
          We've sent a confirmation link to <strong>{values.email.trim()}</strong>.
          Follow it to activate your account, then sign in — your details are
          already saved with it.
        </p>
        <Link to="/sign-in" style={{ display: "inline-block", marginTop: "var(--space-3)" }}>
          Back to sign in
        </Link>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Create an account"
      footer={
        <>
          Already have an account? <Link to="/sign-in">Sign in</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} noValidate>
        <Field
          id="name"
          label="Full name"
          autoComplete="name"
          value={values.name}
          error={errors.name}
          onChange={(e) => update("name", e.target.value)}
        />
        <Field
          id="job_title"
          label="Job title"
          autoComplete="organization-title"
          placeholder="e.g. Founder | Talent Director"
          value={values.job_title}
          error={errors.job_title}
          onChange={(e) => update("job_title", e.target.value)}
        />
        <Field
          id="company_name"
          label="Company name"
          autoComplete="organization"
          value={values.company_name}
          error={errors.company_name}
          onChange={(e) => update("company_name", e.target.value)}
        />
        <Field
          id="phone"
          label="Phone number"
          type="tel"
          autoComplete="tel"
          placeholder="+91 98765 43210"
          hint="Used to sign your outreach emails."
          value={values.phone}
          error={errors.phone}
          onChange={(e) => update("phone", e.target.value)}
        />

        <hr className="hairline" style={{ margin: "var(--space-3) 0" }} />

        <Field
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          value={values.email}
          error={errors.email}
          onChange={(e) => update("email", e.target.value)}
        />
        <Field
          id="password"
          label="Password"
          type="password"
          autoComplete="new-password"
          value={values.password}
          error={errors.password}
          onChange={(e) => update("password", e.target.value)}
        />

        {formError && (
          <p className="error-text" role="alert" style={{ marginBottom: "var(--space-3)" }}>
            {formError}
          </p>
        )}

        <button className="btn" type="submit" disabled={submitting} style={{ width: "100%" }}>
          {submitting ? "Creating account…" : "Create account"}
        </button>
      </form>
    </AuthLayout>
  );
}