// File path: frontend/src/pages/HowItWorks.jsx
//
// Two entry points for the same guide:
//   HowItWorks -- public page at /how-it-works, for new visitors
//   Guide      -- inside the app at /guide, with jump links to each place

import { Link } from "react-router-dom";
import { GuideContent } from "../components/GuideContent";
import { PublicLayout } from "../components/PublicLayout";
import { Seo } from "../components/Seo";
import "../styles/public.css";

export function HowItWorks() {
  return (
    <PublicLayout>
      <Seo
        title="How Crew works: from influencer search to outreach email"
        description="A step-by-step guide to finding Instagram influencers with Crew, reviewing them, and sending outreach emails from your own Gmail."
        path="/how-it-works"
      />
      <h1 style={{ maxWidth: "20ch", fontSize: "clamp(2rem, 5vw, 3rem)" }}>
        How to use Crew
      </h1>
      <p className="hero-lede">
        Six steps from a new account to a sent email. Most of the waiting is
        the search itself.
      </p>

      <GuideContent />

      <section className="pub-cta" aria-labelledby="how-cta">
        <h2 id="how-cta" style={{ marginBottom: "var(--space-3)" }}>
          Ready when you are
        </h2>
        <div className="hero-actions" style={{ marginTop: 0 }}>
          <Link to="/sign-up" className="btn">
            Create account
          </Link>
          <Link to="/sign-in">Sign in</Link>
        </div>
      </section>
    </PublicLayout>
  );
}

export function Guide() {
  return (
    <div style={{ maxWidth: "52rem" }}>
      <h2>How it works</h2>
      <p className="muted" style={{ marginTop: "var(--space-2)" }}>
        The steps from a new campaign to a sent email, and where to click for
        each.
      </p>
      <GuideContent signedIn />
    </div>
  );
}