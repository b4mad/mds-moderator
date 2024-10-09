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
    BOT_NAME: process.env.BOT_NAME,
  },
};

export default nextConfig;
