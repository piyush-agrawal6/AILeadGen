import {defineConfig} from '@playwright/test';
import base from './playwright.intent-only.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
export default defineConfig({...base,webServer:servers.map((s,i)=>({...s,command:i?s.command:s.command.replace('tests.intent_only_fixture_server','tests.billing_recovery_fixture_server'),env:{...s.env,HEYSOW_E2E_DIST_DIR:'.next-growth-build',TRANSACTIONAL_MAIL_ENABLED:'false'}})),testMatch:'subscription-payment.spec.ts',outputDir:'../data/artifacts/verification/billing-recovery/browser',reporter:'list'});
