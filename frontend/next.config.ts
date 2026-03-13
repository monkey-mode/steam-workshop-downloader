import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**.steamstatic.com" },
      { protocol: "https", hostname: "**.steampowered.com" },
    ],
  },
};

export default nextConfig;
