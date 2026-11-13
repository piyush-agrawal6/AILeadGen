import {defineConfig} from '@playwright/test';
import base from './playwright.intent-radar.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
export default defineConfig({...base,testDir:'./intent-radar23-e2e',testMatch:'growth.spec.ts',outputDir:'../data/artifacts/verification/phase4-browser',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/phase4-browser-results.json'}]],webServer:servers.map((server,index)=>({...server,command:index===0?server.command.replace('tests.intent_radar_fixture_server:app','tests.growth_fixture_server:app'):'node ../scripts/local_frontend.cjs start -p 13000',env:{...server.env,HEYSOW_E2E_DIST_DIR:'.next-growth-build',INTENT_RADAR_GROWTH_ENABLED:'true'}}))});
