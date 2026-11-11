import {defineConfig} from '@playwright/test';
import radar from './playwright.intent-radar.config';
const suite=process.env.B04_BROWSER_SUITE==='radar'?'radar':'lead-engine';
const servers=Array.isArray(radar.webServer)?radar.webServer:[];
const evidence='../data/artifacts/verification/phase6/b04-completion-20261110';
export default defineConfig({...radar,testDir:suite==='radar'?'./intent-radar-e2e':'./e2e',outputDir:`${evidence}/${suite}-browser`,reporter:[['list'],['json',{outputFile:`${evidence}/${suite}-browser-results.json`}]],webServer:servers.map((server,index)=>({...server,...(index===1?{command:'node ../scripts/local_frontend.cjs start -p 13000',env:{...server.env,HEYSOW_E2E_DIST_DIR:'.next-gmail-build',HEYSOW_INTERNAL_EXPERIMENTS_ENABLED:'false'}}:{})}))});
