import {defineConfig} from '@playwright/test';
import base from './playwright.accounts.config';
const kind=process.env.PLANEBYTE_BROWSER_SUITE||'onboarding';
const files=kind==='accounts'?{testDir:'./account-e2e',testMatch:'accounts.spec.ts'}:{testDir:'./intent-radar23-e2e',testMatch:kind==='product'?'product-overhaul.spec.ts':'onboarding-ai.spec.ts'};
export default defineConfig({...base,...files,outputDir:`../data/artifacts/verification/onboarding-repair-20261116/${kind}-browser`,reporter:[['list'],['json',{outputFile:`../data/artifacts/verification/onboarding-repair-20261116/${kind}-browser-results.json`}]]});
