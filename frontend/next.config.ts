import type { NextConfig } from "next";

// Where Django runs. The browser never calls this directly: it calls /api/* on
// Next.js, and the rewrite below forwards it, so the session cookie is first-party.
// Locally: Django on :8000. On Vercel: the Render address, e.g. https://homehaat-api.onrender.com (docs/deploy.md).
// It's read when the site is BUILT, so after changing it in Vercel, redeploy.
if (process.env.VERCEL && !process.env.API_INTERNAL_URL) {
  throw new Error("Set API_INTERNAL_URL in Vercel (Settings > Environment Variables) to the Render address.");
}
const API = (process.env.API_INTERNAL_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  // Lets a second, throwaway copy (end-to-end checks) run next to your normal one. Default: .next
  distDir: process.env.NEXT_DIST_DIR || ".next",
  // Keep "/api/cart/" exactly as written. Django URLs end with a slash, and
  // Next.js would otherwise redirect "/api/cart/" to "/api/cart".
  skipTrailingSlashRedirect: true,
  experimental: {
    // How long the /api proxy waits for Django (default 30 s). The AI helper may take up to 50 s when Google is
    // busy (two models, one retry: ai/gemini_client.py TIME_BUDGET), so give it a little more than that.
    proxyTimeout: 60_000,
  },
  async rewrites() {
    return [
      // ":path*" drops the trailing slash, so we add it back for Django.
      { source: "/api/:path*", destination: `${API}/api/:path*/` },
      { source: "/media/:path*", destination: `${API}/media/:path*` },
    ];
  },
  images: {
    remotePatterns: [{ protocol: "https", hostname: "images.unsplash.com" }],
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
