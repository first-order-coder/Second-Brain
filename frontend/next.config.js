/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {},
  images: {
    domains: [],
  },
  eslint: {
    // Allow production builds to succeed even if there are ESLint errors
    ignoreDuringBuilds: true,
  },
}

module.exports = nextConfig
