// File path: frontend/src/lib/siteConfig.js
//
// The one place that says who runs this site and how to reach them. Edit it
// here and every page (footer, contact page, "out of searches" notice)
// follows. vite.config.js keeps its own copy of the owner's name/role for
// the search-engine data -- keep the two in step.

const rawFreeSearches = import.meta.env.VITE_FREE_SEARCHES;

export const siteConfig = {
  name: "Crew",                          // short name: the header wordmark
  fullName: "Crew - Search influencers for Advertisement", // titles, link previews, search engines
  // The public address of the deployed site, e.g. https://crew.example.com
  // (no trailing slash). Used for canonical links; empty during development.
  siteUrl: (import.meta.env.VITE_SITE_URL || "").replace(/\/$/, ""),
  // How many free searches a new account gets. Keep in step with the
  // backend's FREE_RUNS_FOR_NEW_USERS -- this only controls the wording.
  freeSearches: rawFreeSearches === undefined || rawFreeSearches === "" ? 2 : Number(rawFreeSearches),
  owner: {
    name: "Nayan Kumar Sahu",
    title: "Founder | Talent Director",
    company: "Arista Management",
    email: "n4nayans4sahu@gmail.com",
    phone: "+91 72055 40108",
  },
};

export const phoneHref = (phone) => `tel:${phone.replace(/[^\d+]/g, "")}`;

export function mailtoHref(subject, body) {
  const params = new URLSearchParams({ subject, body }).toString().replace(/\+/g, "%20");
  return `mailto:${siteConfig.owner.email}?${params}`;
}

export function searchesLabel(count) {
  return `${count} free search${count === 1 ? "" : "es"}`;
}