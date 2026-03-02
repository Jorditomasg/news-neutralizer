import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
  // @ts-expect-error - eslint is a valid NextConfig property but not in TS types
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
