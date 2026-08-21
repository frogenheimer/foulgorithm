/** @type {import("next").NextConfig} */
const nextConfig = {
  // Fully static export. Every page is prerendered already, so nothing is lost,
  // and the output is plain files that any host can serve. This also delivers
  // the portability ADR-004 asks for: no Vercel runtime is involved.
  output: "export",
};
export default nextConfig;
