import {defineConfig} from '@playwright/test';
import base from './playwright.billing.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
export default defineConfig({...base,testMatch:'intent-only.spec.ts',outputDir:'../data/artifacts/verification/intent-only/browser',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/intent-only/browser-results.json'}]],webServer:servers.map((server,index)=>({...server,command:index===0?server.command.replace('tests.billing_fixture_server:app','tests.intent_only_fixture_server:app'):server.command,env:{...server.env,LEAD_ENGINE_AVAILABLE:'false'}}))});
