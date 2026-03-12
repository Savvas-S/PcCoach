import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      // Individual build result pages are ephemeral (in-memory) — not worth indexing
      disallow: ["/api/", "/build/"],
    },
    sitemap: "https://thepccoach.com/sitemap.xml",
  };
}
