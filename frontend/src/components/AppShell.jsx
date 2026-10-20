// File path: frontend/src/components/AppShell.jsx
//
// The signed-in layout: a narrow sidebar + main content column. Until
// the user's details are filled in, the main area shows the onboarding
// modal instead of the page.

import { useState } from "react";
import { Link, NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useGmailStatus } from "../hooks/useGmailStatus";
import { GmailPromptModal } from "./GmailPromptModal";
import { Seo } from "./Seo";
import { searchesLabel } from "../lib/siteConfig";
import { OnboardingModal } from "./OnboardingModal";

// localStorage can throw (private browsing, blocked storage) -- never let
// that break the app; worst case the prompt is simply asked again.
function readFlag(key) {
  try {
    return localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function writeFlag(key) {
  try {
    localStorage.setItem(key, "1");
  } catch {
    /* ignore */
  }
}

export function AppShell() {
  const { user, signOut, profile, setProfile, profileError, refreshProfile } = useAuth();

  // Offer to connect Gmail once, after the user's details are saved.
  const profileReady = Boolean(profile?.profile_complete);
  const { status: gmailStatus } = useGmailStatus(profileReady);
  const promptKey = `crew:gmail-prompt-seen:${user?.id}`;
  const [promptSeen, setPromptSeen] = useState(() => readFlag(promptKey));
  const showGmailPrompt =
    profileReady &&
    gmailStatus?.configured &&
    !gmailStatus.connected &&
    !gmailStatus.needs_reconnect &&
    !promptSeen;

  function dismissGmailPrompt() {
    writeFlag(promptKey);
    setPromptSeen(true);
  }

  return (
    <div style={{ display: "flex", minHeight: "100%" }}>
      <Seo title="Crew" noindex />
      <aside
        style={{
          width: "15rem",
          flexShrink: 0,
          borderRight: "1px solid var(--rule)",
          padding: "var(--space-4) var(--space-3)",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <h1 style={{ fontSize: "1.3rem", marginBottom: "var(--space-5)" }}>Crew</h1>

        <nav style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          <NavLink to="/campaigns" style={navStyle}>
            Campaigns
          </NavLink>
          <NavLink to="/settings" style={navStyle}>
            Settings
          </NavLink>
          <NavLink to="/guide" style={navStyle}>
            How it works
          </NavLink>
        </nav>

        <div style={{ marginTop: "auto" }}>
          <hr className="hairline" style={{ margin: "var(--space-3) 0" }} />
          <p className="muted" style={{ fontSize: "0.82rem", marginBottom: "var(--space-1)" }}>
            {profile?.name || user?.email}
          </p>
          {profile?.name && (
            <p className="muted" style={{ fontSize: "0.78rem", marginBottom: "var(--space-2)" }}>
              {user?.email}
            </p>
          )}
          <SearchesLeft credits={profile?.run_credits} />
          <button className="btn-secondary btn" onClick={signOut}>
            Sign out
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, padding: "var(--space-5) var(--space-4)" }}>
        {profileError ? (
          <div style={{ maxWidth: "30rem" }}>
            <h2 style={{ marginBottom: "var(--space-2)" }}>We couldn't load your account</h2>
            <p className="error-text" role="alert" style={{ marginBottom: "var(--space-3)" }}>
              {profileError}
            </p>
            <button className="btn" onClick={refreshProfile}>
              Try again
            </button>
          </div>
        ) : !profile ? (
          <p className="muted" role="status">
            Loading your account…
          </p>
        ) : !profile.profile_complete ? (
          <OnboardingModal initialValues={profile} onSaved={setProfile} />
        ) : (
          <>
            <Outlet />
            {showGmailPrompt && <GmailPromptModal onDismiss={dismissGmailPrompt} />}
          </>
        )}
      </main>
    </div>
  );
}

// Free searches left. Hidden for unlimited accounts (run_credits is null).
function SearchesLeft({ credits }) {
  if (credits == null) return null;
  return (
    <p style={{ fontSize: "0.82rem", marginBottom: "var(--space-2)" }}>
      {credits > 0 ? (
        <>
          <strong>{searchesLabel(credits)}</strong> left.{" "}
          <Link to="/contact">Need more?</Link>
        </>
      ) : (
        <>
          No free searches left. <Link to="/contact">Get in touch</Link> for more.
        </>
      )}
    </p>
  );
}

function navStyle({ isActive }) {
  return {
    textDecoration: "none",
    color: isActive ? "var(--berry)" : "var(--ink)",
    fontWeight: isActive ? 600 : 500,
    fontSize: "0.95rem",
  };
}