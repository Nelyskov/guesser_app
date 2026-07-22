/** @type {import('next').NextConfig} */
module.exports = {
  output: "standalone",
  images: { unoptimized: true },
  async rewrites() {
    return [{
      source: "/api/:path*",
      destination: "http://backend:8000/api/:path*"
    }];
  },
};