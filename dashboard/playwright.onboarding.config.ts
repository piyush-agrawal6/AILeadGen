import {defineConfig} from '@playwright/test';
import base from './playwright.product.config';
const servers=Array.isArray(base.webServer)?base.webServer:[];
export default defineConfig({...base,testMatch:'onboarding-ai.spec.ts',outputDir:'../data/artifacts/verification/final-remediation/onboarding-browser',reporter:[['list'],['json',{outputFile:'../data/artifacts/verification/final-remediation/onboarding-browser-results.json'}]],webServer:servers.map((server,index)=>({...server,command:index===0?server.command.replace('tests.intent_only_fixture_server:app','tests.onboarding_fixture_server:app'):server.command}))});
