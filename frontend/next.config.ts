import type { NextConfig } from "next";

// Where Django runs. The browser never calls this directly: it calls /api/* on
// Next.js, and the rewrite below forwards it, so the session cookie is first-party.
const API = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Keep "/api/cart/" exactly as written. Django URLs end with a slash, and
  // Next.js would otherwise redirect "/api/cart/" to "/api/cart".
  skipTrailingSlashRedirect: true,
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
