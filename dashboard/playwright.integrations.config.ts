import {defineConfig} from '@playwright/test';
import {randomBytes} from 'node:crypto';
import base from './playwright.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
const key=randomBytes(32).toString('base64');
const env={HEYSOW_WORKSPACE_MANAGEMENT_ENABLED:'true',HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED:'true',AUTH_GOOGLE_ID:'controlled-client',AUTH_GOOGLE_SECRET:'controlled-client-secret',GOOGLE_SHEETS_REDIRECT_URI:'http://127.0.0.1:13000/acquisition/sheets/callback'};
export default defineConfig({...base,testDir:'./integration-e2e',outputDir:'../data/artifacts/verification/browser-integrations',webServer:servers.map((server,index)=>({...server,env:{...server.env,...env,...(index===0?{HEYSOW_INTEGRATION_ENCRYPTION_KEY:key}:{})}}))});
