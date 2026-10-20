// File path: frontend/src/pages/Landing.jsx
//
// The front page for signed-out visitors. Written for people AND for
// search engines: the words someone would actually search for (influencer
// outreach, find Instagram influencers, influencer campaign, outreach
// emails) appear where they naturally belong -- title, main heading,
// section headings and body copy -- rather than being stuffed in.
//
// Signed-in users never see this: the home route sends them to /campaigns.

import { Link } from "react-router-dom";
import { PublicLayout } from "../components/PublicLayout";
import { Seo } from "../components/Seo";
import { searchesLabel, siteConfig } from "../lib/siteConfig";
import "../styles/public.css";

const WHAT_IT_DOES = [
  {
    title: "Influencer discovery",
    text: "Tell Crew the category, country and follower range your campaign needs. It searches the web and lists Instagram influencers who fit.",
  },
  {
    title: "Review and scoring",
    text: "Each creator gets a score out of 10 and a one-line reason (follower fit, category match, and how much was found), so the strongest matches for your influencer campaign rise to the top.",
  },
  {
    title: "Outreach emails",
    text: "Every creator gets a drafted first email, signed with your name and company. Save it to your Gmail drafts or send it, one creator at a time, after you confirm.",
  },
];

const WHO_FOR = [
  "Influencer marketing agencies building creator lists for clients.",
  "Brand and marketing teams who run their own influencer outreach.",
  "Talent managers and PR consultants who want a faster first pass.",
];

export function Landing() {
  const { owner, freeSearches } = siteConfig;

  const goodToKnow = [
    "Creators are found in public search results, not by visiting Instagram, so some will be missing and follower counts can be out of date. Check each profile before you reach out.",
    "Crew finds handles, not email addresses. You add each creator's address yourself.",
    "Nothing is sent automatically. An email goes out only when you press Send on it and confirm.",
    "Instagram only, for now.",
    "Your campaigns, creators and emails are private to your account.",
    `Every new account gets ${searchesLabel(freeSearches)}, and no card is needed. A search is one run of the pipeline, and a run that fails or finds no creators doesn't use one. After that, get in touch with ${owner.name} to continue.`,
  ];

  return (
    <PublicLayout>
      <Seo
        title={`${siteConfig.fullName} | Outreach Tool`}
        description={`Find Instagram influencers for your campaign, score them against your brief, and draft outreach emails to send from your Gmail. ${searchesLabel(freeSearches)} to start.`}
        path="/"
      />

      <section className="hero" aria-labelledby="hero-title">
        <h1 id="hero-title">Find Instagram influencers and draft your outreach, in one place.</h1>
        <p className="hero-lede">
          Crew is an influencer outreach tool for agencies, brands and talent managers. Describe
          the creators your campaign needs. Crew searches for matching Instagram influencers,
          scores each one against your brief, and drafts a personal outreach email that you can
          review, save to Gmail, and send.
        </p>
        <div className="hero-actions">
          <Link to="/sign-up" className="btn">
            Create account
          </Link>
          <Link to="/how-it-works">See how it works</Link>
        </div>
        <p className="hero-note">
          {searchesLabel(freeSearches)} for every new account, and no card needed. Already have an
          account? <Link to="/sign-in">Sign in</Link>
        </p>
      </section>

      <section className="pub-section" aria-labelledby="what-title">
        <h2 id="what-title">What Crew does</h2>
        <ol className="pub-numbered">
          {WHAT_IT_DOES.map((item, index) => (
            <li key={item.title}>
              <span className="pub-num" aria-hidden="true">
                0{index + 1}
              </span>
              <div>
                <h3>{item.title}</h3>
                <p style={{ marginTop: "0.3rem" }}>{item.text}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="pub-section" aria-labelledby="who-title">
        <h2 id="who-title">Who it's for</h2>
        <div>
          <ul className="pub-list">
            {WHO_FOR.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          <p className="muted" style={{ marginTop: "var(--space-3)" }}>
            If you spend hours finding influencers and writing the same first email, that
            repetitive first pass is the part Crew takes over.
          </p>
        </div>
      </section>

      <section className="pub-section" aria-labelledby="know-title">
        <h2 id="know-title">Good to know</h2>
        <ul className="pub-list">
          {goodToKnow.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </section>

      <section className="pub-section" aria-labelledby="owner-title">
        <h2 id="owner-title">Who runs Crew</h2>
        <div>
          <p>
            Crew is built and run by <strong>{owner.name}</strong>, {owner.title} at{" "}
            {owner.company}.
          </p>
          <p style={{ marginTop: "var(--space-2)" }}>
            Questions, feedback, or want more searches?{" "}
            <Link to="/contact">Get in touch</Link>.
          </p>
        </div>
      </section>

      <section className="pub-cta" aria-labelledby="cta-title">
        <h2 id="cta-title" style={{ marginBottom: "var(--space-3)" }}>
          Ready to find your next creators?
        </h2>
        <div className="hero-actions" style={{ marginTop: 0 }}>
          <Link to="/sign-up" className="btn">
            Create account
          </Link>
          <Link to="/how-it-works">Read the step-by-step guide</Link>
        </div>
      </section>
    </PublicLayout>
  );
}