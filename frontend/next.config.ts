import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  reactCompiler: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: "https://sneak-3jg1.onrender.com/api/v1/:path*", // Proxy to Render backend
      },
    ];
  },
};

export default nextConfig;
