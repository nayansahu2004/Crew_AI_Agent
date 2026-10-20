// File path: frontend/src/components/PublicLayout.jsx
//
// Header + footer for pages anyone can see (front page, How it works,
// Contact, not-found). The header adapts: signed-out visitors get Sign in /
// Create account, signed-in users get a link straight back into the app.
// The footer names who runs the site.

import { Link, NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { siteConfig } from "../lib/siteConfig";
import "../styles/public.css";

export function PublicLayout({ children }) {
  const { session, loading } = useAuth();
  const { owner } = siteConfig;

  return (
    <div className="public">
      <a className="skip-link" href="#main">
        Skip to content
      </a>

      <header className="public-header">
        <Link to="/" className="wordmark">
          {siteConfig.name}
        </Link>
        <nav aria-label="Main">
          <NavLink to="/how-it-works">How it works</NavLink>
          <NavLink to="/contact">Contact</NavLink>
          {/* Nothing here until we know whether they're signed in, so the
              buttons don't flash the wrong way. */}
          {!loading &&
            (session ? (
              <Link to="/campaigns" className="btn">
                Open app
              </Link>
            ) : (
              <>
                <Link to="/sign-in">Sign in</Link>
                <Link to="/sign-up" className="btn">
                  Create account
                </Link>
              </>
            ))}
        </nav>
      </header>

      <main id="main" className="public-main">
        {children}
      </main>

      <footer className="public-footer">
        <span>
          © {new Date().getFullYear()} {siteConfig.name}. Built and run by{" "}
          <Link to="/contact">{owner.name}</Link>, {owner.title}, {owner.company}.
        </span>
        <span>
          <Link to="/how-it-works">How it works</Link> · <Link to="/contact">Contact</Link>
        </span>
      </footer>
    </div>
  );
}