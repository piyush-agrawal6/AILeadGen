import path from "node:path";
import { fileURLToPath } from "node:url";
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  poweredByHeader: false,
  distDir: process.env.HEYSOW_E2E_DIST_DIR || '.next',
  // OAuth callbacks contain short-lived grant codes; keep their URLs out of
  // development request logs without hiding ordinary application diagnostics.
   logging: { incomingRequests: { ignore: [/\/reset-password/, /\/api\/auth\//, /\/acquisition\/sheets\/callback/, /\/intent-radar\/integrations\/sheets\/callback/, /\/settings\/integrations\/gmail-callback/] } },
  turbopack: { root: path.dirname(fileURLToPath(import.meta.url)) },
  images: {
    unoptimized: true,
    dangerouslyAllowSVG: true,
  },
  async headers() {
    return [{source:'/reset-password',headers:[{key:'Referrer-Policy',value:'no-referrer'}]},{ source: "/:path*", headers: [
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
      { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
      { key: "X-Frame-Options", value: "DENY" },
      ...(process.env.APP_ENV === "production" ? [{ key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" }] : []),
    ] }];
  },
};

export default nextConfig;
