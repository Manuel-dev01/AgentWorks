/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The dashboard reads verified proof artifacts from sibling workspace dirs (../agents, ../docs)
  // at request time on the server. Nothing client-bundled depends on them.
  // No ESLint config is shipped (bespoke demo); keep TS type-checking on, skip lint in builds.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
