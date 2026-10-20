// File path: frontend/src/components/Seo.jsx
//
// Sets the page title, description, canonical link and robots rule for the
// current route. Always sets robots explicitly, so a "noindex" from a
// private page can never linger on a public one.

import { useEffect } from "react";
import { siteConfig } from "../lib/siteConfig";

function setMeta(attribute, key, content) {
  let element = document.head.querySelector(`meta[${attribute}="${key}"]`);
  if (!element) {
    element = document.createElement("meta");
    element.setAttribute(attribute, key);
    document.head.appendChild(element);
  }
  element.setAttribute("content", content);
}

function setCanonical(href) {
  let link = document.head.querySelector('link[rel="canonical"]');
  if (!href) {
    link?.remove();
    return;
  }
  if (!link) {
    link = document.createElement("link");
    link.setAttribute("rel", "canonical");
    document.head.appendChild(link);
  }
  link.setAttribute("href", href);
}

export function Seo({ title, description, path = "/", noindex = false }) {
  useEffect(() => {
    document.title = title;
    setMeta("property", "og:title", title);
    setMeta("name", "twitter:title", title);

    if (description) {
      setMeta("name", "description", description);
      setMeta("property", "og:description", description);
      setMeta("name", "twitter:description", description);
    }

    setMeta("name", "robots", noindex ? "noindex, nofollow" : "index, follow");

    const url = siteConfig.siteUrl ? `${siteConfig.siteUrl}${path}` : null;
    setCanonical(noindex ? null : url);
    if (url) setMeta("property", "og:url", url);
  }, [title, description, path, noindex]);

  return null;
}