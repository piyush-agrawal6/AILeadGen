import {defineConfig} from '@playwright/test';
import base from './playwright.gmail.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
export default defineConfig({...base,outputDir:'../data/artifacts/verification/intent-radar23-gmail',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/intent-radar23-gmail-results.json'}]],webServer:servers.map((s,i)=>({...s,...(i===1?{command:'node ../scripts/local_frontend.cjs start -p 13000',env:{...s.env,HEYSOW_E2E_DIST_DIR:'.next-intent-radar23-build'}}:{})}))});
