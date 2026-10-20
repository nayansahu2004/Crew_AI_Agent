// File path: frontend/src/components/GuideContent.jsx
//
// The step-by-step guide and FAQ. Shown on the public "How it works" page
// and again inside the app (signedIn=true, which drops the "create an
// account" step and adds jump links).

import { Link } from "react-router-dom";
import { searchesLabel, siteConfig } from "../lib/siteConfig";
import "../styles/public.css";

const STEPS = [
  {
    id: "account",
    title: "Create your account",
    where: "Create account, at the top right of this page",
    text: "Enter your name, job title, company and phone number, then your email and a password. Those details sign your outreach emails. You may be asked to confirm your email: follow the link in your inbox, then sign in.",
  },
  {
    id: "gmail",
    title: "Connect your Gmail",
    where: "Settings → Gmail → Connect Gmail",
    link: { to: "/settings", label: "Go to Settings" },
    text: "Choose the Google account your outreach should come from and approve it on Google's own page. This is what lets Crew save drafts and send emails for you. Crew offers it right after you first sign in; you can skip it and connect later, but you'll need it before you can save or send. You can disconnect at any time.",
  },
  {
    id: "campaign",
    title: "Create a campaign",
    where: "Campaigns → New campaign",
    link: { to: "/campaigns/new", label: "New campaign" },
    text: "Name it and describe who you're looking for: a category (for example, \"fitness and wellness\"), a target country, and a follower range. The more specific the category, the closer the matches. A narrower follower range gives a more focused list.",
  },
  {
    id: "run",
    title: "Run the pipeline",
    where: "Open your campaign → Run pipeline",
    link: { to: "/campaigns", label: "Your campaigns" },
    text: "Crew searches the web for matching creators, reviews each one against your brief, and drafts a first email for each. It usually takes less than a minute, and keeps working on the server if you close the tab. Each run uses one of your free searches; if a run fails or finds no creators, the search isn't used.",
  },
  {
    id: "review",
    title: "Review the creators",
    where: "Inside the campaign, under Creators",
    text: "Creators are listed best match first, each with a score out of 10 and a short reason. Use Open on Instagram to look at the profile yourself. The score is a simple formula (does the follower count fit, do their profile words match your category, and how much was found), so treat it as a starting order rather than a verdict.",
  },
  {
    id: "send",
    title: "Add an email address, then send",
    where: "On each creator → Save email → Save to Gmail drafts or Send email",
    text: "Type the creator's email address and click Save email. Then either save the draft to Gmail to polish it there, or click Send email and confirm. Sent emails show who they went to and when. If you sent one yourself, outside Crew, use Mark as sent.",
  },
];

const QUESTIONS = [
  {
    q: "How much does Crew cost?",
    a: `Every new account gets ${searchesLabel(siteConfig.freeSearches)}, and no card is needed. A search is one run of the pipeline on a campaign, so running a campaign again uses another one, and a run that fails or finds no creators doesn't use one. After that, get in touch with ${siteConfig.owner.name} to keep going.`,
    link: { to: "/contact", label: "Contact details" },
  },
  {
    q: "Does Crew send emails on its own?",
    a: "No. Crew only drafts them. An email goes out only when you press Send on that one creator and confirm.",
  },
  {
    q: "Where do the creators' email addresses come from?",
    a: "Crew finds Instagram handles, not email addresses. Check the creator's profile for a business contact and type it in yourself.",
  },
  {
    q: "Can I trust the creators it finds?",
    a: "Treat the list as a head start. Creators are found from public search results, not by visiting Instagram, so a follower count can be out of date and some creators will be missing. Check each profile before you reach out.",
  },
  {
    q: "Does Crew get my Gmail password?",
    a: "No. You sign in on Google's own page. Crew keeps a permission that you can revoke, stored encrypted, and uses it only to save drafts and send the emails you choose. It doesn't read your inbox. Disconnect in Settings, or remove Crew at myaccount.google.com/permissions.",
  },
  {
    q: "Who can see my campaigns?",
    a: "Only you. Your campaigns, creators and emails are private to your account.",
  },
  {
    q: "A run failed. What do I do?",
    a: "The message says why. For example, the search service may be out of credits or briefly unavailable. Wait a few minutes and click Run again. A run that fails doesn't use up one of your searches.",
  },
  {
    q: "How do I change the name or company on my emails?",
    a: "Settings → Your details. New emails use the updated details. Emails already drafted keep the old ones until you run the campaign again.",
  },
];

export function GuideContent({ signedIn = false }) {
  const steps = STEPS.filter((step) => !(signedIn && step.id === "account"));

  return (
    <>
      <section className="pub-section" aria-labelledby="guide-steps">
        <h2 id="guide-steps">Step by step</h2>
        <ol className="pub-numbered">
          {steps.map((step, index) => (
            <li key={step.id}>
              <span className="pub-num" aria-hidden="true">
                {String(index + 1).padStart(2, "0")}
              </span>
              <div>
                <h3>{step.title}</h3>
                <p style={{ marginTop: "0.3rem" }}>{step.text}</p>
                <p className="pub-where">Where: {step.where}</p>
                {signedIn && step.link && (
                  <p style={{ marginTop: "0.3rem", fontSize: "0.9rem" }}>
                    <Link to={step.link.to}>{step.link.label} →</Link>
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="pub-section" aria-labelledby="guide-faq">
        <h2 id="guide-faq">Common questions</h2>
        <div className="pub-faq">
          {QUESTIONS.map((item) => (
            <details key={item.q}>
              <summary>{item.q}</summary>
              <p>{item.a}</p>
              {item.link && (
                <p style={{ marginTop: "0.3rem" }}>
                  <Link to={item.link.to}>{item.link.label} →</Link>
                </p>
              )}
            </details>
          ))}
        </div>
      </section>
    </>
  );
}