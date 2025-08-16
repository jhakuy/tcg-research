/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: process.env.NODE_ENV === 'production' 
          ? 'https://your-api-domain.vercel.app/:path*'
          : 'http://localhost:8000/:path*'
      }
    ]
  }
}

module.exports = nextConfig