import {defineConfig} from '@playwright/test';
import base from './playwright.intent-radar.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
const suite=process.env.RADAR23_REGRESSION==='radar'?'radar':'lead-engine';
export default defineConfig({...base,testDir:suite==='radar'?'./intent-radar-e2e':'./e2e',outputDir:'../data/artifacts/verification/intent-radar23-'+suite,reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/intent-radar23-'+suite+'-results.json'}]],webServer:servers.map((s,i)=>({...s,...(i===1?{command:'node ../scripts/local_frontend.cjs start -p 13000',env:{...s.env,HEYSOW_E2E_DIST_DIR:'.next-intent-radar23-build'}}:{})}))});
