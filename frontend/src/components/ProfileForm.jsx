// File path: frontend/src/components/ProfileForm.jsx
//
// The four details used to sign outreach emails. Shared by the
// first-sign-in modal and the Settings page.

import { useState } from "react";
import { api } from "../lib/apiClient";
import { cleanProfile, validateProfile } from "../lib/validation";
import { Field } from "./Field";

export function ProfileForm({ initialValues, submitLabel, onSaved, onEdit }) {
  const [values, setValues] = useState({
    name: initialValues?.name ?? "",
    job_title: initialValues?.job_title ?? "",
    company_name: initialValues?.company_name ?? "",
    phone: initialValues?.phone ?? "",
  });
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState(null);
  const [saving, setSaving] = useState(false);

  function update(field, value) {
    setValues((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }));
    onEdit?.();
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitError(null);

    const found = validateProfile(values);
    setErrors(found);
    if (Object.keys(found).length > 0) return;

    setSaving(true);
    try {
      const saved = await api.post("/api/users/me", cleanProfile(values));
      onSaved(saved);
    } catch (err) {
      setSubmitError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
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
        value={values.phone}
        error={errors.phone}
        onChange={(e) => update("phone", e.target.value)}
      />

      {submitError && (
        <p className="error-text" role="alert" style={{ marginBottom: "var(--space-3)" }}>
          {submitError}
        </p>
      )}

      <button className="btn" type="submit" disabled={saving}>
        {saving ? "Saving…" : submitLabel}
      </button>
    </form>
  );
}