import {defineConfig} from '@playwright/test';
import phase23 from './playwright.intent-radar23.config';
import radar from './playwright.intent-radar23-regression.config';
import gmail from './playwright.intent-radar23-gmail.config';
import platform from './playwright.intent-radar23-platform.config';
import live from './playwright.intent-radar23-live.config';
import developer from './playwright.developer.config';
const suite=process.env.RADAR_PRODUCT_SUITE||'phase23';
const label=process.env.RADAR_PRODUCT_LABEL||'final';
const base=suite==='phase23'||suite==='product'?phase23:suite==='gmail'?gmail:suite==='live'?live:suite.startsWith('platform')?platform:suite==='developer'?developer:radar;
const servers=Array.isArray(base.webServer)?base.webServer:base.webServer?[base.webServer]:[];
export default defineConfig({...base,
 ...(suite==='product'?{testMatch:'product.spec.ts'}:{}),
 ...(suite.startsWith('platform')?{testMatch:'**/*.spec.ts'}:{}),
 outputDir:`../data/artifacts/verification/intent-radar23-product-${suite}-${label}`,
 reporter:[['list'],['json',{outputFile:`../data/artifacts/verification/intent-radar23-product-${suite}-${label}-results.json`}]],
 webServer:servers.map(s=>({...s,...(suite==='developer'&&s.command.startsWith('node ')?{command:'node ../scripts/local_frontend.cjs start -p 13000'}:{}),env:{...s.env,HEYSOW_E2E_DIST_DIR:'.next-intent-radar23-product-build',
  ...(suite==='live'?{DATABASE_PATH:'/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-23-product-live.db'}:{})}}))});
