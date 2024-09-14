/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",

  async rewrites() {
    return [
      {
        source: "/:path*",
        destination: "http://localhost:7860/:path*",
      },
    ];
  },

  env: {
    SYSTEM_PROMPT: process.env.SYSTEM_PROMPT,
  },
};

export default nextConfig;
