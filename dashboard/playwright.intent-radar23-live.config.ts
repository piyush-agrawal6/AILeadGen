import {defineConfig} from '@playwright/test';
import base from './playwright.intent-radar23.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
const database=process.env.RADAR23_LIVE_DATABASE||'/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-23-final-live.db';
export default defineConfig({...base,testMatch:'live.spec.ts',timeout:180000,outputDir:'../data/artifacts/verification/intent-radar23-live-browser',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/intent-radar23-live-browser-results.json'}]],webServer:servers.map((s,i)=>({...s,command:i===0?s.command.replace('tests.intent_radar_23_fixture_server:app','tests.intent_radar_live_browser_server:app'):s.command,env:{...s.env,DATABASE_PATH:database,ALLOWED_USER_EMAILS:'radar23@example.test',INTENT_RADAR_AI_ENABLED:'true',VERTEX_AI_ENABLED:'true',ACQUISITION_TEST_ALLOW_PROVIDER_NETWORK:'1'}}))});
