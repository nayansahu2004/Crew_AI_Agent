// File path: frontend/src/pages/NotFound.jsx
import { Link } from "react-router-dom";
import { PublicLayout } from "../components/PublicLayout";
import { Seo } from "../components/Seo";
import { siteConfig } from "../lib/siteConfig";

export function NotFound() {
  return (
    <PublicLayout>
      <Seo title={`Page not found | ${siteConfig.name}`} noindex />
      <h1 style={{ marginBottom: "var(--space-2)" }}>Page not found</h1>
      <p className="muted" style={{ marginBottom: "var(--space-3)" }}>
        That page doesn't exist, or it has moved.
      </p>
      <Link to="/">Go to the home page</Link>
    </PublicLayout>
  );
}