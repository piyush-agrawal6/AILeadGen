import {defineConfig} from '@playwright/test';
import base from './playwright.intent-radar.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
export default defineConfig({...base,testDir:'./intent-radar23-e2e',testMatch:'phase23.spec.ts',outputDir:'../data/artifacts/verification/intent-radar23-browser',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/intent-radar23-browser-results.json'}]],webServer:servers.map((s,i)=>({...s,command:i===0?s.command.replace('tests.intent_radar_fixture_server:app','tests.intent_radar_23_fixture_server:app'):'node ../scripts/local_frontend.cjs start -p 13000',env:{...s.env,HEYSOW_E2E_DIST_DIR:'.next-intent-radar23-build'}}))});
