import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['*.localhost', '192.168.*.*', 'localhost'],
};

export default nextConfig;
