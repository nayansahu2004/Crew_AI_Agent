// File path: frontend/src/pages/SignIn.jsx
import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { AuthLayout } from "../components/AuthLayout";
import { friendlyAuthError } from "../lib/authErrors";

export function SignIn() {
  const { session, signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  if (session) {
    return <Navigate to="/campaigns" replace />;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    const { error } = await signIn(email, password);

    setSubmitting(false);
    if (error) {
      setError(friendlyAuthError(error));
      return;
    }
    navigate("/campaigns");
  }

  return (
    <AuthLayout
      title="Sign in"
      footer={
        <>
          Don't have an account? <Link to="/sign-up">Sign up</Link>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && <p className="error-text" role="alert" style={{ marginBottom: "var(--space-3)" }}>{error}</p>}

        <button className="btn" type="submit" disabled={submitting} style={{ width: "100%" }}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </AuthLayout>
  );
}