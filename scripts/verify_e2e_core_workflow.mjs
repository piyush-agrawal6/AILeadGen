import playwrightPkg from '../dashboard/node_modules/@playwright/test/index.js';
const { chromium } = playwrightPkg;
import { encode } from '../dashboard/node_modules/next-auth/jwt.js';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const root = path.resolve(__dirname, '..');

function parseEnv(filepath) {
  const env = {};
  if (!fs.existsSync(filepath)) return env;
  const lines = fs.readFileSync(filepath, 'utf8').split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const idx = trimmed.indexOf('=');
    if (idx !== -1) {
      const key = trimmed.slice(0, idx).trim();
      let val = trimmed.slice(idx + 1).trim();
      if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
        val = val.slice(1, -1);
      }
      env[key] = val;
    }
  }
  return env;
}

const envConfig = parseEnv(path.join(root, '.env'));
const authSecret = envConfig.AUTH_SECRET;
const allowedEmail = (envConfig.ALLOWED_USER_EMAILS || 'planebyte@gmail.com').split(',')[0].trim().toLowerCase();

const artifactDir = '/Users/planebyte/.gemini/antigravity/brain/6ce61ed4-aa4a-49e4-8082-8c7aef39282a';
const screenshotsDir = path.join(artifactDir, 'e2e_core_workflow_evidence');
fs.mkdirSync(screenshotsDir, { recursive: true });

const viewports = [
  { name: '1440', width: 1440, height: 900 },
  { name: '1280', width: 1280, height: 800 },
  { name: '1024', width: 1024, height: 768 },
  { name: '768', width: 768, height: 1024 },
  { name: '390', width: 390, height: 844 },
];

const pages = [
  { slug: 'monitors', path: '/intent-radar/monitors' },
  { slug: 'monitors_new', path: '/intent-radar/monitors/new' },
  { slug: 'opportunities', path: '/intent-radar/opportunities' },
  { slug: 'discover', path: '/intent-radar/discover' },
  { slug: 'signals', path: '/intent-radar/signals' },
];

async function verify() {
  console.log('Launching browser to audit core Intent Radar workflow across viewports on http://localhost:3000...');
  const browser = await chromium.launch({ headless: true });
  const baseURL = 'http://localhost:3000';

  const devToken = await encode({
    token: {
      sub: 'admin@planebyte.com',
      email: 'admin@planebyte.com',
      name: 'PlaneByte Admin',
      planeByteAdmitted: true,
      planeByteSession: 'live-prod-session-token',
    },
    secret: authSecret,
    salt: 'authjs.session-token',
    maxAge: 8 * 3600,
  });

  const auditResults = [];

  for (const vp of viewports) {
    console.log(`\n=== Testing Viewport: ${vp.name} (${vp.width}x${vp.height}) ===`);
    const context = await browser.newContext({
      baseURL,
      viewport: { width: vp.width, height: vp.height },
    });

    await context.addCookies([
      {
        name: 'authjs.session-token',
        value: devToken,
        url: baseURL,
        httpOnly: true,
        sameSite: 'Lax',
      },
    ]);

    const page = await context.newPage();

    for (const target of pages) {
      console.log(`[${vp.name}] Visiting ${target.path}...`);
      try {
        await page.goto(target.path, { waitUntil: 'networkidle', timeout: 30000 });
        await page.waitForTimeout(1000);
        const currentUrl = page.url();
        console.log(`[${vp.name}] Loaded URL: ${currentUrl}`);

        const filename = `${target.slug}_${vp.name}.png`;
        const filepath = path.join(screenshotsDir, filename);
        await page.screenshot({ path: filepath, fullPage: false });

        auditResults.push({
          viewport: vp.name,
          page: target.slug,
          path: target.path,
          currentUrl,
          screenshot: filename,
          status: currentUrl.includes(target.path) ? 'PASS' : 'REDIRECT',
        });
      } catch (err) {
        console.error(`[${vp.name}] Error visiting ${target.path}:`, err.message);
        auditResults.push({
          viewport: vp.name,
          page: target.slug,
          path: target.path,
          error: err.message,
          status: 'FAIL',
        });
      }
    }

    await context.close();
  }

  fs.writeFileSync(
    path.join(screenshotsDir, 'audit_results.json'),
    JSON.stringify(auditResults, null, 2)
  );

  console.log('\nVerification complete! Results written to:', path.join(screenshotsDir, 'audit_results.json'));
  await browser.close();
}

verify().catch((err) => {
  console.error('Fatal error during verification:', err);
  process.exit(1);
});
