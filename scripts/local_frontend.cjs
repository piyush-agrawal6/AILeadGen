// The Python preview launcher supplies authoritative root configuration in memory.
// Next's dotenv-expand also interpolates inherited values when the same names
// occur in dashboard env files. Load those defaults first, then restore the
// inherited values before Next/Auth.js initialize. Never export them to bundles.
const path = require('node:path');
const { createRequire } = require('node:module');
const dashboardRequire = createRequire(path.resolve(process.cwd(), 'package.json'));
const preload = path.join(__dirname, 'local_frontend_env.cjs');
// Next starts a separate server process. Preserve the same invariant there too.
process.env.NODE_OPTIONS = `${process.env.NODE_OPTIONS || ''} --require=${JSON.stringify(preload)}`.trim();
require(preload);
// Turbopack's PostCSS subprocess worker is incompatible with Node >=26 (exits
// silently with code 0 before the IPC channel is established). Force webpack
// for local development until a compatible Turbopack version is released.
if (process.argv[2] === 'dev' && !process.argv.includes('--webpack') && !process.argv.includes('--turbopack') && !process.argv.includes('--turbo')) {
  process.argv.splice(3, 0, '--webpack');
}
dashboardRequire('next/dist/bin/next');
