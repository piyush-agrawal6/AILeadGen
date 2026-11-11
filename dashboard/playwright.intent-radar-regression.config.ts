import {defineConfig} from '@playwright/test';
import radar from './playwright.intent-radar.config';
const servers=Array.isArray(radar.webServer)?radar.webServer:[];
export default defineConfig({...radar,testDir:'./e2e',outputDir:'../data/artifacts/verification/intent-radar/lead-engine-browser',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/intent-radar/lead-engine-browser-results.json'}]],webServer:servers.map((server,index)=>({...server,...(index===1?{command:'node ../scripts/local_frontend.cjs start -p 13000',env:{...server.env,HEYSOW_E2E_DIST_DIR:'.next-intent-radar-build'}}:{})}))});
