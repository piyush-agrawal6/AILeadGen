import {defineConfig} from '@playwright/test';
import base from './playwright.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
// These are disposable credentials, never the preview owner's actual session.
const env={APP_ENV:'development',HEYSOW_E2E_DIST_DIR:'.next-preview-test',HEYSOW_WORKSPACE_MANAGEMENT_ENABLED:'true',AUTH_GOOGLE_ID:'controlled-google-client',AUTH_GOOGLE_SECRET:'controlled-google-secret',AUTH_SECRET:'fixture-session-$literal-sign-only-12345678901234567890',LEADENGINE_API_SIGNING_SECRET:'fixture-internal-$literal-sign-only-12345678901234567890',ALLOWED_USER_EMAILS:'founder@leadengine.example,newuser@heysow.example'};
export default defineConfig({...base,testDir:'./preview-e2e',outputDir:'../data/artifacts/verification/browser-preview',webServer:servers.map((server,index)=>({...server,...(index===1?{command:'node ../scripts/local_frontend.cjs dev -p 13000'}:{}),env:{...server.env,...env}}))});
