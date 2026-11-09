const {createRequire} = require('node:module');
const path = require('node:path');
// Use the fixed dashboard directory (resolved from __dirname) rather than
// process.cwd(), which varies across Turbopack's subprocess workers and causes
// @next/env resolution to fail silently with exit code 0.
const dashboardDir = path.resolve(__dirname, '..', 'dashboard');
const dashboardRequire=createRequire(path.join(dashboardDir,'package.json'));
const nextEnv=dashboardRequire('@next/env');
const inherited={...process.env};
nextEnv.loadEnvConfig(dashboardDir,true);
Object.assign(process.env,inherited);
nextEnv.updateInitialEnv(inherited);
