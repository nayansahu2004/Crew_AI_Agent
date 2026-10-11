// File path: frontend/src/components/AppShell.jsx
//
// The signed-in layout: a narrow sidebar + main content column, in the
// editorial-index style rather than a boxed dashboard. Every protected
// page renders inside this via <Outlet />.

import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export function AppShell() {
  const { user, signOut } = useAuth();

  return (
    <div style={{ display: "flex", minHeight: "100%" }}>
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
        <h1 style={{ fontSize: "1.3rem", marginBottom: "var(--space-5)" }}>
          Crew
        </h1>

        <nav style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}>
          <NavLink to="/" end style={navStyle}>
            Campaigns
          </NavLink>
        </nav>

        <div style={{ marginTop: "auto" }}>
          <hr className="hairline" style={{ margin: "var(--space-3) 0" }} />
          <p className="muted" style={{ fontSize: "0.82rem", marginBottom: "var(--space-2)" }}>
            {user?.email}
          </p>
          <button className="btn-secondary btn" onClick={signOut}>
            Sign out
          </button>
        </div>
      </aside>

      <main style={{ flex: 1, padding: "var(--space-5) var(--space-4)" }}>
        <Outlet />
      </main>
    </div>
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