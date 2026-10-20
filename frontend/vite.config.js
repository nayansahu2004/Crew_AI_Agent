// File path: frontend/vite.config.js
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Who runs the site, for search engines. This file runs in Node and can't
// import src/lib/siteConfig.js, so keep these in step with it.
const SITE = {
  name: "Crew - Search influencers for Advertisement",
  alternateName: "Crew",
  description:
    "Find Instagram influencers for your campaign, score them against your brief, and draft outreach emails to send from your Gmail.",
  ownerName: "Nayan Kumar Sahu",
  ownerTitle: "Founder | Talent Director",
  ownerCompany: "Arista Management",
};

// Pages worth indexing, and pages search engines should stay out of.
const PUBLIC_PATHS = ["/", "/how-it-works", "/contact"];
const PRIVATE_PATHS = ["/campaigns", "/settings", "/guide", "/sign-in", "/sign-up"];

// At build time: writes robots.txt and sitemap.xml, and adds the canonical
// link plus structured data (JSON-LD) to index.html. The sitemap and
// canonical need the site's real address, so they only appear when
// VITE_SITE_URL is set.
function seoFiles(siteUrl) {
  return {
    name: "crew-seo-files",

    transformIndexHtml(html) {
      if (!siteUrl) return html;
      const structuredData = JSON.stringify({
        "@context": "https://schema.org",
        "@graph": [
          { "@type": "WebSite", name: SITE.name, alternateName: SITE.alternateName, url: `${siteUrl}/` },
          {
            "@type": "SoftwareApplication",
            name: SITE.name,
            alternateName: SITE.alternateName,
            url: `${siteUrl}/`,
            applicationCategory: "BusinessApplication",
            operatingSystem: "Web",
            description: SITE.description,
            author: {
              "@type": "Person",
              name: SITE.ownerName,
              jobTitle: SITE.ownerTitle,
              worksFor: { "@type": "Organization", name: SITE.ownerCompany },
            },
          },
        ],
      }).replace(/</g, "\\u003c"); // so the data can never close its own <script> tag

      const tags = [
        `<link rel="canonical" href="${siteUrl}/" />`,
        `<meta property="og:url" content="${siteUrl}/" />`,
        `<script type="application/ld+json">${structuredData}</script>`,
      ].join("\n    ");
      return html.replace("</head>", `  ${tags}\n  </head>`);
    },

    generateBundle() {
      const robots = ["User-agent: *", "Allow: /", ...PRIVATE_PATHS.map((p) => `Disallow: ${p}`)];
      if (siteUrl) robots.push("", `Sitemap: ${siteUrl}/sitemap.xml`);
      this.emitFile({ type: "asset", fileName: "robots.txt", source: robots.join("\n") + "\n" });

      if (!siteUrl) {
        this.warn("VITE_SITE_URL is not set: sitemap.xml and canonical links were skipped.");
        return;
      }
      const urls = PUBLIC_PATHS.map((p) => `  <url><loc>${siteUrl}${p === "/" ? "/" : p}</loc></url>`).join("\n");
      this.emitFile({
        type: "asset",
        fileName: "sitemap.xml",
        source: `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
      });
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "VITE_");
  const siteUrl = (env.VITE_SITE_URL || "").replace(/\/$/, "");

  return {
    plugins: [react(), seoFiles(siteUrl)],
    server: { port: 5173 },
  };
});