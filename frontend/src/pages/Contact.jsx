// File path: frontend/src/pages/Contact.jsx
import { PublicLayout } from "../components/PublicLayout";
import { Seo } from "../components/Seo";
import { mailtoHref, phoneHref, searchesLabel, siteConfig } from "../lib/siteConfig";
import "../styles/public.css";

export function Contact() {
  const { owner } = siteConfig;

  return (
    <PublicLayout>
      <Seo
        title={`Contact ${owner.name} | Crew`}
        description={`Get in touch with ${owner.name}, ${owner.title} at ${owner.company}, about Crew: more searches, questions or feedback.`}
        path="/contact"
      />

      <h1 style={{ fontSize: "clamp(2rem, 5vw, 3rem)" }}>Get in touch</h1>
      <p className="hero-lede">
        Crew is built and run by {owner.name}, {owner.title} at {owner.company}.
        Write or call about more searches, a question, or feedback.
      </p>

      <section className="pub-section" aria-labelledby="contact-details">
        <h2 id="contact-details">Contact details</h2>
        <dl className="contact-details">
          <dt>Name</dt>
          <dd>{owner.name}</dd>
          <dt>Role</dt>
          <dd>
            {owner.title}, {owner.company}
          </dd>
          <dt>Email</dt>
          <dd>
            <a href={mailtoHref("Crew", "")}>{owner.email}</a>
          </dd>
          <dt>Phone</dt>
          <dd>
            <a href={phoneHref(owner.phone)}>{owner.phone}</a>
          </dd>
        </dl>
      </section>

      <section className="pub-section" aria-labelledby="contact-searches">
        <h2 id="contact-searches">Need more searches?</h2>
        <p>
          Every new account starts with {searchesLabel(siteConfig.freeSearches)}. A search is one
          run of the pipeline on a campaign. When you've used them, get in
          touch and mention the email you signed up with.
        </p>
      </section>
    </PublicLayout>
  );
}