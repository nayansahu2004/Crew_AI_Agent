// File path: frontend/src/pages/Settings.jsx
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useGmailStatus } from "../hooks/useGmailStatus";
import { GmailConnectCard } from "../components/GmailConnectCard";
import { ProfileForm } from "../components/ProfileForm";

// Why a Gmail connection can fail, in words (the backend sends a short code).
const GMAIL_ERRORS = {
  access_denied: "You cancelled on Google's page, so nothing was connected.",
  permission_denied:
    "Gmail needs permission to create drafts and send email. Please try again and tick every box on Google's page.",
  invalid_state: "That connection attempt expired. Please try again.",
  no_refresh_token:
    "Google didn't grant lasting access. Remove this app at myaccount.google.com/permissions, then connect again.",
  exchange_failed: "Google couldn't complete the connection. Please try again.",
  no_email: "Google didn't tell us which account this was. Please try again.",
};

export function Settings() {
  const { user, profile, setProfile } = useAuth();
  const [saved, setSaved] = useState(false);
  const [params] = useSearchParams();
  const { status: gmailStatus, reload: reloadGmail } = useGmailStatus();

  const gmailResult = params.get("gmail");
  const gmailReason = params.get("reason");

  return (
    <div style={{ maxWidth: "34rem" }}>
      <h2 style={{ marginBottom: "var(--space-2)" }}>Settings</h2>
      <p className="muted" style={{ marginBottom: "var(--space-4)" }}>
        Signed in as {user?.email}
      </p>

      <h3 style={{ marginBottom: "var(--space-1)" }}>Your details</h3>
      <p className="muted" style={{ fontSize: "0.88rem", marginBottom: "var(--space-3)" }}>
        These sign every outreach email drafted for you. Emails already
        drafted keep the details they were written with.
      </p>

      <ProfileForm
        initialValues={profile}
        submitLabel="Save changes"
        onEdit={() => setSaved(false)}
        onSaved={(updated) => {
          setProfile(updated);
          setSaved(true);
        }}
      />

      {saved && (
        <p role="status" style={{ marginTop: "var(--space-3)", color: "var(--moss)" }}>
          Saved.
        </p>
      )}

      <hr className="hairline" />

      <h3 style={{ marginBottom: "var(--space-2)" }}>Gmail</h3>

      {gmailResult === "connected" && (
        <p role="status" style={{ marginBottom: "var(--space-3)", color: "var(--moss)" }}>
          Gmail connected.
        </p>
      )}
      {gmailResult === "error" && (
        <p className="error-text" role="alert" style={{ marginBottom: "var(--space-3)" }}>
          {GMAIL_ERRORS[gmailReason] ?? "Couldn't connect Gmail. Please try again."}
        </p>
      )}

      <GmailConnectCard status={gmailStatus} onChanged={reloadGmail} />
    </div>
  );
}