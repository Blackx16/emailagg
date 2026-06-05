import type { NextConfig } from "next";

const allowedOrigins = ["localhost", "127.0.0.1", "lvh.me"];
const frontendUrl = process.env.FRONTEND_URL || process.env.NEXT_PUBLIC_FRONTEND_URL;

if (frontendUrl) {
  try {
    const hostname = new URL(frontendUrl).hostname;
    if (hostname && !allowedOrigins.includes(hostname)) {
      allowedOrigins.push(hostname);
    }
  } catch (e) {
    // ignore
  }
}

const nextConfig: NextConfig = {
  allowedDevOrigins: allowedOrigins,
};

export default nextConfig;
