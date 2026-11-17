import {defineConfig} from '@playwright/test';
import base from './playwright.intent-only.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
export default defineConfig({...base,webServer:servers.map(s=>({...s,env:{...s.env,HEYSOW_E2E_DIST_DIR:'.next-subscription-build'}})),testMatch:'subscription-payment.spec.ts',outputDir:'../data/artifacts/verification/creem-20261117/browser',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/creem-20261117/browser-results.json'}]]});
