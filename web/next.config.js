/** @type {import('next').NextConfig} */
const nextConfig = {
  // Ensure API routes are treated as serverless functions
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3000', 'goldbot24.vercel.app'],
    },
  },
  // Force dynamic rendering for API routes
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: '/api/:path*',
      },
    ];
  },
};

module.exports = nextConfig;