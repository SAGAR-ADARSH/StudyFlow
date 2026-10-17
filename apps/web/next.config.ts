import type { NextConfig } from "next";

// The browser only ever calls its own origin; the Next server forwards /api/v1 to FastAPI.
// Override API_PROXY_TARGET when the API runs somewhere else (e.g. http://api:8000 in compose).
const API_PROXY_TARGET = process.env.API_PROXY_TARGET || "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${API_PROXY_TARGET}/api/v1/:path*`,
      },
      {
        source: "/health",
        destination: `${API_PROXY_TARGET}/health`,
      },
    ];
  },
};

export default nextConfig;
