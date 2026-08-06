/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  webpack: (config, { dev, isServer }) => {
    if (dev) {
      config.cache = false;
    }
    if (isServer) {
      config.externals = [...(config.externals || []), "echarts"];
    }
    return config;
  },
};

export default nextConfig;
