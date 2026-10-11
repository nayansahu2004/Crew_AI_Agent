// File path: frontend/src/pages/CampaignCreate.jsx
//
// Form matching the backend's CampaignCreate schema exactly:
// name, description, category, target_country, min_followers,
// max_followers, platform. user_id is never sent -- the backend always
// derives it from the verified token.

import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../lib/apiClient";

export function CampaignCreate() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    name: "",
    description: "",
    category: "",
    target_country: "",
    min_followers: 20000,
    max_followers: 500000,
    platform: "instagram",
  });
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (Number(form.min_followers) > Number(form.max_followers)) {
      setError("Minimum followers can't be greater than maximum followers.");
      return;
    }

    setSubmitting(true);
    try {
      const created = await api.post("/api/campaigns", {
        ...form,
        description: form.description || null,
        min_followers: Number(form.min_followers),
        max_followers: Number(form.max_followers),
      });
      navigate(`/campaigns/${created.id}`);
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  }

  return (
    <div style={{ maxWidth: "34rem" }}>
      <p style={{ marginBottom: "var(--space-3)" }}>
        <Link to="/" className="muted" style={{ fontSize: "0.88rem" }}>
          ← All campaigns
        </Link>
      </p>

      <h2 style={{ marginBottom: "var(--space-4)" }}>New campaign</h2>

      <form onSubmit={handleSubmit}>
        <div className="field">
          <label htmlFor="name">Campaign name</label>
          <input
            id="name"
            required
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="description">Description (optional)</label>
          <textarea
            id="description"
            value={form.description}
            onChange={(e) => update("description", e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="category">Category</label>
          <input
            id="category"
            required
            placeholder="e.g. fashion and beauty"
            value={form.category}
            onChange={(e) => update("category", e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="target_country">Target country</label>
          <input
            id="target_country"
            required
            placeholder="e.g. India"
            value={form.target_country}
            onChange={(e) => update("target_country", e.target.value)}
          />
        </div>

        <div className="field">
          <label htmlFor="platform">Platform</label>
          <select
            id="platform"
            value={form.platform}
            onChange={(e) => update("platform", e.target.value)}
          >
            <option value="instagram">Instagram</option>
          </select>
        </div>

        <div style={{ display: "flex", gap: "var(--space-3)" }}>
          <div className="field" style={{ flex: 1 }}>
            <label htmlFor="min_followers">Min followers</label>
            <input
              id="min_followers"
              type="number"
              min="1"
              required
              value={form.min_followers}
              onChange={(e) => update("min_followers", e.target.value)}
            />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label htmlFor="max_followers">Max followers</label>
            <input
              id="max_followers"
              type="number"
              min="1"
              required
              value={form.max_followers}
              onChange={(e) => update("max_followers", e.target.value)}
            />
          </div>
        </div>

        {error && (
          <p className="error-text" style={{ marginBottom: "var(--space-3)" }}>
            {error}
          </p>
        )}

        <button className="btn" type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create campaign"}
        </button>
      </form>
    </div>
  );
}