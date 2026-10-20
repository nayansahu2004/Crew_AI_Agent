// File path: frontend/src/components/UpgradeNotice.jsx
//
// Shown when an account has used its free searches. There's no payment
// system: it points people to the owner, with the email pre-filled.

import { useAuth } from "../context/AuthContext";
import { mailtoHref, phoneHref, searchesLabel, siteConfig } from "../lib/siteConfig";
import "../styles/public.css";

export function UpgradeNotice() {
  const { user } = useAuth();
  const { owner } = siteConfig;
  const asking = `Hi ${owner.name.split(" ")[0]}, I've used my free searches on Crew and I'd like more. My account email is ${user?.email ?? "(your email here)"}.`;

  return (
    <div className="notice" role="status">
      <h3>You've used your {searchesLabel(siteConfig.freeSearches)}</h3>
      <p style={{ marginTop: "0.3rem" }}>
        To keep going, get in touch with {owner.name} and ask for more
        searches. Mention the email you signed up with.
      </p>
      <ul className="contact-lines">
        <li>
          Email: <a href={mailtoHref("More searches on Crew", asking)}>{owner.email}</a>
        </li>
        <li>
          Phone: <a href={phoneHref(owner.phone)}>{owner.phone}</a>
        </li>
      </ul>
    </div>
  );
}