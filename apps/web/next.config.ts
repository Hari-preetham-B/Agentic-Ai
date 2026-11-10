import type { NextConfig } from "next";
import path from "node:path";
import { loadEnvConfig } from "@next/env";

// Load the repository-root .env as well, so one file can configure both the
// API and the web app. Variables in apps/web/.env.local still take priority.
loadEnvConfig(path.resolve(__dirname, "../.."));

const nextConfig: NextConfig = {
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
