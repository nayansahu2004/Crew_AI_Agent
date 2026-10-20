// File path: frontend/src/components/OnboardingModal.jsx
//
// Shown over the app for anyone whose details are incomplete. Uses the
// native <dialog> element: it traps keyboard focus and makes everything
// behind it inert. Escape is blocked, so it can't be dismissed -- the
// details are needed to sign the outreach emails.

import { useEffect, useRef } from "react";
import { ProfileForm } from "./ProfileForm";
import "../styles/dialog.css";

export function OnboardingModal({ initialValues, onSaved }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => dialog?.close();
  }, []);

  return (
    <dialog
      ref={dialogRef}
      className="modal"
      aria-labelledby="onboarding-title"
      onCancel={(e) => e.preventDefault()}
    >
      <h2 id="onboarding-title" style={{ marginBottom: "var(--space-2)" }}>
        Welcome — one last step
      </h2>
      <p className="muted" style={{ marginBottom: "var(--space-4)" }}>
        Tell us who the outreach emails come from. These details sign every
        email we draft for you, and you can change them any time in Settings.
      </p>
      <ProfileForm
        initialValues={initialValues}
        submitLabel="Save and continue"
        onSaved={onSaved}
      />
    </dialog>
  );
}